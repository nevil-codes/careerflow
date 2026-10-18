# CareerFlow

Local job-application copilot. Runs entirely on your machine.

**Current state (Phase 2):** profile import from `candidate_context.md`, a manual job tracker (postings, applications with full status history, follow-up tasks), and a local LLM provider layer (Ollama) with validated structured output. No AI features use it yet; audits come in Phase 3. No API keys, no Notion/Excel sync yet. See [docs/ROADMAP.md](docs/ROADMAP.md).

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
│   │   ├── api/               profile, postings, applications, tasks, providers routers
│   │   ├── llm/               provider interface, Ollama client, structured output, profile context
│   │   └── seed/              candidate_context.md parser + importer (python -m app.seed)
│   ├── alembic/               migrations
│   ├── data/                  SQLite DB (git-ignored)
│   └── tests/
├── frontend/                  Vite + React UI (postings, application board, tasks, profile)
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

Open http://localhost:5173. Pages: Postings, Applications (board), Tasks, Profile, Settings. Vite proxies `/api/*` to the backend (override with `API_PROXY_TARGET`).

### 4. Local LLM (optional until Phase 3)

```bash
# install from https://ollama.com, then:
ollama serve                 # if the desktop app isn't already running it
ollama pull qwen3:8b         # or any model; gpt-oss:20b also works
```

In the app, open **Settings**, add the provider (defaults to `http://localhost:11434`), pick a model, and click **Test provider**. It sends a small request that must come back as JSON matching a schema. Only one provider is active at a time.

### Docker (alternative)

```bash
cp candidate_context.example.md candidate_context.md   # if you haven't yet
docker compose up --build
docker compose exec backend python -m app.seed
```

Frontend on :5173, backend on :8000. The backend reaches Ollama on your host at `host.docker.internal:11434`. The SQLite DB is shared with the host at `backend/data/`. An Ollama service is stubbed out (commented) in `docker-compose.yml` for later phases.

## Tests

```bash
cd backend && uv run pytest
cd frontend && npm run typecheck
```

The backend tests cover the parser, the seed (including idempotency and integrity guards), every endpoint, application status history, and checks that Alembic migrations match the models and upgrade existing data.

After pulling new code, run `uv run alembic upgrade head` again to apply new migrations.

## Data integrity rules

`candidate_context.md` is the source of truth for the profile.

- **Status is never inferred.** Only case/spacing is normalised (`In Progress` becomes `in-progress`). A missing or unknown status (`done`, `wip`, `ongoing`, …) fails the seed with a line number and writes nothing.
- **In-progress items cannot become completed** except by changing the file and re-seeding. Any other code path that tries raises `LockedFieldError` on flush.
- **German level is locked.** It is stored verbatim from the file. Changing it outside the seed raises `LockedFieldError`.
- After every seed, stored statuses and German level are re-read and compared against the file, and any mismatch fails the seed.
- **The profile is read-only outside the seed.** Any insert, update or delete of profile rows from anywhere else (including future LLM features) raises `LockedFieldError`. LLM prompts get a plain-text snapshot of the profile with statuses and German level verbatim, plus rules not to restate them differently.
- **No API keys in the database.** `provider_config` stores only name, model and URL. Cloud providers (later) will read keys from the environment or OS keychain.
- **Application history is append-only and automatic.** Every status change, from any code path, is written to `application_event` by an ORM flush hook. Statuses can move freely (e.g. rejected back to interviewing), but nothing changes silently. `applied_at` is set the first time an application leaves `draft` and can be backdated.

## Configuration

| Variable                   | Default                                  |
|----------------------------|------------------------------------------|
| `CAREERFLOW_DATABASE_URL`  | `sqlite:///backend/data/careerflow.db`   |
| `CAREERFLOW_CONTEXT_FILE`  | `./candidate_context.md` (repo root)     |
| `CAREERFLOW_OLLAMA_URL`    | `http://localhost:11434`                 |
| `CAREERFLOW_LLM_TIMEOUT`   | `180` (seconds per LLM call)             |
| `API_PROXY_TARGET` (Vite)  | `http://localhost:8000`                  |

## API

Full interactive docs at http://localhost:8000/docs.

| Method | Path | Notes |
|--------|------|-------|
| GET | `/profile` | 404 until seeded |
| GET | `/profile/items?type=` | `type`: `education`, `job`, `project`, `course`, `skill` |
| GET, POST | `/postings` | `?q=` searches title and company |
| GET, PATCH, DELETE | `/postings/{id}` | DELETE also removes its application, history and tasks |
| GET, POST | `/applications` | One per posting (409 on a second). `?status=` filter |
| GET, PATCH, DELETE | `/applications/{id}` | GET includes `events` (history) and `tasks` |
| GET, POST | `/tasks` | `?application_id=`, `?status=`, `?open=true`; sorted by due date |
| PATCH, DELETE | `/tasks/{id}` | |
| GET, POST | `/providers` | LLM provider configs. Enabling one disables the others |
| GET | `/providers/defaults` | Default server URL per provider kind |
| PATCH, DELETE | `/providers/{id}` | |
| GET | `/providers/{id}/models` | Installed models (503 if the server is unreachable) |
| POST | `/providers/{id}/test` | Structured test request; always 200, check `ok` / `error` |
