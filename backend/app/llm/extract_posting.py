"""Extract a posting's basic fields from pasted job-description text."""

import re

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.llm.base import ChatMessage, Provider
from app.llm.structured import generate_structured

# Title and company sit near the top; very long pastes are trimmed for the prompt only.
MAX_PROMPT_CHARS = 20_000


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


class ExtractedPosting(BaseModel):
    title: str = Field(description="The job title exactly as written in the posting.")
    company: str = Field(description="The hiring company's name exactly as written in the posting.")
    location: str | None = Field(default=None, description="City/country or 'Remote', if stated.")
    language: str | None = Field(
        default=None, description="Language the posting is written in, in English, e.g. 'English' or 'German'."
    )
    url: str | None = Field(default=None, description="Application or posting URL, only if it appears in the text.")

    @field_validator("title", "company", "location", "language", "url", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("title", "company", "url")
    @classmethod
    def _must_appear_in_source(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Guards against made-up values: they must be copied from the pasted text."""
        source = (info.context or {}).get("source")
        if value is None or source is None:
            return value
        if _normalize(value) not in _normalize(source):
            raise ValueError(f"{value!r} does not appear in the posting text; copy it exactly or use null")
        return value

    @field_validator("language")
    @classmethod
    def _capitalize(cls, value: str | None) -> str | None:
        return value.capitalize() if value else value


SYSTEM_PROMPT = """\
You extract structured data from a job posting. Reply only with JSON matching the schema.
Copy the job title and company name exactly as they appear in the text. Do not translate,
shorten or invent anything. Use null for anything the posting does not state."""


def extract_posting(provider: Provider, text: str) -> ExtractedPosting:
    messages: list[ChatMessage] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Job posting:\n\n{text[:MAX_PROMPT_CHARS]}"},
    ]
    posting = generate_structured(provider, ExtractedPosting, messages, context={"source": text}).value
    # Post-processing after validation, so the appears-in-text check saw the raw values.
    if posting.url and not posting.url.startswith(("http://", "https://")):
        posting.url = f"https://{posting.url}"
    if posting.language is None:
        posting.language = detect_language(text)
    return posting


_STOPWORDS = {
    "German": {"und", "der", "die", "das", "mit", "für", "wir", "du", "dein", "deine", "ist", "bei", "zu", "von", "auf", "sie", "ihre", "uns"},
    "English": {"and", "the", "with", "for", "we", "you", "your", "is", "to", "of", "our", "are", "will", "in"},
}


def detect_language(text: str) -> str | None:
    """Deterministic fallback: whichever stopword set dominates, if clearly."""
    words = re.findall(r"[a-zäöüß]+", text.casefold())
    counts = {lang: sum(w in stop for w in words) for lang, stop in _STOPWORDS.items()}
    best, runner_up = sorted(counts.values(), reverse=True)
    if best < 5 or best < 2 * runner_up:
        return None
    return max(counts, key=counts.get)
