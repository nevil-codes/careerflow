# CareerFlow

Local job-application copilot. Runs entirely on your machine.

**Phase 0 (Foundations):** data model, profile import from `candidate_context.md`, read-only profile API, and a Profile page. No LLM calls, API keys, audits, or Notion/Excel sync yet.

| Layer    | Stack                                             |
|----------|---------------------------------------------------|
| Backend  | Python 3.12, FastAPI, SQLModel, SQLite, Alembic   |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS          |
| Tests    | pytest                                            |

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app
│   │   ├── models.py          SQLModel tables + shared Pydantic schemas
│   │   ├── api/profile.py     GET /profile, GET /profile/items
│   │   └── seed/              candidate_context.md parser + importer (python -m app.seed)
│   ├── alembic/               migrations
│   ├── data/                  SQLite DB (git-ignored)
│   └── tests/
├── frontend/                  Vite + React Profile page
├── candidate_context.example.md
└── docker-compose.yml
```

## Setup

Prerequisites: [uv](https://docs.astral.sh/uv/) (installs Python 3.12 for you) and Node.js 20.19+.

### 1. Your profile

```bash
cp candidate_context.example.md candidate_context.md
# edit candidate_context.md
```

`candidate_context.md` is git-ignored. Format rules are in the comment at the top of the example file. In short:

- `## Profile` needs `name` and `german_level`.
- Each item under `## Education`, `## Experience`, `## Projects`, `## Courses` is a `### Title` and needs a `- status:` of `completed`, `in-progress`, `planned` or `paused`.
- `## Skills` is one `- skill` bullet per skill.
- Any other `##` section is ignored.

### 2. Backend

```bash
cd backend
uv sync                          # create .venv with deps
uv run alembic upgrade head      # create backend/data/careerflow.db
uv run python -m app.seed        # import ../candidate_context.md (or pass a path)
uv run uvicorn app.main:app --reload
```

API at http://localhost:8000, interactive docs at http://localhost:8000/docs.

Re-run `python -m app.seed` whenever you edit `candidate_context.md`. It is idempotent: items are matched by type + title, so IDs stay stable, and items you delete from the file are removed.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api/*` to the backend (override with `API_PROXY_TARGET`).

### Docker (alternative)

```bash
cp candidate_context.example.md candidate_context.md   # if you haven't yet
docker compose up --build
docker compose exec backend python -m app.seed
```

Frontend on :5173, backend on :8000. The SQLite DB is shared with the host at `backend/data/`. An Ollama service is stubbed out (commented) in `docker-compose.yml` for later phases.

## Tests

```bash
cd backend && uv run pytest
cd frontend && npm run typecheck
```

The backend tests cover the parser, the seed (including idempotency and integrity guards), both endpoints, and a check that Alembic migrations match the models.

## Data integrity rules

`candidate_context.md` is the source of truth for the profile.

- **Status is never inferred.** Only case/spacing is normalised (`In Progress` becomes `in-progress`). A missing or unknown status (`done`, `wip`, `ongoing`, …) fails the seed with a line number and writes nothing.
- **In-progress items cannot become completed** except by changing the file and re-seeding. Any other code path that tries raises `LockedFieldError` on flush.
- **German level is locked.** It is stored verbatim from the file. Changing it outside the seed raises `LockedFieldError`.
- After every seed, stored statuses and German level are re-read and compared against the file, and any mismatch fails the seed.

## Configuration

| Variable                   | Default                                  |
|----------------------------|------------------------------------------|
| `CAREERFLOW_DATABASE_URL`  | `sqlite:///backend/data/careerflow.db`   |
| `CAREERFLOW_CONTEXT_FILE`  | `./candidate_context.md` (repo root)     |
| `API_PROXY_TARGET` (Vite)  | `http://localhost:8000`                  |

## API

| Method | Path                          | Returns                                  |
|--------|-------------------------------|------------------------------------------|
| GET    | `/profile`                    | Profile (404 until seeded)               |
| GET    | `/profile/items?type=project` | Items, optionally filtered by `type`: `education`, `job`, `project`, `course`, `skill` |
