import os
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()

# Backend service URL (as set in .env)
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(page_title="AI Todo App", layout="wide")
st.title("🛠 AI-Powered Todo List")

col_tasks, col_chat = st.columns((1, 1))

# --- Tasks Column ---
with col_tasks:
    st.header("Your Tasks")

    # Fetch tasks
    try:
        resp = requests.get(f"{BACKEND_URL}/tasks")
        resp.raise_for_status()
        tasks = resp.json()
    except Exception as e:
        st.error(f"Couldn’t load tasks: {e}")
        tasks = []

    for t in tasks:
        completed = st.checkbox(
            t["title"],
            value=t["completed"],
            key=f"task_{t['id']}"
        )

        # ←— INSERT THESE LINES —→
        if t.get("description"):
            st.markdown(f"> **Description:** {t['description']}")
        if t.get("due_date"):
            st.markdown(f"> **Due:** {t['due_date']}")
        st.markdown(
            f"> **Created:** {t['created_at']}  \n"
            f"> **Updated:** {t['updated_at']}"
        )
        if completed != t["completed"]:
            # Instruct AI to update completion
            ai_msg = f"update_task(id={t['id']}, completed={str(completed).lower()})"
            try:
                r = requests.post(f"{BACKEND_URL}/chat", json={"message": ai_msg})
                r.raise_for_status()
                st.rerun()
            except Exception as e:
                st.error(f"Error updating task: {e}")

        # Delete button
        if st.button("Delete", key=f"del_{t['id']}"):
            ai_msg = f"delete_task(id={t['id']})"
            try:
                r = requests.post(f"{BACKEND_URL}/chat", json={"message": ai_msg})
                r.raise_for_status()
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting task: {e}")

    st.markdown("---")
    st.subheader("Add a new task")
    with st.form("new_task_form", clear_on_submit=True):
        new_title = st.text_input("Title")
        new_desc = st.text_area("Description")
        new_due = st.text_input("Due (e.g. 'tomorrow at 9am')")
        submitted = st.form_submit_button("Add via AI")
        if submitted:
            ai_msg = (
                f"create_task(title=\"{new_title}\", "
                f"description=\"{new_desc}\", due_date=\"{new_due}\")"
            )
            try:
                r = requests.post(f"{BACKEND_URL}/chat", json={"message": ai_msg})
                r.raise_for_status()
                st.rerun()
            except Exception as e:
                st.error(f"Error creating task: {e}")

# --- Chat Column ---
with col_chat:
    st.header("💬 Chat with AI")

    # Initialize chat history
    if "history" not in st.session_state:
        st.session_state.history = []

    # Display history
    for entry in st.session_state.history:
        if entry["role"] == "user":
            st.markdown(f"**You:** {entry['text']}")
        else:
            st.markdown(f"**AI:** {entry['text']}")

    # Use a form to clear input on submit
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Your message...", key="user_input")
        sent = st.form_submit_button("Send")

        if sent and user_input:
            # Append user
            st.session_state.history.append({"role": "user", "text": user_input})

            # Call chat endpoint
            try:
                r = requests.post(f"{BACKEND_URL}/chat", json={"message": user_input})
                r.raise_for_status()
                data = r.json().get("data", {})
                ai_response = str(data)
            except Exception as e:
                ai_response = f"Error: {e}"

            # Append AI
            st.session_state.history.append({"role": "assistant", "text": ai_response})

            # Rerun to show updated history
            st.rerun()
