# Contributing Guide

Thank you for contributing to the Smart DevOps Assistant!

## Development Setup

```bash
git clone https://github.com/your-username/devops-assistant.git
cd devops-assistant
```

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Branching Strategy

- `main` — production-ready, protected
- `develop` — integration branch
- `feature/<name>` — new features
- `fix/<name>` — bug fixes
- `docs/<name>` — documentation updates

## Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add AWS Lambda tool integration
fix: correct RBAC permission check for staging deployments
docs: update ARCHITECTURE.md with session pool diagram
test: add coverage for github_tool.py
refactor: extract approval logic into ApprovalService
```

## Pull Request Checklist

- [ ] Tests pass locally (`pytest tests/`)
- [ ] Frontend builds (`npm run build`)
- [ ] New tools have description strings and are registered in `tools_registry.py`
- [ ] Sensitive env vars are in `.env.example` with placeholder values
- [ ] Code follows existing patterns (async/await in backend, typed React in frontend)

## Code Style

**Backend:** PEP8, max line length 120, `flake8` enforced in CI
**Frontend:** ESLint + Prettier, TypeScript strict mode

## Testing

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend
cd frontend && npm run lint && npm run build
```
