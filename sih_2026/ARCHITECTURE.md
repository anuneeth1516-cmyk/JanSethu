# jansethu Architecture

## System architecture

```text
Next.js web app -> FastAPI REST API -> PostgreSQL + pgvector
                         |
                         -> AIService -> provider adapter -> external AI API
                         |
                         -> object storage for evidence
```

The frontend never receives provider credentials. Reports are accepted by the API, persisted, analyzed by `AIService`, embedded for semantic search, and matched against participant profiles by capability relevance rather than fixed categories.

## Technology stack

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, Lucide icons, Leaflet/OpenStreetMap-ready map surface
- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Pydantic settings, JWT authentication
- Data: PostgreSQL with pgvector in production; SQLite-compatible development fallback for fast demos
- AI: OpenAI-compatible adapter behind `AIService`; mock adapter only when `AI_API_KEY` is absent for local development
- Deployment: Vercel for the frontend and Render/Fly.io for FastAPI plus managed PostgreSQL

## Folder structure

```text
frontend/              Next.js application
backend/app/api/       FastAPI routes
backend/app/core/      settings and security
backend/app/models/    database models
backend/app/schemas/   API contracts
backend/app/services/  AI, matching, and report workflows
docs/                  architecture and API contracts
```

## Database schema

Core entities are `users`, `profiles`, `skills`, `organizations`, `problems`, `reports`, `locations`, `ai_analyses`, `embeddings`, `matches`, `teams`, `projects`, `tasks`, `solutions`, `resources`, `updates`, `impact_metrics`, and `feedback`. Problems can have many reports and support votes; profiles expose free-form capabilities and an embedding; matches store score and explanation snapshots for auditability.

## API endpoints

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- `GET /api/v1/problems`, `POST /api/v1/problems`, `GET /api/v1/problems/{id}`
- `POST /api/v1/problems/{id}/support`, `POST /api/v1/problems/{id}/collaboration-requests`
- `GET /api/v1/recommendations/problems`, `GET /api/v1/problems/{id}/matches`
- `POST /api/v1/teams`, `GET /api/v1/projects/{id}`, `PATCH /api/v1/projects/{id}`
- `GET /api/v1/impact`, `POST /api/v1/problems/{id}/feedback`

## AI architecture

Application services depend on the `AIService` protocol. `OpenAIService` sends text and optional image evidence to the configured external provider and returns structured analysis: generated domain/tags, severity, urgency, affected people, needs, stakeholders, solution areas, and a concise rationale. Provider-specific SDK and response parsing stay inside the adapter.

## Semantic matching

The report analysis is serialized into a search document and embedded. Candidate profile documents are embedded from skills, expertise, projects, interests, and resources. pgvector cosine similarity provides retrieval; a transparent reranker combines semantic relevance, location proximity, availability, and profile completeness. No problem-to-organization mapping is hardcoded.

## Authentication and security

JWT access tokens are issued by FastAPI and stored in an HttpOnly cookie in production. Passwords use Argon2. CORS is restricted by `FRONTEND_URL`. `AI_API_KEY`, `DATABASE_URL`, and `JWT_SECRET` are environment variables only. `.env` is ignored and `.env.example` contains placeholders.

## UI page structure

Public pages cover landing, how it works, login, and registration. Authenticated pages share a compact navigation shell: citizen dashboard/report/map/my reports, solver recommendations/matches/teams/projects, organization profile/requests/projects, and authority verification/approvals/impact.

## Development phases

1. Foundation, authentication, responsive dashboard shell, and seed demo data.
2. Citizen reporting with evidence and location.
3. PostgreSQL persistence and report lifecycle.
4. External AI analysis through `AIService`.
5. Semantic duplicate grouping.
6. Dynamic collaborator matching.
7. Collaboration requests and teams.
8. Project milestones, tasks, updates, and evidence.
9. Impact metrics and feedback.
10. Demo polish, accessibility, and deployment configuration.

Each phase keeps the frontend and backend independently startable and is validated before the next phase begins.