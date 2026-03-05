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


SCOPE_CLASSIFIER_SYSTEM = """You are a scope classifier for a professional assistant in the {industry} sector.
User Query: {query}
Conversation Summary: {summary}

Task: Determine if the User Query is relevant to the professional domain of {industry} or the current business conversation.

1. Output 'INDUSTRY_SPECIFIC' if the query:
   - Relates to {industry} services, expertise, products, or company information.
   - Is a logical continuation, confirmation, or action request (like scheduling) based on the session summary.
   - Specifically addresses business-related inquiries within this domain.

2. Output 'GENERAL' if the query:
   - Is a standalone greeting or social pleasantry.
   - Concerns a completely unrelated industry, generic consumer products, or general knowledge topics outside this business context.
   - Is irrelevant to the professional role of a representative in {industry}.

Output ONLY 'INDUSTRY_SPECIFIC' or 'GENERAL'.
"""

# New RAG System Prompt
SYSTEM_PROMPT = """
You are representative of the company. 
Conversation Summary: {summary}

INSTRUCTIONS:
1. Answer using the provided context and the summary.
2. ADHERE TO NATURAL SPEECH: Speak like a human on a phone call. Use fluid transitions instead of "1, 2, 3" or "First, second".
3. NEVER use numbered lists, bullet points, or mechanical lists (e.g., "1. Topic, 2. Topic"). Use natural phrasing like "either X or Y" or "including both A and B".
4. Do NOT repeat your initial greeting or the list of industries you specialize in.
5. If the user is responding with a confirmation, affirmation (e.g. "Yes", "Sure"), or following up on a task (e.g. scheduling, booking), use the Conversation Summary to provide a natural response.
6. If the information is missing from both the context and the summary, say exactly: "NO_INFO_AVAILABLE"
7. Respond in first person, concisely (approx 20 words).
8. Usually end with a question to keep things moving, UNLESS the goal is fully achieved.
9. CRITICAL CLOSURE RULE: Trigger completion ONLY when a specific commitment is FINALIZED. 
   - ACHIEVED: "Yes, tomorrow at 3 PM is perfect" or "Great, Friday at 10 AM is noted".
   - NOT ACHIEVED: "Yes please", "Book a time", "I want a consultation", "Tell me more".
10. If the user provided a time or detail (e.g., "Tomorrow 3 PM"), ACKNOWLEDGE IT SPECIFICALLY. 
11. To complete: thank the user warmly, confirm the final details (e.g., "Great, I've noted your appointment for Friday at 10 AM. Talk soon!"), and append exactly "[COMPLETE]" at the end.
12. Ensure your response is aligned with this steering instruction: {goal}.
"""

VOICE_MAPPING = {
    "Female - Professional": "anushka",
    "Female - Composed": "vidya",
    "Female - Casual": "manisha",
    "Male - Professional": "hitesh",
    "Male - Bold": "karun"
}

SPEED_MAPPING = {
    "Slower": 0.8,
    "Slow": 0.9,
    "Normal": 1.0,
    "Fast": 1.1,
    "Faster": 1.2
}

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
            
            # Clean up derived topics (strip numbering, bullets, etc.)
            derived = []
            for t in response.split("\n"):
                t = t.strip()
                if t:
                    # Strip "1. ", "2) ", "- ", etc.
                    t = re.sub(r'^\s*[\d\.\-\*\)]+\s*', '', t)
                    if t:
                        derived.append(t)
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
        "turn_count":        0,
        "derived_topics":    get_client_topics(),
        "last_audio_processed": None, # hash of last recording handled
        "audio_played_keys": set(),  # track which message audios have been played
        "history_summary":   "",     # rolling summary of the conversation
        "final_summary":     None,   # final wrap-up summary
        "pending_completion": False, # Flag to trigger end after processing current turn
        "spoken_language":   "Auto-Detect",
        "tts_speaker":       "anushka",
        "tts_speed":         1.0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _get_sarvam() -> SarvamClient:
    if st.session_state["sarvam"] is None:
        st.session_state["sarvam"] = SarvamClient()
    return st.session_state["sarvam"]


