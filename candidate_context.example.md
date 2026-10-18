# Candidate Context

<!--
Copy to candidate_context.md (git-ignored) and fill in your details.
Seed with:  cd backend && uv run python -m app.seed

Rules:
- `## Profile` needs `name` and `german_level`. german_level is stored verbatim and locked.
- Every item under Education / Experience / Projects / Courses needs a `status`:
  completed | in-progress | planned | paused   (case and spaces don't matter: "In Progress" is fine)
  Unknown or missing status = seed fails. Nothing is ever inferred.
- `stack` is comma-separated, `metrics` is semicolon-separated, or put either as nested bullets.
- Any other line under an item becomes its description.
- Any other `##` section is ignored by the seed (free-form context for later phases).
-->

## Profile
- name: Alex Example
- headline: Backend & ML Engineer
- email: alex@example.com
- location: Berlin, Germany
- german_level: B1 (Goethe certificate, B2 in progress)

## Education
### M.Sc. Data Science
- institution: Example University
- period: 2024 – 2026
- status: in-progress

### B.Tech. Computer Engineering
- institution: Example Institute of Technology
- period: 2019 – 2023
- status: completed

## Experience
### Software Engineer
- company: Acme GmbH
- period: 2023 – present
- status: in-progress
- stack: Python, FastAPI, PostgreSQL
- metrics:
  - Cut p95 API latency by 40%
  - Migrated 3 services to async
Owned the internal analytics API.

## Projects
### CareerFlow
- status: in-progress
- stack: FastAPI, SQLModel, React, TypeScript
- link: https://github.com/example/careerflow
Local job-application copilot.

### Sentiment Classifier
- status: completed
- stack: PyTorch, Hugging Face
- metrics: F1 0.91 on held-out set; 120 GitHub stars

## Courses
### Deep Learning Specialization
- institution: Coursera
- status: completed

## Skills
- Python
- TypeScript
- SQL
- Docker

## Notes
Free-form context here is ignored by the seed.
