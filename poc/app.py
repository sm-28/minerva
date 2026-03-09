import io
import os
import sys
import time
import re
import logging
import hashlib
import base64
import datetime

import streamlit as st
from whatsapp_input import whatsapp_input

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
1. Answer using the provided context and the summary not exceeding 30 words.
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
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* WhatsApp Dark Theme Background */
    [data-testid="stAppViewContainer"] {
        background-color: #0b141a !important;
        background-image: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png') !important;
        background-blend-mode: overlay !important;
        background-attachment: fixed !important;
    }

    /* --- Layout Fixes --- */
    
    .chat-toolbar {
        background: #202c33 !important;
        height: 110px !important;
        padding: 5px 20px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        border-bottom: 2px solid #2a3942 !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 99999 !important;
        text-align: center !important;
        transition: all 0.3s ease !important;
    }
    
    .chat-toolbar.shrunk {
        height: 70px !important;
        flex-direction: row !important;
        align-items: center !important;
    }
    
    .chat-toolbar h1 {
        font-size: 1.8rem !important;
        color: #e9edef !important;
        margin: 0 !important;
        padding: 5px 0 0 0 !important; /* Prevent top clipping */
        font-weight: 600 !important;
        line-height: 1.2 !important;
    }
    
    .whatsapp-input-fixed {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        width: 100% !important;
        background: #0b141a !important;
        background: linear-gradient(to top, #0b141a 95%, transparent) !important;
        padding: 15px 0 30px 0 !important;
        z-index: 99998 !important;
        display: flex !important;
        justify-content: center !important;
    }
    
    .whatsapp-input-wrapper {
        width: 95% !important;
        max-width: 850px !important;
    }

    [data-testid="stMainBlockContainer"], .main .block-container {
        padding-top: 170px !important; /* More space for header */
        padding-bottom: 140px !important; /* More space for input */
    }

    @media (min-width: 992px) {
        .chat-toolbar, .whatsapp-input-fixed {
            left: 120px !important;
            width: calc(100% - 120px) !important;
        }
    }

    /* --- Restored WhatsApp Elements --- */
    .whatsapp-row {
        display: flex !important;
        width: 100% !important;
        margin-bottom: 12px !important;
        padding: 0 10px !important;
    }
    .whatsapp-row.user { justify-content: flex-end !important; }
    .whatsapp-row.assistant { justify-content: flex-start !important; }

    .bubble {
        min-width: 280px;
        max-width: 85%;
        padding: 8px 12px 22px 12px;
        border-radius: 8px;
        position: relative;
        font-size: 15px;
        line-height: 1.4;
        box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
        word-wrap: break-word;
    }

    .assistant-bubble {
        background-color: #202c33 !important;
        color: #e9edef !important;
        border-top-left-radius: 0 !important;
        margin-left: 8px;
    }
    .assistant-bubble::before {
        content: "";
        position: absolute;
        top: 0;
        left: -8px;
        width: 10px;
        height: 12px;
        background-color: #202c33;
        clip-path: polygon(100% 0, 0 0, 100% 100%);
    }

    .user-bubble {
        background-color: #005c4b !important;
        color: #e9edef !important;
        border-top-right-radius: 0 !important;
        margin-right: 8px;
    }
    .user-bubble::before {
        content: "";
        position: absolute;
        top: 0;
        right: -8px;
        width: 10px;
        height: 12px;
        background-color: #005c4b;
        clip-path: polygon(0 0, 100% 0, 0 100%);
    }

    .whatsapp-time {
        font-size: 11px !important;
        color: rgba(233, 237, 239, 0.6) !important;
        position: absolute;
        bottom: 4px;
        right: 8px;
    }

    audio {
        width: 100% !important;
        height: 40px !important;
        filter: invert(100%) hue-rotate(180deg) brightness(1.2) contrast(0.85);
        opacity: 0.9;
        margin-top: 8px !important;
        border-radius: 20px;
    }

    /* Login Header Styling */
    .hero-header {
        background: #202c33;
        padding: 2rem;
        border-bottom: 1px solid #2a3942;
        margin-bottom: 2rem;
        border-radius: 12px;
        text-align: center;
    }
    .hero-header h1 { color: #e9edef; font-size: 2rem; margin: 0; }
    .hero-header p { color: #8696a0; margin-top: 10px; }

    /* Sidebar Overrides */
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background-color: #111b21 !important;
        border-right: 1px solid #2a3942;
    }
    .sidebar-sticky-header {
        position: sticky; top: 0; background: #111b21; z-index: 100;
        padding-bottom: 15px; border-bottom: 1px solid #2a3942;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #00a884 !important;
    }

    .stButton > button {
        background-color: #00a884 !important;
        color: white !important;
        border-radius: 24px !important;
        border: none !important;
    }

    /* Clean Streamlit Defaults */
    [data-testid="stHeader"], [data-testid="stFooter"], [data-testid="stChatInput"] { display: none !important; }
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
        # User Identity, Logout, and End Conversation (Sticky Top)
        user_email = st.session_state.get("user_id", "Guest")
        display_name = user_email.split("@")[0].title() if "@" in user_email else user_email.title()
        
        st.markdown(f'<div class="sidebar-sticky-header">', unsafe_allow_html=True)
        st.markdown(f"### 👋 {display_name}")
        
        col_buttons = st.columns(2)
        with col_buttons[0]:
            if st.button("Logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        with col_buttons[1]:
            if st.session_state["conversation"] and not st.session_state["session_ended"]:
                if st.button("⛔️ End", use_container_width=True, type="primary"):
                    st.session_state["session_ended"] = True
                    # Generate final summary immediately if it doesn't exist
                    if not st.session_state.get("final_summary"):
                        log.info("Flow: Manual end - generating summary")
                        sarvam = _get_sarvam()
                        full_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state["conversation"]])
                        sum_prompt = f"Summarize this customer conversation into 3 bullet points: Main interest, Key details provided, and Business Outcome. History:\n{full_history}"
                        st.session_state["final_summary"] = sarvam.chat_completion("You are a business summarizer.", sum_prompt)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Rest of the sidebar (Scrollable)
        
        # Industry selection
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
                for c in CLIENTS:
                    if c["Industry"] == new_industry:
                        reset_session()
                        st.session_state["selected_client"] = c
                        st.rerun()
            st.divider()

        st.markdown("## 📊 Session Stats")
        client_name = st.session_state["selected_client"]["Client"] if st.session_state["selected_client"] else "None"
        st.markdown(f"**Client:** {client_name}")
        st.markdown(f"**Turns:** {st.session_state['turn_count']}")
        
        # Latency tracker
        if st.session_state["latency_log"]:
            st.divider()
            st.markdown("## ⏱️ Latency Tracker")
            last = st.session_state["latency_log"][-1]
            for k, v in last.items():
                st.markdown(f"- **{k}**: `{v:.3f}s`")
            total = sum(last.values())
            st.markdown(f"- **TOTAL**: `{total:.3f}s`")
        
        st.divider()
        st.markdown("## 🎙️ Minerva Settings")

        # Debug mode toggle
        st.session_state["debug_mode"] = st.toggle(
            "Debug Mode",
            value=st.session_state["debug_mode"],
        )

        st.markdown("### 🗣️ Language")
        st.session_state["spoken_language"] = st.selectbox(
            "Select language:",
            options=["Auto-Detect", "English", "Hindi", "Bengali", "Tamil", "Telugu", "Kannada", "Malayalam", "Marathi", "Gujarati", "Punjabi"],
            index=0
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
        default_speed_idx = 2 
        current_speed = st.session_state.get("tts_speed", 1.0)
        for i, (name, val) in enumerate(SPEED_MAPPING.items()):
            if abs(val - current_speed) < 0.01:
                default_speed_idx = i
                break
        
        selected_speed_name = st.selectbox("Change Speed:", options=speed_names, index=default_speed_idx)
        st.session_state["tts_speed"] = SPEED_MAPPING[selected_speed_name]
        
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

        st.divider()
        st.caption("Minerva Voice AI [WhatsApp Edition]")


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

    # WhatsApp-style Toolbar Header
    st.markdown(
        '''
        <div class="chat-toolbar" id="minerva-header">
            <h1>🎙️ Minerva AI</h1>
            <p>Document-Grounded 24/7 Multilingual Voice AI Assistant</p>
        </div>
        <script>
            (function() {
                const targetSelectors = ['[data-testid="stAppViewContainer"]', '.main', 'section.main'];
                let container = null;
                
                function findContainer() {
                    for (const selector of targetSelectors) {
                        const el = window.parent.document.querySelector(selector);
                        if (el && el.scrollHeight > window.innerHeight) {
                            return el;
                        }
                    }
                    return window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
                }

                const header = window.parent.document.getElementById('minerva-header');
                
                // Track scroll for shrinking header
                let attempts = 0;
                const interval = setInterval(() => {
                    container = findContainer();
                    if (container || attempts > 30) {
                        clearInterval(interval);
                        if (container && header) {
                            container.addEventListener('scroll', function() {
                                if (container.scrollTop > 40) {
                                    header.classList.add('shrunk');
                                } else {
                                    header.classList.remove('shrunk');
                                }
                            }, { passive: true });
                        }
                    }
                    attempts++;
                }, 500);
            })();
        </script>
        ''',
        unsafe_allow_html=True,
    )
    
    # Topics removal as requested

    # 1. Industry Selection (mandatory before greeting)
    if not st.session_state["selected_client"]:
        cols = st.columns([1, 3, 1])
        with cols[1]:
            st.markdown('<h2 style="text-align: center; color: #e9edef; margin-top: 0; margin-bottom: 25px;">Select your industry to begin</h2>', unsafe_allow_html=True)
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

    # Topics removal as requested

    # Conversation history
    for i, msg in enumerate(st.session_state["conversation"]):
        # Get current time for the timestamp
        now = datetime.datetime.now().strftime("%H:%M")
        
        if msg["role"] == "user":
            st.markdown(f'''<div class="whatsapp-row user">
<div class="bubble user-bubble">
<div style="margin-bottom: 2px;">{msg["content"]}</div>
<div class="whatsapp-time">{now}</div>
</div>
</div>''', unsafe_allow_html=True)
        else:
            # Assistant bubble logic
            audio_html = ""
            if "audio_data" in msg:
                audio_key = f"audio_msg_{i}"
                autoplay = audio_key not in st.session_state["audio_played_keys"]
                # Convert bytes to base64 for native HTML audio tag
                b64_audio = base64.b64encode(msg["audio_data"]).decode()
                audio_html = f'''<audio controls autoplay playsinline style="width:100%; height:40px;">
<source src="data:audio/wav;base64,{b64_audio}" type="audio/wav">
</audio>'''
                if autoplay:
                    st.session_state["audio_played_keys"].add(audio_key)

            st.markdown(f'''<div class="whatsapp-row assistant">
<div class="bubble assistant-bubble">
<div style="margin-bottom: 5px;">{msg["content"]}</div>
{audio_html}
<div class="whatsapp-time">{now}</div>
</div>
</div>''', unsafe_allow_html=True)
            
            if msg.get("is_unknown"):
                st.caption("⚠️ Grounding check: Unknown in provided context.")

    if show_summary:
        st.markdown("---")
        st.markdown("## 🏁 Session Final Results")
        render_end_session_summary()
        cols = st.columns([1, 2, 1])
        with cols[1]:
            if st.button("🔄 Start New Session", use_container_width=True):
                reset_session()
                st.rerun()
        return

    # Unified WhatsApp Input Component
    st.markdown('<div class="whatsapp-input-fixed" id="whatsapp-input-outer"><div class="whatsapp-input-wrapper">', unsafe_allow_html=True)
    input_result = whatsapp_input(key="whatsapp_input_v1")
    st.markdown('</div></div>', unsafe_allow_html=True)

    chat_query = None
    audio_bytes = None

    if input_result:
        log.info(f"### INPUT DETECTED: {input_result.get('type')} | Timestamp: {input_result.get('timestamp')}")
        if input_result["type"] == "text":
            chat_query = input_result["content"]
        elif input_result["type"] == "audio":
            audio_bytes = base64.b64decode(input_result["content"])

        if chat_query or (audio_bytes and len(audio_bytes) > 2000):
            # NEW ROBUST DEDUPLICATION using timestamp from component
            event_id = input_result.get("timestamp")
            
            if event_id:
                if st.session_state.get("last_event_id") == event_id:
                    # Silence the log for same-event reruns
                    # log.info(f"Deduplication: Stopping rerun for event {event_id}")
                    st.stop()
                log.info(f"--- PROCESSING NEW EVENT: {event_id} ---")
                st.session_state["last_event_id"] = event_id
            else:
                log.warning("Received input_result without timestamp!")

            tracker = LatencyTracker()
            sarvam  = _get_sarvam()
            transcript = ""
            det_lang = "en-IN" 
            
            if chat_query:
                transcript = chat_query
                det_lang = "en-IN"
                log.info(f"PROCESSING TEXT: '{transcript}'")
                
                # Immediate visual feedback
                st.markdown(f'''<div class="whatsapp-row user">
<div class="bubble user-bubble">
<div style="margin-bottom: 2px;">{transcript}</div>
<div class="whatsapp-time">{datetime.datetime.now().strftime("%H:%M")}</div>
</div>
</div>''', unsafe_allow_html=True)
                
                st.session_state["conversation"].append({"role": "user", "content": transcript})

            elif audio_bytes:
                # Handle Audio input (STT)
                audio_hash = hashlib.md5(audio_bytes).hexdigest()
                if st.session_state["last_audio_processed"] == audio_hash:
                    st.stop()
                st.session_state["last_audio_processed"] = audio_hash
                
                lang_map = {
                    "Auto-Detect": "unknown",
                    "English": "en-IN", "Hindi": "hi-IN", "Bengali": "bn-IN",
                    "Tamil": "ta-IN", "Telugu": "te-IN", "Kannada": "kn-IN",
                    "Malayalam": "ml-IN", "Marathi": "mr-IN", "Gujarati": "gu-IN",
                    "Punjabi": "pa-IN"
                }
                requested_lang = lang_map.get(st.session_state["spoken_language"], "unknown")
                
                try:
                    with tracker.measure("STT"):
                        transcript, det_lang = sarvam.transcribe(audio_bytes, language_code=requested_lang, extension="webm")
                except Exception as e:
                    log.error(f"Flow: STT failed: {e}")
                    st.session_state["last_audio_processed"] = None
                    st.stop()
                
                if not transcript:
                    st.stop()
                log.info(f"AUDIO TRANSCRIPT: {transcript} (Language: {det_lang})")
                
                # Immediate visual feedback
                st.markdown(f'''<div class="whatsapp-row user">
<div class="bubble user-bubble">
<div style="margin-bottom: 2px;">{transcript}</div>
<div class="whatsapp-time">{datetime.datetime.now().strftime("%H:%M")}</div>
</div>
</div>''', unsafe_allow_html=True)
                
                st.session_state["conversation"].append({"role": "user", "content": transcript})
                
                # Step 1.1: Translate to English for processing if audio was in non-English
                if str(det_lang).strip().lower() != "en-in":
                    log.info(f"Flow: Translating from {det_lang} to English")
                    with tracker.measure("Translate"):
                        transcript = sarvam.translate(transcript, det_lang, "en-IN")
        
        # Proceed with reasoning for either input type
        if transcript:
            response = ""
            is_unknown = False

            if st.session_state["selected_client"]:
                client = st.session_state["selected_client"]
                
                try:
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
                    
                    # Evaluation Logic
                    is_industry_specific = "INDUSTRY_SPECIFIC" in scope_choice.upper()
                    scheduling_keywords = ["visit", "call", "appointment", "friday", "monday", "tuesday", "wednesday", "thursday", "saturday", "sunday", "morning", "afternoon", "evening", "time", "date", "schedule"]
                    is_likely_continuation = len(transcript.split()) <= 8 and (
                        any(word in transcript.lower() for word in ["yes", "yeah", "ok", "sure", "elaborate", "tell", "explain", "more", "details"]) or
                        any(word in transcript.lower() for word in scheduling_keywords)
                    )
                    is_goal_steering_phase = st.session_state["turn_count"] >= 3
                    
                    info_available = (chunks and chunks[0]["score"] > 0.15) or is_likely_continuation or is_goal_steering_phase
                    proceed_to_llm = False
                    
                    if not is_industry_specific and not info_available:
                        response = f"I am sorry, I can only assist with inquiries related to {client['Industry']}. Can I help you with any more questions on this topic?"
                    elif not is_industry_specific and info_available:
                        proceed_to_llm = True
                    elif is_industry_specific and info_available:
                        proceed_to_llm = True
                    elif is_industry_specific and not info_available:
                        response = f"I appreciate your interest in this detail about our {client['Industry']} services. I don't have that specific information in my current knowledge base. I've logged this for a senior representative to review and provide info. Is there anything else I can help you with?"
                        st.session_state["unknown_questions"].append(transcript)
                        is_unknown = True

                    if proceed_to_llm:
                        log.info(f"Flow: Proceeding to LLM. Chunks: {len(chunks)}")
                        with tracker.measure("LLM"):
                            goal_text = client["Goal"]
                            goal_steer = f"Nudge towards: {goal_text}" if st.session_state["turn_count"] >= 2 else "None"
                            if st.session_state["turn_count"] >= 5:
                                goal_steer = f"STRONG PUSH: {goal_text}. Lead the user to complete this now."

                            curr_summary = st.session_state.get("history_summary", "")
                            if not curr_summary:
                                conv = st.session_state["conversation"]
                                start_idx = 1 if len(conv) > 1 and conv[0]["role"] == "assistant" else 0
                                recent_msgs = [f"{m['role']}: {m['content']}" for m in conv[start_idx:][-4:]]
                                curr_summary = "Previous turns: " + " | ".join(recent_msgs)

                            sys_msg = SYSTEM_PROMPT.format(summary=curr_summary, goal=goal_steer)
                            user_msg = build_rag_prompt(chunks, transcript)
                            response = sarvam.chat_completion(sys_msg, user_msg, temperature=0.3)
                            
                        # Response processing
                        if "[COMPLETE]" in response:
                            response = response.replace("[COMPLETE]", "").strip()
                            st.session_state["pending_completion"] = True
                            with tracker.measure("Summarize"):
                                full_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state["conversation"]])
                                sum_prompt = f"Summarize this customer conversation into 3 bullet points: Main interest, Key details provided, and Business Outcome. History:\n{full_history}"
                                st.session_state["final_summary"] = sarvam.chat_completion("You are a business summarizer.", sum_prompt)
                        
                        elif "NO_INFO_AVAILABLE".lower() in response.lower():
                            is_unknown = True
                            response = f"I appreciate your interest in this detail about our {client['Industry']} services. I've logged this for review. Is there anything else?"
                            st.session_state["unknown_questions"].append(transcript)

                except Exception as e:
                    log.error(f"Reasoning loop fatal error: {e}")
                    response = "I encountered a technical issue. Could you please repeat that?"
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

            # ALWAYS rerun if we have a transcript (even if response generation failed)
            # This ensures the user's message is officially Part Of The History
            log.info("Flow: Rerunning to finalize turn")
            st.rerun()

    # Show latest latency log
    if st.session_state["latency_log"]:
        render_latency_panel(st.session_state["latency_log"][-1])



if __name__ == "__main__":
    main()
