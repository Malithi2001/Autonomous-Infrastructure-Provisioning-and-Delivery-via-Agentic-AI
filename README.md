# 🤖 Agentic AI-Powered Smart DevOps Assistant

> An autonomous, LLM-driven DevOps assistant capable of managing CI/CD pipelines, infrastructure provisioning, incident response, and system monitoring through natural language interaction.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.2+-purple.svg)](https://langchain.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Project Overview

This project is a **Final Year Research Project** for the BSc (Hons.) in Information Technology at **Horizon Campus, Faculty of Information Technology**.

The Smart DevOps Assistant bridges the gap between human intent and machine execution by integrating Large Language Models (LLMs) with agentic frameworks (LangChain) to autonomously manage complex infrastructure tasks — acting as a *virtual DevOps engineer*.

### 👥 Team Members

| Name | Registration No |
|------|----------------|
| T.V.M. Weerasooriya | ITBIN-2211-0316 |

**Supervisor:** Isuru Samarappulige | **Co-supervisor:** Anuradha Ishani Yapa

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React/Vite Frontend                       │
│         Chat UI │ HITL Approval │ Execution Logs            │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST / WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend (Python)                    │
│      Auth │ RBAC │ Webhook Handler │ Audit Logger           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              LangChain Agent Core (AI Brain)                 │
│   LLM │ Memory │ Tool Binding │ Planning │ Reasoning        │
└────────┬──────────────────────────────────┬─────────────────┘
         │                                  │
┌────────▼────────┐                ┌────────▼────────────────┐
│  DevOps Tools   │                │   Cloud Infrastructure  │
│ Docker │ GitHub │                │   AWS EC2 │ Kubernetes  │
│ Actions│ Shell  │                │   Terraform │ Prometheus │
└─────────────────┘                └─────────────────────────┘
```

---

## ✨ Key Features

- 🗣️ **Natural Language Infrastructure as Code** — describe what you want, the agent does it
- 🔁 **Self-Healing Workflows** — detects failures, parses logs, and auto-remediates
- 🔐 **Human-in-the-Loop (HITL)** — approval gates for high-risk operations
- 🛡️ **RBAC Security** — role-based access control for all agent actions
- 📋 **Full Audit Logging** — timestamped, traceable action history
- 🔍 **Transparent Decision Mapping** — explainable reasoning for every action
- 🐳 **Docker-Ready** — fully containerized deployment

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI (Python 3.11+) |
| AI / Agent Core | LangChain + OpenAI / Claude |
| Task Queue | Celery + Redis |
| Database | PostgreSQL + SQLAlchemy |
| Auth | JWT + RBAC |
| Containerization | Docker + Docker Compose |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | React 18 + Vite |
| Styling | Tailwind CSS |
| State Management | Zustand |
| HTTP Client | Axios |
| Real-time | WebSocket (native) |
| UI Components | shadcn/ui |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- An OpenAI or Anthropic API key

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/devops-assistant.git
cd devops-assistant
```

### 2. Environment Setup

```bash
# Copy environment templates
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Edit with your credentials
nano backend/.env
```

### 3. Run with Docker Compose (Recommended)

```bash
docker-compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 4. Run Locally (Development)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## 📁 Project Structure

```
devops-assistant/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/routes/         # API endpoint routers
│   │   ├── agents/             # LangChain agent logic
│   │   ├── tools/              # DevOps tool integrations
│   │   ├── core/               # Config, security, database
│   │   ├── models/             # SQLAlchemy DB models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── services/           # Business logic services
│   ├── tests/                  # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                   # React/Vite frontend
│   ├── src/
│   │   ├── components/         # UI components
│   │   │   ├── chat/           # Chat interface
│   │   │   ├── approval/       # HITL approval UI
│   │   │   └── logs/           # Execution log viewer
│   │   ├── pages/              # Route pages
│   │   ├── hooks/              # Custom React hooks
│   │   ├── store/              # Zustand state stores
│   │   └── services/           # API service layer
│   ├── Dockerfile
│   └── package.json
│
├── docs/                       # Project documentation
├── .github/workflows/          # CI/CD GitHub Actions
├── docker-compose.yml
└── README.md
```

---

## 📖 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Agent Design](docs/AGENT_DESIGN.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Contributing Guide](CONTRIBUTING.md)

---

## 🔒 Security & Ethics

This system implements:
- **RBAC** — granular permission control per role
- **HITL Approval Gates** — human sign-off required for production actions
- **Audit Logs** — full traceability of all AI decisions
- **Sandboxed Testing** — all features validated in isolated environments before production
- **Data Encryption** — at-rest and in-transit for all sensitive data

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- Horizon Campus, Faculty of Information Technology
- Supervisor: Isuru Samarappulige
- Co-supervisor: Anuradha Ishani Yapa
- LangChain, FastAPI, and React open-source communities