def reset_session():
    """Reset conversation and session-specific state without logging out."""
    for key in ["unknown_questions", "conversation", "latency_log", "session_ended", "has_greeted", "audio_played_keys", "selected_client", "turn_count", "history_summary", "final_summary", "pending_completion"]:
        if key in ["session_ended", "has_greeted", "pending_completion"]:
            st.session_state[key] = False
        elif key == "audio_played_keys":
            st.session_state[key] = set()
        elif key in ["selected_client", "history_summary", "final_summary"]:
            st.session_state[key] = None if key != "history_summary" else ""
        elif key == "turn_count":
            st.session_state[key] = 0
        else:
            st.session_state[key] = []


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
        
        st.markdown(f"**Turns:** {st.session_state['turn_count']}")
        
        if st.session_state["conversation"] and not st.session_state["session_ended"]:
            if st.button("⛔️ End Conversation", use_container_width=True, type="primary"):
                st.session_state["session_ended"] = True
                # Generate final summary immediately if it doesn't exist
                if not st.session_state.get("final_summary"):
                    log.info("Flow: Manual end - generating final session summary")
                    sarvam = _get_sarvam()
                    full_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state["conversation"]])
                    sum_prompt = f"Summarize this customer conversation into 3 bullet points: Main interest, Key details provided, and Business Outcome. History:\n{full_history}"
                    st.session_state["final_summary"] = sarvam.chat_completion("You are a business summarizer.", sum_prompt)
                st.rerun()
        
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

        st.markdown("### 🎭 Voice")
        voice_names = list(VOICE_MAPPING.keys())
        default_voice_idx = 0
        current_speaker = st.session_state.get("tts_speaker", "anushka")
        for i, (name, speaker) in enumerate(VOICE_MAPPING.items()):
            if speaker == current_speaker:
                default_voice_idx = i
                break
        
        selected_voice_name = st.selectbox("Change Voice:", options=voice_names, index=default_voice_idx)
        st.session_state["tts_speaker"] = VOICE_MAPPING[selected_voice_name]

        st.markdown("### ⚡ Speed")
        speed_names = list(SPEED_MAPPING.keys())
        default_speed_idx = 2 # Normal
        current_speed = st.session_state.get("tts_speed", 1.0)
        for i, (name, val) in enumerate(SPEED_MAPPING.items()):
            if abs(val - current_speed) < 0.01:
                default_speed_idx = i
                break
        
        selected_speed_name = st.selectbox("Change Speed:", options=speed_names, index=default_speed_idx)
        st.session_state["tts_speed"] = SPEED_MAPPING[selected_speed_name]

        st.divider()

        if st.session_state["selected_client"]:
            st.markdown("### 🏢 Industry")
            industry_names = get_available_industries()
            current_industry = st.session_state["selected_client"]["Industry"]
            try:
                industry_idx = industry_names.index(current_industry)
            except ValueError:
                industry_idx = 0
            
            new_industry = st.selectbox("Switch Industry:", options=industry_names, index=industry_idx)
            if new_industry != current_industry:
                # Find the matching client config
                for c in CLIENTS:
                    if c["Industry"] == new_industry:
                        reset_session()
                        st.session_state["selected_client"] = c
                        st.rerun()
        
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

    # 1. Industry Selection (mandatory before greeting)
    if not st.session_state["selected_client"]:
        st.subheader("Select your industry to begin")
        cols = st.columns([1, 2, 1])
        with cols[1]:
            with st.form("select_industry_form"):
                industry_names = get_available_industries()
                selected_ind = st.selectbox("Industry:", options=["Select..."] + industry_names)
                submit = st.form_submit_button("Start Minerva", use_container_width=True)
                
                if submit and selected_ind != "Select...":
                    for c in CLIENTS:
                        if c["Industry"] == selected_ind:
                            st.session_state["selected_client"] = c
                            # Load only selected index
                            try:
                                with st.spinner(f"Loading {selected_ind} knowledge base..."):
                                    load_vector_store(c["index"])
                                st.session_state["vector_store_ok"] = True
                            except Exception as e:
                                st.error(f"Could not load index for {selected_ind}: {e}")
                                st.stop()
                            st.rerun()
            st.info("Minerva will talk to you within the context of the selected industry.")
            st.stop()

    # Welcome greeting (after industry selection)
    if not st.session_state.get("has_greeted", False):
        sarvam = _get_sarvam()
        client = st.session_state["selected_client"]
        industry = client["Industry"]
        topics_list = st.session_state["derived_topics"].get(client["index"], [])
        
        if len(topics_list) > 1:
            topics_phrase = ", ".join(topics_list[:2]) + f", and {topics_list[2]}" if len(topics_list) >= 3 else " and ".join(topics_list[:2])
        elif topics_list:
            topics_phrase = topics_list[0]
        else:
            topics_phrase = "various industry related inquiries"

        greeting_text = f"Welcome to Minerva! I am your Intellignt voice assistant for {industry}. I can help you with things like {topics_phrase}. How can I assist you today?"
        st.session_state["has_greeted"] = True
        greeting_audio = None
        try:
            with st.spinner("Initializing voice..."):
                greeting_audio = sarvam.text_to_speech(
                    greeting_text, 
                    speaker=st.session_state["tts_speaker"], 
                    pace=st.session_state["tts_speed"]
                )
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

    # Display topics prominently if conversation just started
    if len(st.session_state["conversation"]) <= 1 and not show_summary:
        client = st.session_state["selected_client"]
        topics_list = st.session_state["derived_topics"].get(client["index"], [])
        if topics_list:
            st.markdown(f"### 💡 Topics I can help you with:")
            cols = st.columns(len(topics_list[:5]))
            for i, topic in enumerate(topics_list[:5]):
                with cols[i]:
                    st.markdown(f'<div class="metric-tile" style="height: 100%; display: flex; align-items: center; justify-content: center; font-weight: 500;">{topic}</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

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

            if st.session_state["selected_client"]:
                client = st.session_state["selected_client"]
                topics_list = st.session_state["derived_topics"].get(client["index"], [])
                topics_str = ", ".join(topics_list)
                
                with st.status("Checking scope...", expanded=False) as status:
                    # Scope Detection
                    with tracker.measure("Classification"):
                        curr_summary = st.session_state.get("history_summary", "")
                        scope_sys = SCOPE_CLASSIFIER_SYSTEM.format(
                            industry=client['Industry'],
                            query=transcript,
                            summary=curr_summary
                        )
                        scope_choice = sarvam.chat_completion(scope_sys, f"User Query: {transcript}", temperature=0.0, max_tokens=10)
                    st.session_state["turn_count"] += 1
                    
                    # Step 4: RAG
                    with tracker.measure("Retrieval"):
                        chunks = retrieve(transcript, client["index"], top_k=3)
                    
                    # Evaluation Logic for the 4 Cases
                    # Case determinants
                    is_industry_specific = "INDUSTRY_SPECIFIC" in scope_choice.upper()
                    
                    # We consider info "available" if:
                    # 1. We found some chunks with decent scores
                    # 2. It's a conversational turn (short or refers to scheduling/next steps)
                    # 3. We are deep in the conversation (turn 3+), trusting the session history
                    scheduling_keywords = ["visit", "call", "appointment", "friday", "monday", "tuesday", "wednesday", "thursday", "saturday", "sunday", "morning", "afternoon", "evening", "time", "date", "schedule"]
                    is_likely_continuation = len(transcript.split()) <= 8 and (
                        any(word in transcript.lower() for word in ["yes", "yeah", "ok", "sure", "elaborate", "tell", "explain", "more", "details"]) or
                        any(word in transcript.lower() for word in scheduling_keywords)
                    )
                    is_goal_steering_phase = st.session_state["turn_count"] >= 3
                    
                    info_available = (chunks and chunks[0]["score"] > 0.15) or is_likely_continuation or is_goal_steering_phase
                    
                    proceed_to_llm = False
                    
                    if not is_industry_specific and not info_available:
                        # Case 1: Not Industry Specific & Info NOT available: Deny gently
                        response = f"I am sorry, I can only assist with inquiries related to {client['Industry']}. Can I help you with any more questions on this topic?"
                        status.update(label="Out of Industry Scope", state="error")
                    
                    elif not is_industry_specific and info_available:
                        # Case 2: Not Industry Specific & Info available: Provide Grounded Results
                        proceed_to_llm = True
                    
                    elif is_industry_specific and info_available:
                        # Case 3: Industry Specific & Info available: Provide Grounded Results
                        proceed_to_llm = True
                        
                    elif is_industry_specific and not info_available:
                        # Case 4: Industry Specific & Info NOT available: Appreciate/acknoweldge and add to tracker
                        response = f"I appreciate your interest in this detail about our {client['Industry']} services. I don't have that specific information in my current knowledge base. I've logged this for a senior representative to review and provide info. Is there anything else I can help you with?"
                        st.session_state["unknown_questions"].append(transcript)
                        is_unknown = True
                        status.update(label="Info not available (logged)", state="warning")

                    if proceed_to_llm:
                        log.info(f"Flow: Proceeding to LLM. Chunks: {len(chunks)}, Continuation: {is_likely_continuation}, GoalPhase: {is_goal_steering_phase}")
                        status.update(label=f"Responding for {client['Industry']}...", state="complete")
                        with tracker.measure("LLM"):
                            # Use turn count and summary
                            goal_text = client["Goal"]
                            if st.session_state["turn_count"] >= 5:
                                goal_steer = f"STRONG PUSH: {goal_text}. Lead the user to complete this now."
                            elif st.session_state["turn_count"] >= 2:
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
                            
                            # Fallback if LLM decides the info is not actually in the context
                            elif "NO_INFO_AVAILABLE".lower() in response.lower():
                                log.info("Flow: LLM indicated info missing. Triggering Case 4 logic.")
                                is_unknown = True
                                response = f"I appreciate your interest in this detail about our {client['Industry']} services. I don't have that specific information in my current knowledge base. I've logged this for a senior representative to review and provide info. Is there anything else I can help you with?"
                                st.session_state["unknown_questions"].append(transcript)
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
                        audio_data = sarvam.text_to_speech(
                            response, 
                            det_lang,
                            speaker=st.session_state["tts_speaker"],
                            pace=st.session_state["tts_speed"]
                        )
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
                
                # Turn Management: Summarize every 2 turns if turn count > 2 to stay sharp
                if st.session_state["turn_count"] > 2:
                    log.info("Flow: Updating history summary for continuity")
                    prev_sum = st.session_state.get("history_summary", "")
                    # Fetch last 4 messages (2 turns) for current context
                    recent_msgs = [f"{m['role']}: {m['content']}" for m in st.session_state["conversation"][-4:]]
                    hist_str = "\n".join(recent_msgs)
                    
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
    col1, _ = st.columns([1, 3])
    with col1:
        if st.button("⛔️ End Conversation", use_container_width=True, type="primary"):
            st.session_state["session_ended"] = True
            st.rerun()


if __name__ == "__main__":
    main()
