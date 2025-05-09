import os
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()

# URL of the backend service, injected via .env
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(page_title="AI Todo App", layout="wide")
st.title("🛠 AI-Powered Todo List")

# Two-column layout: tasks on the left, chat on the right
col_tasks, col_chat = st.columns((1, 1))

# --- Tasks Column ---
with col_tasks:
    st.header("Your Tasks")

    # Fetch tasks from the backend
    try:
        resp = requests.get(f"{BACKEND_URL}/tasks")
        resp.raise_for_status()
        tasks = resp.json()
    except Exception as e:
        st.error(f"Couldn’t load tasks: {e}")
        tasks = []

    # Display each task
    for t in tasks:
        completed = st.checkbox(
            t["title"],
            value=t["completed"],
            key=f"task_{t['id']}"
        )

        # Show description, due-date, and timestamps
        if t.get("description"):
            st.markdown(f"> **Description:** {t['description']}")
        if t.get("due_date"):
            st.markdown(f"> **Due:** {t['due_date']}")
        st.markdown(
            f"> **Created:** {t['created_at']}  \n"
            f"> **Updated:** {t['updated_at']}"
        )

        # Completion toggle
        if completed != t["completed"]:
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

    # Form to add a new task
    st.markdown("---")
    st.subheader("Add a new task")
    with st.form("new_task_form", clear_on_submit=True):
        new_title = st.text_input("Title")
        new_desc  = st.text_area("Description")
        new_due   = st.text_input("Due (e.g. 'tomorrow at 9am')")
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

    if "history" not in st.session_state:
        st.session_state.history = []

    # Display chat history
    for entry in st.session_state.history:
        role = "You" if entry["role"] == "user" else "AI"
        st.markdown(f"**{role}:** {entry['text']}")

    # Chat form
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Your message…", key="user_input")
        sent = st.form_submit_button("Send")

        if sent and user_input:
            # Add user message to history
            st.session_state.history.append({"role": "user", "text": user_input})

            # Call the /chat endpoint
            try:
                r = requests.post(f"{BACKEND_URL}/chat", json={"message": user_input})
                r.raise_for_status()
                res = r.json()

                # 1) Free-form chat reply?
                if res.get("chat_response"):
                    ai_response = res["chat_response"]

                # 2) Task created/updated?
                elif res.get("task"):
                    t = res["task"]
                    ai_response = (
                        f"✅ Task {t['id']} – {t['title']} "
                        f"(due {t['due_date'] or 'none'})"
                    )

                # 3) Task deleted?
                elif res.get("delete"):
                    d = res["delete"]
                    if d.get("deleted"):
                        ai_response = f"🗑️ Deleted task ID {d['id']}"
                    else:
                        ai_response = f"❌ Failed to delete task ID {d['id']}"

                else:
                    # Fallback: show entire JSON
                    ai_response = str(res)

            except Exception as e:
                ai_response = f"Error: {e}"

            # Add AI response to history and rerun
            st.session_state.history.append({"role": "assistant", "text": ai_response})
            st.rerun()
