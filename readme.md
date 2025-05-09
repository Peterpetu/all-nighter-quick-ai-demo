# 📝 AI-Powered Multiagent Todo & Notes App

This is a demo project showcasing an AI-powered Todo & Notes application, featuring advanced Natural Language → Task creation, management, and chat-based interaction. The backend utilizes FastAPI with structured multiagent orchestration, and the frontend is built with Streamlit.

---

## 🚀 Quick Start (One-command launch)

**Prerequisites**:
- Docker Compose installed
- An OpenAI API Key (stored in `.env`)

**Step 1: Clone the repository and configure your API key**
```bash
git clone <repository-url>
cd ai_demo
cp .env-example .env
# Edit .env to include your OpenAI API key
```
**Step 2: Start the application**

```bash
make up
```
Your app will launch:

Frontend UI: http://localhost:3000

Backend API: http://localhost:8000

## 📚 Features Overview
✅ Natural Language → Task Conversion

✅ Intelligent Chatbot Interface

✅ Persistent Task Management (CRUD with SQLite)

✅ Advanced Multiagent Coordination:

UserServiceAgent (Chat & task orchestration)

TaskCreationAgent (Task CRUD handling via LLM)

Support Agents (Intent/Emotion detection, Contextual Questions, Task Status summarization)

## 🧑‍💻 Architecture & Design Choices
The app employs a robust multiagent architecture:

High-Level Structure
```scss
Frontend (Streamlit)
    │
Backend API (FastAPI)
    ├── UserServiceAgent (GPT-4o)
    │     ├── TaskCreationAgent (nested GPT-4o agent)
    │     ├── IntentEmotionAgent (GPT-4o)
    │     ├── QuestionForUserAgent (GPT-4o)
    │     └── TaskStatusAgent (GPT-4o)
    │
SQLite DB Persistence
```
## 🧠 LLM Orchestration Strategy
Single-entry Orchestrator Agent (UserServiceAgent) routes user requests intelligently.

Orchestrator uses specialized nested agents/tools (TaskCreationAgent, intent, question, status agents) depending on context.

Agents maintain context-aware memory between interactions, enhancing task understanding and conversational coherence.

## ✨ Prompt Engineering
System Prompts: Clear, concise, and specific to agent roles, kept separate in markdown files.

Prompt Injection: Contextual information (tasks, intent, status summaries) dynamically injected into agent prompts for context-aware interactions.

## ⚙️ Error Handling & Robustness
Graceful API Fallbacks: Any LLM/API failure gracefully reported to users with clear error messaging.

Tool Invocation Checks: Parsing of LLM responses to ensure valid tool calls. If parsing fails, the agent gracefully falls back to standard chat replies.

Logging: Comprehensive logs to diagnose issues rapidly (logging module utilized throughout).

## 🗂 Directory Structure Overview
```bash
ai_demo/
├── .env-example                 # Template for your API keys and config
├── docker-compose.yml           # Docker Compose services configuration
├── Makefile                     # Simple project commands
│
├── backend/                     # FastAPI backend service
│   ├── app/
│   │   ├── agents/
│   │   │   ├── base.py
│   │   │   ├── user_service_agent.py
│   │   │   ├── task_creation_agent.py
│   │   │   └── system_prompts/
│   │   ├── models.py
│   │   ├── db.py
│   │   └── routers/
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/                    # Streamlit frontend service
│   ├── streamlit_app.py
│   ├── Dockerfile
│   └── requirements.txt
│
└── db/                          # SQLite DB container (volume holder)
```
## 🛠 Development Workflow
Common Commands (via Makefile)
```bash
make build        # Build all containers
make up           # Run all containers
make down         # Stop all containers
make logs         # Tail logs from all services
```
## 🧪 Testing
Currently, automated tests are scheduled for Phase 5 (optional, based on project time constraints). If added, tests will be implemented using:

pytest (for unit and integration tests)

FastAPI's built-in testing utilities for API endpoints.

Running Tests (future phase)
```bash
cd backend
poetry run pytest tests/
```
## 📦 Dependencies & Technologies
| Component | Tech Stack                                  |
|-----------|---------------------------------------------|
| Frontend  | Streamlit                                   |
| Backend   | FastAPI, SQLModel, SQLite, Poetry           |
| Agents    | GPT-4o, OpenAI API, pydantic-ai library     |
| Deployment| Docker Compose                              |

## 🗺️ Roadmap & Next Steps
✅ Phase 1: Project Setup & Containerization

✅ Phase 2: Task Model + CRUD & SQLite Persistence

✅ Phase 3: Chat UI + NL→Task Agent (current)

✅ Phase 4: Multiagent Orchestration (current)

🚧 Phase 5: Tests, Polish, Docs (future, if time permits)

## 📌 Troubleshooting & FAQs
**Q: The agent says "manage_task(...)" but doesn't create tasks.**
A: Ensure .env contains a valid OpenAI API key and containers have been restarted (make down && make up). Check logs for detailed errors.

**Q: Streamlit or API doesn't start correctly.**
A: Run `make logs` to diagnose issues quickly.