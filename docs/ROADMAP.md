# CareerFlow Roadmap

One phase per session. Each phase ends with something usable.

## Decisions (2026-10-18)

| Topic | Decision |
|-------|----------|
| Posting intake | Paste the job description text. No URL scraping or job-board APIs for now. |
| First LLM provider | Ollama (local, no key). Cloud providers later. |
| Sync | Excel first, one-way export. Notion later. |
| Order | Job tracker before audits (audits need postings). |

## Rules for every phase

- `candidate_context.md` is the only source of truth for the profile. Nothing else writes to it or to the profile tables.
- Every feature that writes data gets an integrity test.
- Ask before adding any dependency.

## Phases

### Phase 0: Foundations (done)
Monorepo, models and migrations, profile seed with status and German-level guards, `GET /profile`, `GET /profile/items`, Profile page.

### Phase 0.5: Close out
- [ ] Add the real `candidate_context.md` and seed it.
- [ ] Run `docker compose up` on a machine with Docker.
- [x] Commit Phase 0.
- [x] Push to github.com/nevil-codes/careerflow, open PRs #1 (Phase 0) and #2 (Phase 1).

### Phase 1: Job tracker (no LLM) (done)
- Postings: create from pasted text, list, view, edit, delete.
- Applications: status pipeline draft → applied → interviewing → offer / rejected / withdrawn, with timestamps.
- Tasks attached to applications (e.g. follow-ups with due dates).
- Frontend: postings list and detail, application board, tasks.

**Done when:** the real job hunt can be tracked end to end by hand.

### Phase 2: LLM provider layer (done)
- Provider interface; Ollama first.
- `ProviderConfig` stores model and URL only. Keys in env or OS keychain, never in the DB.
- Structured JSON output validated against Pydantic schemas, with retries.
- The LLM can read the profile, never write it.

**Done when:** a "test provider" action returns a valid structured response.

### Phase 3: Audits
- Extract requirements from a posting (must-haves, nice-to-haves, German level, location/visa).
- Match against profile items: score, gaps, and which item backs which claim.
- German check is deterministic against the locked level.

**Done when:** each posting shows a fit report with evidence.

### Phase 4: Documents
- Tailored CV and cover letter generated only from profile items.
- Claims checker blocks: in-progress items described as finished, German level differing from the locked value, claims with no backing item.
- Edit before saving. PDF/DOCX export (library needs approval).

### Phase 5: Sync
- Excel export (one-way). Then Notion push.

### Phase 6: Hardening
- DB backup/restore, search, packaging.
