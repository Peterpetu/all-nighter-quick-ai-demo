# AI-Powered Todo App

A modular Todo/Task-List application with LLM-powered features.

🚀 Phase 1: Infrastructure & Health Check

Completed:
- Monorepo scaffold: backend/, frontend/, db/
- Docker Compose + Makefile
- Python pinned (3.11.2), Poetry backend
- VS Code devcontainer with dev dependencies
- Minimal FastAPI app with /health endpoint

🔨 Getting Started

Prerequisites:
- Docker & Docker Compose
- (Optional) VS Code + Dev Containers extension

Build & Run:
make build
make up

Health Check:
curl http://localhost:8000/health
# returns {"status":"ok"}

📦 Repo Structure
/
    backend/      FastAPI + PydanticAI + app code
    frontend/     React app (placeholder)
    db/           SQLite volume container
    docker-compose.yml
    Makefile
    .devcontainer/
    .python-version

🛠 Roadmap
- Phase 2: Task model + CRUD & SQLite persistence
- Phase 3: Chat UI + NL→Task agent + other support agents
- Phase 4: Knowledge-graph logging
- Phase 5: Tests, polish, docs