from fastapi import FastAPI

from app.api import applications, postings, profile, tasks

app = FastAPI(title="CareerFlow", version="0.2.0")
app.include_router(profile.router)
app.include_router(postings.router)
app.include_router(applications.router)
app.include_router(tasks.router)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}
