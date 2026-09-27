# jansethu API

Run from this directory with `python -m uvicorn app.main:app --reload --port 8000` after installing `requirements.txt`. The API uses an in-memory development store in this first vertical slice. Set `AI_API_KEY` to route analysis through the external provider; without it, the local adapter keeps demos runnable while preserving the `AIService` boundary.