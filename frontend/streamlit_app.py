"""
Robust Todo Streamlit – v2
==========================
Adds **hard blocking guards** so that **no oversized input ever reaches the backend**:
    • Double‑checked validation inside the *submit* handler (server‑side) – even if the UI
      button is somehow triggered, the payload is silently dropped and a helpful
      error message appears instead.
    • Same guard added to the *Add Task* form.

All other structure (token counting, separation of concerns, error handling) is kept.
Optional dependency `tiktoken` still provides exact token counts.
"""

import os
import logging
from typing import List, Dict, Optional, Callable
import math
import time as time

import streamlit as st
import requests
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 🔧  Configuration & Constants
# -----------------------------------------------------------------------------
load_dotenv()
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://backend:8000")

# Character limits
MAX_TITLE_LEN = 50
MAX_DESC_LEN = 150
MAX_DUE_LEN   = 50
# Token limit (chat)
MAX_CHAT_TOKENS = 3_000

# -----------------------------------------------------------------------------
# 🧮  Token utilities
# -----------------------------------------------------------------------------
try:
    import tiktoken  # type: ignore
    enc = tiktoken.get_encoding("cl100k_base")
    def token_len(text: str) -> int:  # exact
        return len(enc.encode(text))
except ModuleNotFoundError:
    logging.warning("tiktoken missing – using char≈token/4 heuristic.")
    def token_len(text: str) -> int:  # rough
        return math.ceil(len(text) / 4)

# -----------------------------------------------------------------------------
# 🛠  Backend helpers
# -----------------------------------------------------------------------------

def _safe_request(fn: Callable[[], requests.Response]) -> Optional[Dict]:
    try:
        res = fn(); res.raise_for_status(); return res.json()
    except Exception as err:
        st.error(f"Backend error: {err}")
        logging.exception(err)
        return None

def fetch_tasks() -> List[Dict]:
    data = _safe_request(lambda: requests.get(f"{BACKEND_URL}/tasks"))
    return data or []

def chat_backend(message: str) -> Optional[Dict]:
    return _safe_request(lambda: requests.post(f"{BACKEND_URL}/chat", json={"message": message}))

# -----------------------------------------------------------------------------
# ✅  Validation helpers
# -----------------------------------------------------------------------------
within_chars = lambda txt, lim: len(txt.strip()) <= lim
within_tokens = lambda txt, lim: token_len(txt) <= lim

# -----------------------------------------------------------------------------
# 🎨  UI components
# -----------------------------------------------------------------------------

