import io
import os
import sys
import time
import re
import logging
import hashlib

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
    UNKNOWN_RESPONSE,
)

# ---------------------------------------------------------------------------
# Prompts & Constants
# ---------------------------------------------------------------------------

INDUSTRY_CLASSIFIER_SYSTEM = """You are an industry classifier. The available industries are: {industries}.
Given a user query, output ONLY the exact industry name from the list or 'UNKNOWN'. 
Examples:
- "Can you help with my credit card?" -> Fintech
- "How do I fix my warehouse roof?" -> Warehouses
- "Tell me about mobile banking" -> Fintech
- "Cold roofing solutions" -> Warehouses

Identify the industry based on the core topic of the user's question."""

SCOPE_CLASSIFIER_SYSTEM = """You are a scope classifier for the {industry} industry. 
Available Topics: {topics}.
User Query: {query}

Instructions:
1. If the query is about the industry, its services, the company's background, history, experience, or track record, output 'RELATED'.
2. If the user is expressing interest in the next steps, asking to book an appointment, requesting a consultation, or asking for contact details/pricing, output 'RELATED'.
3. Even if it's a short "yes", "sure", "book it" following a suggestion, it's 'RELATED'.
4. If it's a greeting (hi, hello) or completely unrelated (weather, jokes, general knowledge), output 'GENERAL'.
5. Output ONLY the word 'RELATED' or 'GENERAL' with no punctuation.
6. When in doubt, prefer 'RELATED'.
"""

TOPIC_CLASSIFIER_SYSTEM = "You are a topic classifier. Given a list of topics ({topics}) for {industry}, determine which one the user is asking about. Output ONLY the exact topic name or 'OUT_OF_SCOPE'. If it's a broad industry question, pick the most relevant topic."

# New RAG System Prompt
SYSTEM_PROMPT = """
You are representative of the company. 
Conversation Summary: {summary}

INSTRUCTIONS:
1. Answer using the provided context and the summary.
2. Do NOT repeat your initial greeting or the list of industries you specialize in.
3. If the user is responding with a confirmation, affirmation (e.g. "Yes", "Sure"), or following up on a task (e.g. scheduling, booking), use the Conversation Summary to provide a natural response.
3. If the information is missing from both the context and the summary, say: "I do not have that information in my knowledge base."
4. Respond in first person, concisely (approx 20 words).
5. Usually end with a question to keep things moving, UNLESS the goal is fully achieved.
6. CRITICAL CLOSURE RULE: Trigger completion ONLY when a specific commitment is FINALIZED. 
   - ACHIEVED: "Yes, Friday at 10 AM is perfect" or "My number is 555-0123".
   - NOT ACHIEVED: "Yes please", "Book a time", "I want a consultation", "Tell me more".
7. If the user expresses interest (e.g., "Yes", "Book it") but hasn't picked a time/date yet, you MUST ask: "What day or time would work best for you?" 
8. Do NOT append "[COMPLETE]" until the user has actually picked a slot or provided contact info.
9. To complete: thank the user warmly, confirm the final details (e.g., "Great, I've noted your appointment for Friday at 10 AM. Talk soon!"), and append exactly "[COMPLETE]" at the end.
10. Ensure your response is aligned with this steering instruction: {goal}.
"""

log = get_logger("app")
logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)

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
            if st.checkbox("Any trouble in login? Enter as a Guest"):
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
import json
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
CLIENT_CONFIG_PATH = BASE_DIR / "client_config.json"

@st.cache_resource
def load_clients():
    with open(CLIENT_CONFIG_PATH) as f:
        return json.load(f)

CLIENTS = load_clients()

def get_available_industries():
    return list(set([c["Industry"] for c in CLIENTS]))

