from fastapi import FastAPI

from app.api import profile

app = FastAPI(title="CareerFlow", version="0.1.0")
app.include_router(profile.router)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}