def tasks_panel():
    """Render the left column – task list plus “Add Task” form with robust length guards."""
    # Reset the form if a previous oversized submission was discarded
    if st.session_state.pop("reset_task_form", False):
        for key in ("task_title_input", "task_desc_input", "task_due_input"):
            st.session_state.pop(key, None)

    st.header("Your Tasks")

    # Show existing tasks
    tasks = fetch_tasks()
    for t in tasks:
        st.markdown("---")
        st.markdown(f"**• {t['title']}**")
        if t.get("description"):
            st.markdown(f"**Description:** {t['description']}")
        if t.get("due_date"):
            st.markdown(f"**Due:** {t['due_date']}")
        st.markdown(f"_Created: {t['created_at']}  |  Updated: {t['updated_at']}_")

        if st.button("Delete", key=f"del_{t['id']}"):
            if chat_backend(f"Please delete task #{t['id']}"):
                st.rerun()

    if not tasks:
        st.info("No tasks available.")

    st.markdown("---")
    st.subheader("Add a new task")

    with st.form("add_task", clear_on_submit=True):
        title_input = st.text_input(
            "Title",
            key="task_title_input",
            max_chars=MAX_TITLE_LEN
        )
        desc_input = st.text_area(
            "Description",
            key="task_desc_input",
            max_chars=MAX_DESC_LEN
        )
        due_input = st.text_input(
            "Due (e.g. 'tomorrow at 9 am')",
            key="task_due_input",
            max_chars=MAX_DUE_LEN
        )

        # UI-time validation
        is_title_valid_ui = len(title_input) <= MAX_TITLE_LEN
        is_desc_valid_ui  = len(desc_input)  <= MAX_DESC_LEN
        is_due_valid_ui   = len(due_input)   <= MAX_DUE_LEN

        if not is_title_valid_ui:
            st.warning(f"Title too long – max {MAX_TITLE_LEN} chars.")
        if not is_desc_valid_ui:
            st.warning(f"Description too long – max {MAX_DESC_LEN} chars.")
        if not is_due_valid_ui:
            st.warning(f"Due date too long – max {MAX_DUE_LEN} chars.")

        can_submit_form = is_title_valid_ui and is_desc_valid_ui and is_due_valid_ui
        submit_pressed = st.form_submit_button("Add via AI", disabled=not can_submit_form)

        if submit_pressed:
            # If somehow still invalid, discard and reset
            if not can_submit_form:
                st.warning("Task discarded – one or more fields were too long. Please try again.")
                st.session_state["reset_task_form"] = True
                time.sleep(2)
                st.rerun()

            # Final hard‐stop in case of race
            title_too_long = len(title_input) > MAX_TITLE_LEN
            desc_too_long  = len(desc_input)  > MAX_DESC_LEN
            due_too_long   = len(due_input)   > MAX_DUE_LEN

            if title_too_long or desc_too_long or due_too_long:
                errors = []
                if title_too_long:
                    errors.append(f"Title length {len(title_input)} > {MAX_TITLE_LEN}")
                if desc_too_long:
                    errors.append(f"Description length {len(desc_input)} > {MAX_DESC_LEN}")
                if due_too_long:
                    errors.append(f"Due-date length {len(due_input)} > {MAX_DUE_LEN}")
                st.error("Task not added: " + "; ".join(errors))
                st.session_state["reset_task_form"] = True
                time.sleep(3)
                st.stop()

            # All good – trim and send to backend
            title_clean = title_input.strip()
            desc_clean  = desc_input.strip()
            due_clean   = due_input.strip()
            prompt = (
                f"Please create a new task titled '{title_clean}' "
                f"with description '{desc_clean}' and due date '{due_clean}'."
            )
            if chat_backend(prompt):
                st.rerun()
            else:
                st.error("Backend reported an issue adding the task.")
                time.sleep(2)


def chat_panel():
    """Right-hand column – chat UI with self-resetting draft box."""

    # ------------------------------------------------------------------
    # ⬅️  Pre-render housekeeping – clear stale oversize draft
    # ------------------------------------------------------------------
    if st.session_state.pop("reset_chat", False):  # flag set on previous run
        st.session_state.pop("chat_input", None)  # remove draft before widget exists

    st.header("💬 Chat with AI")

    hist = st.session_state.setdefault("history", [])
    for msg in hist:
        role = "You" if msg["role"] == "user" else "AI"
        st.markdown(f"**{role}:** {msg['text']}")

    # ------------------------------------------------------------------
    # 📥  Draft & submission form
    # ------------------------------------------------------------------
    with st.form("chat_form", clear_on_submit=True):
        user_msg = st.text_area("Your message…", key="chat_input")
        tok_cnt  = token_len(user_msg)
        st.caption(f"{tok_cnt}/{MAX_CHAT_TOKENS} tokens")

        if tok_cnt > MAX_CHAT_TOKENS:
            st.warning("Message too long – please shorten to ≤ 3 000 tokens.")
            

        can_send = tok_cnt <= MAX_CHAT_TOKENS
        send = st.form_submit_button("Send", disabled=not can_send)

        # ------------------------------------------------------------------
        # 🚦  Submission handling
        # ------------------------------------------------------------------
        if send:
            if not can_send:  # Should not happen; double-check anyway
                st.warning("Message discarded – too many tokens. Please try again.")
                st.session_state["reset_chat"] = True  # trigger reset on next run
                time.sleep(2)
                st.rerun()

            # ✅  Valid submission
            hist.append({"role": "user", "text": user_msg})
            resp = chat_backend(user_msg)
            reply = resp.get("chat_response") if resp and "chat_response" in resp else (resp or "No response")
            hist.append({"role": "assistant", "text": reply})
            # clear_on_submit already empties widget draft, no need to reset
            st.rerun()

# -----------------------------------------------------------------------------
# 🚀  Main
# -----------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="AI Todo App", layout="wide")
    st.title("🛠 AI‑Powered Todo List")

    col_left, col_right = st.columns(2)
    with col_left:  tasks_panel()
    with col_right: chat_panel()

if __name__ == "__main__":
    main()
