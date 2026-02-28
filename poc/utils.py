import time
import logging
from contextlib import contextmanager
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

class ContextFilter(logging.Filter):
    """
    Filter that injects user_id and session_id into every log record.
    Pulls from st.session_state and Streamlit context if available.
    """
    def filter(self, record):
        # Default values
        record.user_id = "anonymous"
        record.session_id = "no-session"

        try:
            # Try to get Streamlit session ID defensively to avoid ScriptRunContext warnings
            from streamlit.runtime.scriptrunner import get_script_run_ctx as _get_ctx
            ctx = _get_ctx()
            if ctx:
                record.session_id = ctx.session_id
            
            # Try to get user ID from session state
            if "user_id" in st.session_state:
                record.user_id = st.session_state["user_id"]
        except (Exception, ImportError, RuntimeError):
            # Outside of Streamlit thread or state not ready
            pass
        return True

# Configure root logger with the new format
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clear existing handlers to avoid duplicates
if logger.hasHandlers():
    logger.handlers.clear()

handler = logging.StreamHandler()
handler.addFilter(ContextFilter())
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] [U:%(user_id)s] [S:%(session_id)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)

def get_st_session_id() -> str:
    """Return the Streamlit session ID."""
    ctx = get_script_run_ctx()
    return ctx.session_id if ctx else "no-session"


# ---------------------------------------------------------------------------
# Latency / Timing
# ---------------------------------------------------------------------------

class LatencyTracker:
    """Accumulates named timing measurements for one pipeline run."""

    def __init__(self):
        self._metrics: dict[str, float] = {}

    @contextmanager
    def measure(self, label: str):
        """Context manager that measures wall-clock duration for *label*."""
        start = time.perf_counter()
        yield
        self._metrics[label] = round(time.perf_counter() - start, 3)

    def get(self, label: str) -> float | None:
        return self._metrics.get(label)

    def all(self) -> dict[str, float]:
        return dict(self._metrics)

    def total(self) -> float:
        return round(sum(self._metrics.values()), 3)

    def summary_lines(self) -> list[str]:
        lines = [f"  {k}: {v:.3f}s" for k, v in self._metrics.items()]
        lines.append(f"  TOTAL: {self.total():.3f}s")
        return lines

# ---------------------------------------------------------------------------
# Email OTP Utilities
# ---------------------------------------------------------------------------

import emails

def send_otp_email(to_email: str, otp_code: str, smtp_user: str, smtp_password: str) -> bool:
    """
    Sends a 6-digit OTP code to the provided email address using Gmail SMTP.
    Returns True if successful, False otherwise.
    """
    try:
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="background-color: #f4f4f4; padding: 30px; border-radius: 8px; text-align: center;">
                <h2 style="color: #333;">🎙️ Minerva Voice AI</h2>
                <p style="color: #555; font-size: 16px;">Here is your one-time login code:</p>
                <div style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #2c3e50; margin: 20px 0;">
                    {otp_code}
                </div>
                <p style="color: #777; font-size: 12px;">This code will expire in 10 minutes.</p>
            </div>
        </body>
        </html>
        """
        message = emails.html(
            html=html_body,
            subject="Minerva Voice AI - Login Code",
            mail_from=("Minerva Auth", smtp_user)
        )
        
        # Configure SMTP
        r = message.send(
            to=to_email,
            smtp={'host': 'smtp.gmail.com', 'port': 465, 'ssl': True, 'user': smtp_user, 'password': smtp_password}
        )
        
        if r.status_code == 250:
            logger.info(f"OTP email sent successfully to {to_email}")
            return True
        else:
            logger.error(f"Failed to send OTP to {to_email}. SMTP Status: {r.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send OTP to {to_email}. Error: {e}")
        return False