@st.cache_resource
def get_client_topics():
    sarvam = SarvamClient()
    topics = {}
    for client in CLIENTS:
        index_name = client["index"]
        industry = client["Industry"]
        try:
            # Retrieve chunks to find representative topics
            chunks = retrieve("Get the highlights present in this knowledge base", index_name, top_k=5)
            if not chunks:
                topics[index_name] = []
                continue
            
            context = "\n".join([c["text"][:4000] for c in chunks])
            log.info(f"Flow: Context for {index_name}: {context}")
            prompt = f"Based on these following contexts {context} \n from a {industry} company, list maximum of 5 specific customer enquiry topics strictly based on the provided context. Output only the topics (3 words max), one per line, no numbering."
            response = sarvam.chat_completion("You are a helpful assistant.", prompt, temperature=0.0, max_tokens=100)
            
            derived = [t.strip("- ").strip() for t in response.split("\n") if t.strip()]
            topics[index_name] = derived
            log.info(f"Flow: Derived topics for {index_name}")
        except Exception as e:
            log.error(f"Failed to derive topics for {index_name}: {e}")
            topics[index_name] = []
    return topics

def _init_state():
    defaults = {
        "user_id":           None,
        "session_id":        None,
        "unknown_questions": [],
        "conversation":      [],   # list of {"role": "user"|"assistant", "content": str}
        "sarvam":            SarvamClient(),
        "vector_store_ok":   False,
        "session_ended":     False,
        "debug_mode":        False,
        "latency_log":       [],
        "has_greeted":       False,
        "selected_client":   None, # dict from CLIENTS
        "selected_topic":    None,
        "turn_count":        0,
        "derived_topics":    get_client_topics(),
        "last_audio_processed": None, # hash of last recording handled
        "audio_played_keys": set(),  # track which message audios have been played
        "history_summary":   "",     # rolling summary of the conversation
        "final_summary":     None,   # final wrap-up summary
        "pending_completion": False, # Flag to trigger end after processing current turn
        "spoken_language":   "Auto-Detect",
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
        st.markdown("## 📊 Session Stats")
        client_name = st.session_state["selected_client"]["Client"] if st.session_state["selected_client"] else "None"
        st.markdown(f"**Client:** {client_name}")
        if st.session_state["selected_client"]:
            topics = st.session_state["derived_topics"].get(st.session_state["selected_client"]["index"], [])
            if topics:
                st.markdown("**Available Topics:**")
                for t in topics:
                    st.markdown(f"- {t}")
        
        st.markdown(f"**Topic:** {st.session_state['selected_topic'] or 'None'}")
        st.markdown(f"**Turns:** {st.session_state['turn_count']}")
        
        st.divider()
        st.markdown("## 🎙️ Minerva Settings")

        # Debug mode toggle
        st.session_state["debug_mode"] = st.toggle(
            "Debug Mode",
            value=st.session_state["debug_mode"],
            help="Show similarity scores, retrieved chunks, and token counts",
        )

        st.markdown("### 🗣️ Language")
        st.session_state["spoken_language"] = st.selectbox(
            "Select language you are speaking in:",
            options=["Auto-Detect", "English", "Hindi", "Bengali", "Tamil", "Telugu", "Kannada", "Malayalam", "Marathi", "Gujarati", "Punjabi"],
            index=0,
            help="Locking the language can improve accuracy if auto-detect is failing."
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
    # 1. Show the Business Summary/Outcome if available
    summary = st.session_state.get("final_summary")
    if summary:
        st.markdown(
            f'<div class="summary-box" style="border-left: 4px solid #10b981; background: rgba(16, 185, 129, 0.05);">'
            f'<h3 style="color:#10b981">✨ Goal Achieved</h3>'
            f'<div style="padding:1rem;border-radius:8px;margin-bottom:1rem; border: 1px solid rgba(16,185,129,0.2)">'
            f'{summary}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # 2. Show Unknown Questions
    unknowns = st.session_state["unknown_questions"]
    if unknowns:
        items_html = "".join(f"<li>{q}</li>" for q in unknowns)
        st.markdown(
            f'<div class="summary-box" style="border-left: 4px solid #f59e0b; background: rgba(245, 158, 11, 0.05);">'
            f'<h3 style="color:#f59e0b">📋 Pending Inquiries</h3>'
            f'<p>Our team will follow up on these details:</p>'
            f'<ol>{items_html}</ol>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.success("✅ All your questions were addressed during this session!")


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

    # Pre-load vector stores
    if not st.session_state["vector_store_ok"]:
        for client in CLIENTS:
            try:
                load_vector_store(client["index"])
            except Exception as e:
                st.warning(f"Could not load index for {client['Client']}: {e}")
        st.session_state["vector_store_ok"] = True

    # Welcome greeting
    if not st.session_state.get("has_greeted", False):
        sarvam = _get_sarvam()
        industries_list = get_available_industries()
        industries_str = ", ".join(industries_list)
        greeting_text = f"Welcome to Minerva. I am your intelligent voice assistant. I specialize in {industries_str}. How can I help you today?"
        st.session_state["has_greeted"] = True
        greeting_audio = None
        try:
            with st.spinner("Initializing voice..."):
                greeting_audio = sarvam.text_to_speech(greeting_text)
        except Exception as e:
            log.error(f"Greeting TTS failed: {e}")
        
        st.session_state["conversation"].append({
            "role": "assistant",
            "content": greeting_text,
            "audio_data": greeting_audio,
        })
        st.rerun()

    # Determine if we should show the summary
    session_ended = st.session_state.get("session_ended", False)
    pending_completion = st.session_state.get("pending_completion", False)
    
    # We only show the summary if session_ended is True and we AREN'T currently processing a final message
    show_summary = session_ended and not pending_completion

    # Conversation history (using chat_message for better aesthetic)
    for i, msg in enumerate(st.session_state["conversation"]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("is_unknown"):
                st.caption("⚠️ Grounding check: Unknown in provided context.")
            
            # Autoplay last assistant message audio if not played yet
            if msg["role"] == "assistant" and "audio_data" in msg:
                audio_key = f"audio_msg_{i}"
                if audio_key not in st.session_state["audio_played_keys"]:
                    st.audio(msg["audio_data"], format="audio/wav", autoplay=True)
                    st.session_state["audio_played_keys"].add(audio_key)
                else:
                    # Render regular audio player without autoplay for history
                    st.audio(msg["audio_data"], format="audio/wav")

    if show_summary:
        st.markdown("---")
        st.markdown("## 🏁 Session Final Results")
        render_end_session_summary()
        if st.button("🔄 Start New Session", use_container_width=True):
            for key in ["unknown_questions", "conversation", "latency_log", "session_ended", "has_greeted", "audio_played_keys"]:
                if key == "session_ended" or key == "has_greeted":
                    st.session_state[key] = False
                elif key == "audio_played_keys":
                    st.session_state[key] = set()
                else:
                    st.session_state[key] = []
            st.rerun()
        return

    # Mic input
    st.markdown("---")
    st.markdown("### 🎤 Talk with Minerva")
    st.caption("Click the microphone button, ask your question, then click again to stop.")

    try:
        from audio_recorder_streamlit import audio_recorder
        audio_bytes = audio_recorder(
            text="Click to Record",
            recording_color="#e74c3c",
            neutral_color="#5b7fde",
            icon_name="microphone",
            icon_size="3x",
            pause_threshold=2.0,    # auto-stop after 2s of silence
            sample_rate=44100,
        )
    except ImportError:
        st.warning("audio-recorder-streamlit is not installed. Using file uploader as fallback.")
        uploaded = st.file_uploader("Upload WAV audio", type=["wav"])
        audio_bytes = uploaded.read() if uploaded else None

    # Process audio
    if audio_bytes and len(audio_bytes) > 2000:
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        if st.session_state["last_audio_processed"] != audio_hash:
            # Set this immediately to prevent concurrent re-entry
            st.session_state["last_audio_processed"] = audio_hash
            
            tracker = LatencyTracker()
            sarvam  = _get_sarvam()

            # Step 1: STT
            lang_map = {
                "Auto-Detect": "unknown",
                "English": "en-IN",
                "Hindi": "hi-IN",
                "Bengali": "bn-IN",
                "Tamil": "ta-IN",
                "Telugu": "te-IN",
                "Kannada": "kn-IN",
                "Malayalam": "ml-IN",
                "Marathi": "mr-IN",
                "Gujarati": "gu-IN",
                "Punjabi": "pa-IN"
            }
            requested_lang = lang_map.get(st.session_state["spoken_language"], "unknown")
            
            with st.status("Listening...", expanded=False) as status:
                try:
                    with tracker.measure("STT"):
                        transcript, det_lang = sarvam.transcribe(audio_bytes, language_code=requested_lang)
                except Exception as e:
                    log.error(f"Flow: STT failed: {e}")
                    status.update(label="Speech detection failed. Please try again.", state="error")
                    st.session_state["last_audio_processed"] = None # Reset to allow retry
                    st.stop()
                if not transcript:
                    log.info("Flow: STT returned empty transcript")
                    status.update(label="No speech detected.", state="error")
                    st.stop()
                status.update(label="Transcribed!", state="complete")
        
            log.info(f"TRANSCRIPT: {transcript} (Language: {det_lang})")
            with st.chat_message("user"):
                st.markdown(transcript)
            st.session_state["conversation"].append({"role": "user", "content": transcript})
            
            # Step 1.1: Translate to English for processing
            if str(det_lang).strip().lower() != "en-in":
                log.info(f"Flow: Translating from {det_lang} to English")
                with tracker.measure("Translate"):
                    transcript = sarvam.translate(transcript, det_lang, "en-IN")
            else:
                log.info("Flow: Transcript already in English")

            response = ""
            is_unknown = False

            # Step 2: Industry Detection (if needed)
            if not st.session_state["selected_client"]:
                with st.status("Identifying industry...", expanded=False) as status:
                    with tracker.measure("Classification (Industry)"):
                        industries = ", ".join(get_available_industries())
                        sys_prompt = INDUSTRY_CLASSIFIER_SYSTEM.format(industries=industries)
                        user_prompt = f"User Query: {transcript}"
                        choice = sarvam.chat_completion(sys_prompt, user_prompt, temperature=0.0, max_tokens=20)
                        
                        # Fuzzy match industry
                        match = None
                        low_choice = choice.lower()
                        for c in CLIENTS:
                            ind_name = c["Industry"].lower()
                            if ind_name in low_choice or low_choice in ind_name:
                                match = c
                                break
                        
                        if match:
                            st.session_state["selected_client"] = match
                            log.info(f"Flow: Industry identified as '{match['Industry']}'")
                            status.update(label=f"Industry: {match['Industry']}", state="complete")
                            
                            if len(transcript.split()) <= 2:
                                log.info("Flow: Short query - offering greeting and topics")
                                topics_list = st.session_state["derived_topics"].get(match["index"], [])
                                spoken_topics = ", ".join(topics_list[:3]) + (" and others" if len(topics_list) > 3 else "")
                                response = f"I see you're interested in {match['Industry']}. I can help you with {spoken_topics}. What would you like to know?"
                                display_response = f"I see you're interested in {match['Industry']}. I can help you with: {', '.join(topics_list)}. What would you like to know?"
                                st.session_state["pending_display_response"] = display_response
                            else:
                                log.info("Flow: Long query detected - proceeding to RAG immediately")
                        else:
                            log.info("Flow: Industry match failed")
                            response = f"I am sorry, I currently only specialize in {industries}. Please let me know which of these you are interested in."
                            status.update(label="Unknown Industry", state="error")
            else:
                log.info("Flow: Industry already selected")
            
            if st.session_state["selected_client"] and not response:
                client = st.session_state["selected_client"]
                topics_list = st.session_state["derived_topics"].get(client["index"], [])
                topics_str = ", ".join(topics_list)
                
                with st.status("Checking scope...", expanded=False) as status:
                    # Scope Detection
                    with tracker.measure("Classification (Scope)"):
                        scope_sys = SCOPE_CLASSIFIER_SYSTEM.format(
                            industry=client['Industry'],
                            topics=topics_str,
                            query=transcript
                        )
                        scope_choice = sarvam.chat_completion(scope_sys, f"User Query: {transcript}", temperature=0.0, max_tokens=10)
                    if "RELATED" in scope_choice.upper():
                        log.info(f"Flow: Query is within scope for '{client['Industry']}'")
                        st.session_state["turn_count"] += 1
                        
                        # Topic Detection (Advisory only)
                        with tracker.measure("Classification (Topic)"):
                            topics = ", ".join(st.session_state["derived_topics"].get(client["index"], []))
                            topic_sys = TOPIC_CLASSIFIER_SYSTEM.format(industry=client['Industry'], topics=topics)
                            topic_user = f"Topics: {topics}\nUser Query: {transcript}"
                            topic_choice = sarvam.chat_completion(topic_sys, topic_user, temperature=0.0, max_tokens=30)
                        
                        # Even if topic matches OUT_OF_SCOPE, we proceed with RAG if industry matched
                        if topic_choice.upper() != "OUT_OF_SCOPE":
                            log.info(f"Flow: Topic identified as '{topic_choice}'")
                            st.session_state["selected_topic"] = topic_choice
                            status.update(label=f"Topic: {topic_choice}", state="complete")
                        else:
                            log.info("Flow: Topic classifier returned OUT_OF_SCOPE but proceeding with RAG")
                            status.update(label=f"Industry query: {client['Industry']}", state="complete")
                        
                        # Step 4: RAG
                        with tracker.measure("Retrieval"):
                            chunks = retrieve(transcript, client["index"], top_k=3)
                        
                        # Decide if we should proceed to LLM
                        # We proceed if: 
                        # 1. We found some chunks with decent scores
                        # 2. It's a conversational turn (short or refers to scheduling/next steps)
                        scheduling_keywords = ["visit", "call", "appointment", "friday", "monday", "tuesday", "wednesday", "thursday", "saturday", "sunday", "morning", "afternoon", "evening", "time", "date", "schedule"]
                        is_likely_continuation = len(transcript.split()) <= 8 and (
                            any(word in transcript.lower() for word in ["yes", "yeah", "ok", "sure", "elaborate", "tell", "explain", "more", "details"]) or
                            any(word in transcript.lower() for word in scheduling_keywords)
                        )
                        
                        # If we are deep in the conversation (turn 3+), we trust the scope classifier and history more
                        is_goal_steering_phase = st.session_state["turn_count"] >= 3
                        
                        if (chunks and chunks[0]["score"] > 0.15) or is_likely_continuation or is_goal_steering_phase:
                            log.info(f"Flow: Proceeding to LLM. Chunks: {len(chunks)}, Continuation: {is_likely_continuation}, GoalPhase: {is_goal_steering_phase}")
                            with tracker.measure("LLM"):
                                # Use turn count and summary
                                goal_text = client["Goal"]
                                if st.session_state["turn_count"] >= 5:
                                    goal_steer = f"STRONG PUSH: {goal_text}. Lead the user to complete this now."
                                elif st.session_state["turn_count"] >= 1:
                                    goal_steer = f"Nudge towards: {goal_text}"
                                else:
                                    goal_steer = "None"

                                curr_summary = st.session_state.get("history_summary", "")
                                if not curr_summary:
                                    conv = st.session_state["conversation"]
                                    start_idx = 1 if len(conv) > 1 and conv[0]["role"] == "assistant" else 0
                                    recent_msgs = [f"{m['role']}: {m['content']}" for m in conv[start_idx:][-4:]]
                                    curr_summary = "Previous turns: " + " | ".join(recent_msgs)

                                sys_msg = SYSTEM_PROMPT.format(summary=curr_summary, goal=goal_steer)
                                user_msg = build_rag_prompt(chunks, transcript)
                                response = sarvam.chat_completion(sys_msg, user_msg, temperature=0.3)
                                
                                # Check for completion signal
                                if "[COMPLETE]" in response:
                                    response = response.replace("[COMPLETE]", "").strip()
                                    # Set PENDING completion so we process THIS turn's audio first
                                    st.session_state["pending_completion"] = True
                                    
                                    # Generate final business summary
                                    log.info("Flow: Generating final session summary")
                                    with tracker.measure("Summarize"):
                                        full_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state["conversation"]])
                                        sum_prompt = f"Summarize this customer conversation into 3 bullet points: Main interest, Key details provided, and Business Outcome (e.g. appointment booked for Friday). History:\n{full_history}"
                                        st.session_state["final_summary"] = sarvam.chat_completion("You are a business summarizer.", sum_prompt)
                        else:
                            log.info("Flow: RAG found no relevant information and not a conversational turn")
                            is_unknown = True
                            response = "I got your topic of interest, but I do not have specific information about it in my knowledge base. I have logged this and can arrange a follow-up."
                            st.session_state["unknown_questions"].append(transcript)
                    else:
                        log.info("Flow: Scope classifier returned GENERAL/OFF-TOPIC")
                        response = f"I am sorry, I can only assist with inquiries related to {client['Industry']}. Can I help you with any more questions on this topic?"
                        status.update(label="Out of Industry Scope", state="error")

            # Step 5: Output (TTS)
            if response:
                # Use display version if we saved one
                ui_text = st.session_state.pop("pending_display_response", response)
                
                # Translate back if needed
                if str(det_lang).strip().lower() != "en-in":
                    log.info(f"Flow: Translating response back to {det_lang}")
                    with tracker.measure("Translate"):
                        ui_text = sarvam.translate(ui_text, "en-IN", det_lang)
                        response = sarvam.translate(response, "en-IN", det_lang)
                
                audio_data = None
                try:
                    with tracker.measure("TTS"):
                        audio_data = sarvam.text_to_speech(response, det_lang)
                except Exception as e:
                    log.error(f"Flow: TTS failed, proceeding with text only. Error: {e}")
                
                # Store in history WITH audio (optional) for replay on rerun
                msg_entry = {
                    "role": "assistant", 
                    "content": ui_text, 
                    "is_unknown": is_unknown
                }
                if audio_data:
                    msg_entry["audio_data"] = audio_data
                st.session_state["conversation"].append(msg_entry)

                # Finalize session if pending
                if st.session_state.get("pending_completion"):
                    st.session_state["session_ended"] = True
                    st.session_state["pending_completion"] = False
                
                # Turn Management: Summarize every 3 turns to prevent overflow
                if st.session_state["turn_count"] % 3 == 0 and st.session_state["turn_count"] > 0:
                    log.info("Flow: Summarizing history to prevent memory overflow")
                    prev_sum = st.session_state.get("history_summary", "")
                    hist_str = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state["conversation"][-6:]])
                    
                    if prev_sum:
                        sum_prompt = f"Current Summary: {prev_sum}\n\nNew messages:\n{hist_str}\n\nUpdate the summary to include key info from new messages. Keep it to 2-3 sentences."
                    else:
                        sum_prompt = f"Summarize this conversation concisely in 2 sentences:\n{hist_str}"
                        
                    new_summary = sarvam.chat_completion("You are a expert summarizer.", sum_prompt, max_tokens=150)
                    st.session_state["history_summary"] = new_summary
                    
                    # Optional: Prune old messages if needed, but keeping current for UI display
                    # If UI becomes slow, we could clear conversation and only show summary.
                
                # Mark turn limit steering (handled above in goal_steer logic)
                if st.session_state["turn_count"] >= 3:
                    log.info("Flow: Goal steering active")
                
                # Render latency before rerun
                st.session_state["latency_log"].append(tracker.all())

                # Force rerun to update UI (Sidebar AND Chat History with new audio)
                log.info("Flow: Rerunning to update UI")
                st.rerun()

    # Show latest latency log
    if st.session_state["latency_log"]:
        render_latency_panel(st.session_state["latency_log"][-1])

    # End Conversation button
    st.markdown("---")
    col1, _ = st.columns([1, 4])
    with col1:
        if st.button("⛔️ End Conversation"):
            st.session_state["session_ended"] = True
            st.rerun()


if __name__ == "__main__":
    main()
