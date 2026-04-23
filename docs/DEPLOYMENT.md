# Deployment Guide

## Local Development (Recommended for First Run)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker Desktop (for Docker tool integration)
- PostgreSQL 15+ (or use Docker Compose)

### Step 1 — Clone and configure
```bash
git clone https://github.com/your-username/devops-assistant.git
cd devops-assistant

# Set up backend env
cp backend/.env.example backend/.env
# Edit backend/.env: add OPENAI_API_KEY, GITHUB_TOKEN, etc.

# Set up frontend env
cp frontend/.env.example frontend/.env
```

### Step 2 — Start with Docker Compose
```bash
docker compose up --build
```

Services started:
- PostgreSQL on port 5432
- Redis on port 6379
- FastAPI backend on http://localhost:8000
- React frontend on http://localhost:5173

### Step 3 — Create your first admin user
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","username":"admin","password":"Admin@1234"}'
```

Then manually update the role to `admin` in the database:
```sql
UPDATE users SET role = 'admin' WHERE username = 'admin';
```

---

## AWS EC2 Deployment

### Step 1 — Provision EC2 instance
- Instance type: `t3.medium` (minimum), `t3.large` recommended
- AMI: Ubuntu 22.04 LTS
- Security Group: Open ports 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (API)

### Step 2 — Install Docker on EC2
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
newgrp docker
```

### Step 3 — Clone and deploy
```bash
git clone https://github.com/your-username/devops-assistant.git
cd devops-assistant
cp backend/.env.example backend/.env
nano backend/.env  # Add production credentials

docker compose up -d --build
```

### Step 4 — Configure GitHub webhook (for self-healing)
In your app repository:
- Settings → Webhooks → Add webhook
- Payload URL: `http://<EC2_IP>:8000/api/v1/webhooks/github`
- Content type: `application/json`
- Events: Workflow runs, Pushes

---

## GitHub Actions CI/CD

Add these secrets to your repository (Settings → Secrets → Actions):

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for tests |
| `AWS_ACCESS_KEY_ID` | AWS credentials for ECR/EC2 |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `AWS_DEFAULT_REGION` | e.g. `us-east-1` |
| `EC2_HOST` | EC2 public IP or hostname |
| `EC2_USER` | SSH user (e.g. `ubuntu`) |
| `EC2_SSH_KEY` | Private SSH key content |

The CI pipeline (`.github/workflows/ci.yml`) runs on every push:
1. Backend lint + pytest
2. Frontend lint + build
3. Docker Compose build verification

The CD pipeline (`.github/workflows/deploy.yml`) runs on merge to `main`:
1. Builds and pushes Docker images to ECR
2. SSH deploys to EC2

---

## Environment Variables Reference

See `backend/.env.example` for full reference with descriptions.

**Minimum required for local dev:**
```env
SECRET_KEY=any-random-string-32-chars
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://devops_user:devops_pass@localhost:5432/devops_assistant
```
