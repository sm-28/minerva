import time
import logging
from contextlib import contextmanager
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
from pathlib import Path
from datetime import datetime

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

import threading

class SessionFileHandler(logging.Handler):
    """
    A logging handler that routes log records to session-specific files.
    The filename includes a human-readable timestamp and the session ID.
    """
    def __init__(self, log_dir="logs"):
        super().__init__()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self._handlers = {}
        self._lock = threading.Lock()

    def emit(self, record):
        # We rely on ContextFilter to have injected session_id
        session_id = getattr(record, 'session_id', 'no-session')
        
        # We only create files for actual Streamlit sessions
        if session_id == 'no-session':
            return

        with self._lock:
            if session_id not in self._handlers:
                # Human readable timestamp: YYYY-MM-DD_HH-MM-SS
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                # Filename: session_YYYY-MM-DD_HH-MM-SS_sid.log
                log_file = self.log_dir / f"session_{timestamp}_{session_id[:8]}.log"
                
                handler = logging.FileHandler(log_file, encoding='utf-8')
                if self.formatter:
                    handler.setFormatter(self.formatter)
                self._handlers[session_id] = handler
            
            self._handlers[session_id].emit(record)

    def close(self):
        with self._lock:
            for h in self._handlers.values():
                h.close()
            self._handlers.clear()
        super().close()

# Global setup flag
_logging_initialized = False
_logging_lock = threading.Lock()

def get_logger(name: str) -> logging.Logger:
    """Return a named logger, ensuring the root logger is configured for session files."""
    global _logging_initialized
    
    with _logging_lock:
        if not _logging_initialized:
            root = logging.getLogger()
            root.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [U:%(user_id)s] [S:%(session_id)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S"
            )

            # 1. Console Handler
            console_handler = logging.StreamHandler()
            console_handler.addFilter(ContextFilter())
            console_handler.setFormatter(formatter)
            root.addHandler(console_handler)

            # 2. Session File Handler
            session_handler = SessionFileHandler()
            session_handler.addFilter(ContextFilter())
            session_handler.setFormatter(formatter)
            root.addHandler(session_handler)

            _logging_initialized = True
            
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
        
        log = get_logger("utils")
        if r.status_code == 250:
            log.info(f"OTP email sent successfully to {to_email}")
            return True
        else:
            log.error(f"Failed to send OTP to {to_email}. SMTP Status: {r.status_code}")
            return False
            
    except Exception as e:
        log = get_logger("utils")
        log.error(f"Failed to send OTP to {to_email}. Error: {e}")
        return False
