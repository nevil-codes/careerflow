from fastapi import FastAPI

from app.api import applications, postings, profile, providers, tasks

app = FastAPI(title="CareerFlow", version="0.3.0")
app.include_router(profile.router)
app.include_router(postings.router)
app.include_router(applications.router)
app.include_router(tasks.router)
app.include_router(providers.router)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}
