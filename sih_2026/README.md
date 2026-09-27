# jansethu

**You report the problem. AI finds the people who can solve it.**

jansethu is an open-ended civic collaboration platform. The frontend lives in `frontend/`, the FastAPI service in `backend/`, and the full architecture contract is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Run locally

1. Copy `.env.example` to `.env` and set `AI_API_KEY` when an external model is available.
2. Frontend: `cd frontend`, `npm install`, `npm run dev`.
3. Backend: `cd backend`, `python -m venv .venv`, activate it, `pip install -r requirements.txt`, then `python -m uvicorn app.main:app --reload --port 8000`.

The first vertical slice includes a responsive dashboard, report modal, AI analysis service boundary, dynamic needs, support counts, recommendations, and impact data. PostgreSQL/pgvector persistence, authentication, and project workflows are staged in the documented phases.