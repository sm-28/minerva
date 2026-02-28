import io
import os
import sys
import time
import re
import logging

import streamlit as st

# Add poc/ to path when running from project root
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from utils import LatencyTracker, get_logger, get_st_session_id
from sarvam_adapter import SarvamClient
from rag import (
    load_vector_store,
    retrieve,
    build_rag_prompt,
    SYSTEM_PROMPT,
    UNKNOWN_RESPONSE,
)

log = get_logger("app")

# Enable debug logging for authlib to troubleshoot handshake failures
logging.getLogger("authlib").setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Minerva",
    
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Authentication Gateway
# ---------------------------------------------------------------------------

def check_auth():
    """
    Check if user is authenticated via st.login/st.user.
    Provides a login interface if not.
    """
    # Bypass for local testing if explicitly disabled in .env
    auth_disabled = os.environ.get("AUTH_DISABLED", "false").lower() == "true"
    
    if auth_disabled:
        st.session_state["user_id"] = "dev-user"
        st.session_state["session_id"] = "dev-session"
        return

    # Check if a custom session state indicates logged in
    if not st.session_state.get("is_logged_in", False):
        import random
        from utils import send_otp_email
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(
                '<div class="hero-header">'
                '<h1>🎙️ Minerva Voice AI [Demo]</h1>'
                '<p>Secure Email OTP Login</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            
            # State machine for OTP
            if "otp_sent" not in st.session_state:
                st.session_state["otp_sent"] = False
                
            if not st.session_state["otp_sent"]:
                with st.form("request_otp_form"):
                    email = st.text_input("Enter your email address to receive a login code")
                    submit = st.form_submit_button("Send Code", use_container_width=True)
                    
                    if submit and email:
                        # Generate OTP
                        otp = str(random.randint(100000, 999999))
                        st.session_state["pending_email"] = email
                        st.session_state["pending_otp"] = otp
                        
                        # Fetch Secrets
                        smtp_user = st.secrets.get("smtp", {}).get("user", "")
                        smtp_pass = st.secrets.get("smtp", {}).get("password", "")
                        
                        if not smtp_user or not smtp_pass:
                            st.error("Missing SMTP credentials in secrets.toml!")
                            st.stop()
                            
                        with st.spinner("Sending code..."):
                            success = send_otp_email(email, otp, smtp_user, smtp_pass)
                            
                        if success:
                            st.session_state["otp_sent"] = True
                            st.rerun()
                        else:
                            st.error("Failed to send email. Check credentials and console logs.")
                            
            else: # OTP was sent, verify it
                st.info(f"A 6-digit code was sent to **{st.session_state.get('pending_email')}**")
                with st.form("verify_otp_form"):
                    entered_otp = st.text_input("Enter the 6-digit code", max_chars=6)
                    verify = st.form_submit_button("Verify & Login", use_container_width=True)
                    
                    if verify:
                        if entered_otp == st.session_state.get("pending_otp"):
                            st.session_state["is_logged_in"] = True
                            st.session_state["user_id"] = st.session_state["pending_email"]
                            st.session_state["session_id"] = get_st_session_id()
                            # Cleanup
                            del st.session_state["pending_otp"]
                            del st.session_state["otp_sent"]
                            st.rerun()
                        else:
                            st.error("Incorrect code. Please try again.")
                
                if st.button("Start over", use_container_width=True):
                    st.session_state["otp_sent"] = False
                    st.rerun()
            
            # Add a "Force Bypass" button if they are stuck
            st.divider()
            if st.checkbox("Having trouble? Enable local development bypass"):
                st.info("💡 Set `AUTH_DISABLED=true` in your `.env` file to skip this permanently.")
                if st.button("Enter as Guest"):
                    st.session_state["is_logged_in"] = True
                    st.session_state["user_id"] = "guest-user"
                    st.session_state["session_id"] = get_st_session_id()
                    st.rerun()

            st.stop()
        
    # User is officially verified via OTP (or bypass) and execution continues

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Gradient header */
    .hero-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .hero-header h1 {
        color: #e0e0ff;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    .hero-header p {
        color: #a0b0d0;
        margin: 0.4rem 0 0 0;
        font-size: 0.95rem;
    }

    /* Metric tiles */
    .metric-tile {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 0.6rem 1rem;
        text-align: center;
        font-size: 0.85rem;
        color: #a0b0d0;
        border: 1px solid #2a2a4a;
    }
    .metric-value {
        font-size: 1.2rem;
        font-weight: 700;
        color: #7eb8f7;
    }

    /* Unknown badge */
    .unknown-badge {
        background: #c0392b;
        color: white;
        border-radius: 6px;
        padding: 0.2rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .known-badge {
        background: #27ae60;
        color: white;
        border-radius: 6px;
        padding: 0.2rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0d0d1a;
    }

    /* End conversation button */
    .stButton > button {
        background: linear-gradient(to right, #C49863, #D6AA75);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(231,76,60,0.4);
    }

    /* Summary box */
    .summary-box {
        background: linear-gradient(135deg, #1a0a0a, #2d1515);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #6a1a1a;
        margin-top: 1rem;
    }
    .summary-box h3 { color: #ff8080; margin-top: 0; }
    .summary-box li { color: #ffcccc; margin: 0.4rem 0; }

    /* Debug box */
    .debug-box {
        background: #0a0a1a;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #2a2a4a;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        color: #8899bb;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_state():
    defaults = {
        "user_id":           None,
        "session_id":        None,
        "unknown_questions": [],
        "conversation":      [],   # list of {"role": "user"|"assistant", "content": str, "is_unknown": bool}
        "sarvam":            None,
        "vector_store_ok":   False,
        "session_ended":     False,
        "debug_mode":        False,
        "latency_log":       [],   # list of dicts from LatencyTracker.all()
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _get_sarvam() -> SarvamClient:
    if st.session_state["sarvam"] is None:
        st.session_state["sarvam"] = SarvamClient()
    return st.session_state["sarvam"]


def _ensure_vector_store():
    if not st.session_state["vector_store_ok"]:
        load_vector_store()
        st.session_state["vector_store_ok"] = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> list[str]:
    """Split text into sentences/phrases for sequential synthesis."""
    # Split by period, question mark, or exclamation followed by space
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Filter out empty and trim
    return [s.strip() for s in sentences if s.strip()]

# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

def render_sidebar():
    with st.sidebar:
        # User Identity & Logout at the top
        user_email = st.session_state.get("user_id", "Guest")
        display_name = user_email.split("@")[0].title() if "@" in user_email else user_email.title()
        
        st.markdown(f"### 👋 {display_name}")
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
                
        st.divider()
        st.markdown("## 🎙️ Minerva Settings")

        # Debug mode toggle
        st.session_state["debug_mode"] = st.toggle(
            "Debug Mode",
            value=st.session_state["debug_mode"],
            help="Show similarity scores, retrieved chunks, and token counts",
        )
        st.divider()

        # Unknown questions log
        unknowns = st.session_state["unknown_questions"]
        st.markdown(f"### ❓ Unknown Questions ({len(unknowns)})")
        if unknowns:
            for i, q in enumerate(unknowns, 1):
                st.markdown(f"`{i}.` {q}")
        else:
            st.caption("No unknown questions yet.")

        st.divider()

        # Latency history
        if st.session_state["latency_log"]:
            st.markdown("### ⏱️ Last Latency")
            last = st.session_state["latency_log"][-1]
            for k, v in last.items():
                st.markdown(f"- **{k}**: `{v:.3f}s`")

        st.divider()
        st.caption("Minerva Voice AI [Demo]")


def render_latency_panel(latency: dict):
    if not latency:
        return
    cols = st.columns(len(latency) + 1)
    for i, (k, v) in enumerate(latency.items()):
        with cols[i]:
            st.markdown(
                f'<div class="metric-tile">'
                f'<div>{k}</div>'
                f'<div class="metric-value">{v:.2f}s</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    total = sum(latency.values())
    with cols[-1]:
        st.markdown(
            f'<div class="metric-tile">'
            f'<div>TOTAL</div>'
            f'<div class="metric-value">{total:.2f}s</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_debug_panel(result: dict):
    if not st.session_state["debug_mode"]:
        return
    with st.expander("🔬 Debug Information", expanded=True):
        chunks = result.get("chunks", [])
        is_unk = result.get("is_unknown", False)
        tokens = result.get("llm_tokens", 0)

        badge = f'<span class="{"unknown-badge" if is_unk else "known-badge"}">'
        badge += f'{"UNKNOWN" if is_unk else "KNOWN"}</span>'
        st.markdown(f"**Classification:** {badge}", unsafe_allow_html=True)
        st.markdown(f"**Response tokens (approx.):** `{tokens}`")

        if chunks:
            st.markdown("**Retrieved Chunks:**")
            for c in chunks:
                score_color = "#e74c3c" if c["is_unknown"] else "#27ae60"
                st.markdown(
                    f"**Chunk {c['rank']}** — `{c['source']}` — "
                    f"Score: <span style='color:{score_color};font-weight:700'>{c['score']:.4f}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="debug-box">{c["text"][:400]}{"…" if len(c["text"]) > 400 else ""}</div>',
                    unsafe_allow_html=True,
                )


def render_end_session_summary():
    unknowns = st.session_state["unknown_questions"]
    if not unknowns:
        st.success("✅ No unknown questions were recorded this session. Great coverage!")
        return

    items_html = "".join(f"<li>{q}</li>" for q in unknowns)
    st.markdown(
        f'<div class="summary-box">'
        f'<h3>📋 Unknown Questions Summary</h3>'
        f'<p>The following questions could not be answered from the provided documents:</p>'
        f'<ol>{items_html}</ol>'
        f'<hr style="border-color:#6a1a1a;margin:1rem 0">'
        f'<p style="color:#ffa0a0;font-size:0.9rem">📞 <strong>Simulate callback:</strong> '
        f'A follow-up will be arranged to address these {len(unknowns)} questions.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

def main():
    _init_state()
    check_auth()
    render_sidebar()

    # Hero header
    st.markdown(
        '<div class="hero-header">'
        '<h1>🎙️ Minerva Voice AI [Demo]</h1>'
        '<p>Document-Grounded 24/7 Multilingual Voice AI Assistant</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Pre-load vector store (shows error if not ingested)
    try:
        _ensure_vector_store()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    # Early-exit if session ended
    if st.session_state["session_ended"]:
        st.markdown("---")
        st.markdown("## 🏁 Session Ended")
        render_end_session_summary()
        if st.button("🔄 Start New Session"):
            for key in ["unknown_questions", "conversation", "latency_log", "session_ended"]:
                st.session_state[key] = [] if key != "session_ended" else False
            st.rerun()
        return

    # Conversation history (using chat_message for better aesthetic)
    for msg in st.session_state["conversation"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("is_unknown"):
                st.caption("⚠️ Grounding check: Unknown in provided context.")

    # Mic input
    st.markdown("---")
    st.markdown("### 🎤 Speak to the Bot")
    st.caption("Click the microphone button, ask your question, then click again to stop.")

    try:
        from audio_recorder_streamlit import audio_recorder
        audio_bytes = audio_recorder(
            text="",
            recording_color="#e74c3c",
            neutral_color="#5b7fde",
            icon_name="microphone",
            icon_size="3x",
            pause_threshold=2.0,    # auto-stop after 2s of silence
            sample_rate=16000,
        )
    except ImportError:
        st.warning("audio-recorder-streamlit is not installed. Using file uploader as fallback.")
        uploaded = st.file_uploader("Upload WAV audio", type=["wav"])
        audio_bytes = uploaded.read() if uploaded else None

    # Process audio
    if audio_bytes and len(audio_bytes) > 2000:  # skip spurious tiny captures
        tracker = LatencyTracker()
        sarvam  = _get_sarvam()

        # Step 1: STT (Transcribe user audio)
        with st.status("Listening...", expanded=False) as status:
            with tracker.measure("STT"):
                try:
                    transcript, det_lang = sarvam.transcribe(audio_bytes, language_code="unknown")
                    log.info("Detected language: %s", det_lang)
                except Exception as e:
                    st.error(f"STT Error: {e}")
                    st.stop()
            
            if not transcript:
                status.update(label="No speech detected.", state="error")
                st.stop()
            
            status.update(label="Transcribed!", state="complete")
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(transcript)
        
        st.session_state["conversation"].append({
            "role": "user", "content": transcript
        })
        # Step 1.1: Translate the user query from the detected language to english. If it is english, skip this step
        if str(det_lang).strip().lower() != "en-in":
            with st.status("Translating...", expanded=False) as status:
                with tracker.measure("Translate"):
                    try:
                        transcript = sarvam.translate(transcript, det_lang, "en-IN")
                    except Exception as e:
                        st.error(f"Translate Error: {e}")
                        st.stop()
            status.update(label="Translated!", state="complete")

        # Step 2: Retrieval (RAG)
        with st.status("Searching documents...", expanded=False) as status:
            with tracker.measure("Retrieval"):
                chunks = retrieve(transcript, top_k=3)
            status.update(label="Context retrieved.", state="complete")

        is_unknown = (not chunks) or chunks[0]["is_unknown"]

        # Step 3: LLM + Step 4: Translation + Step 5: TTS
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            audio_placeholder = st.empty()
            debug_placeholder = st.empty()
            
            if is_unknown:
                response = UNKNOWN_RESPONSE
                llm_tokens = 0
                st.session_state["unknown_questions"].append(transcript)
                
                # Translate fallback if needed
                if str(det_lang).strip().lower() != "en-in":
                    with tracker.measure("Translate"):
                        response = sarvam.translate(response, "en-IN", det_lang)
                
                response_placeholder.markdown(response)
                
                # Synthesize and play
                with tracker.measure("TTS"):
                    audio_data = sarvam.text_to_speech(response, det_lang)
                audio_placeholder.audio(audio_data, format="audio/wav", autoplay=True)
                
            else:
                user_prompt = build_rag_prompt(chunks, transcript)
                
                # Generate base response (LLM)
                with tracker.measure("LLM"):
                    try:
                        response_en = sarvam.chat_completion(SYSTEM_PROMPT, user_prompt)
                    except Exception as e:
                        st.error(f"LLM Error: {e}")
                        st.stop()
                
                # Translate to user's language if required
                if str(det_lang).strip().lower() != "en-in":
                    with tracker.measure("Translate"):
                        response = sarvam.translate(response_en, "en-IN", det_lang)
                else:
                    response = response_en
                
                # Split and play progressively
                response_placeholder.markdown(response)
                llm_tokens = len(response_en.split())

                # Progressive TTS: synthesizing the whole thing but showing markers
                # Actually, for "play as it arrives", we synthesize sentences
                sentences = split_sentences(response)
                all_audio = []
                
                # Note: Streamlit's st.audio replaces previous audio. 
                # To play *sequence* seamlessly, we'd need HTML/JS.
                # For this POC, we'll synthesize segments and concatenate or play the whole thing.
                # Speed hack: synthesize first two sentences together for faster playback
                with tracker.measure("TTS"):
                    audio_data = sarvam.text_to_speech(response, det_lang)
                
                audio_placeholder.audio(audio_data, format="audio/wav", autoplay=True)

            # Log to session
            st.session_state["conversation"].append({
                "role": "assistant", 
                "content": response, 
                "is_unknown": is_unknown
            })
            st.session_state["latency_log"].append(tracker.all())

            # Final metrics
            render_latency_panel(tracker.all())
            
            if st.session_state["debug_mode"]:
                with debug_placeholder:
                    render_debug_panel({
                        "chunks": chunks,
                        "is_unknown": is_unknown,
                        "llm_tokens": llm_tokens
                    })

    # End Conversation button
    st.markdown("---")
    col1, _ = st.columns([1, 4])
    with col1:
        if st.button("⛔️ End Conversation"):
            st.session_state["session_ended"] = True
            st.rerun()


if __name__ == "__main__":
    main()
