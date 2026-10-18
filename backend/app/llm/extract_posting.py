"""Extract a posting's basic fields from pasted job-description text."""

import re

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.llm.base import ChatMessage, Provider
from app.llm.structured import generate_structured

# Title and company sit near the top; very long pastes are trimmed for the prompt only.
MAX_PROMPT_CHARS = 20_000


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


# German-style gender tags: (m/w/d), (w/m/d), (m/f/d), (all genders), (gn), ...
_GENDER_TAG = re.compile(r"\s*\((?:[mwfdx]\s*/\s*){1,3}[mwfdx]\*?\)|\s*\((?:all genders|gn\*?|m/w/div\.?)\)", re.I)

# Models sometimes emit a placeholder string instead of JSON null, e.g. ":null" or "N/A".
_NULLISH = re.compile(r"^[\s:\"'`.-]*(null|none|n/?a|unknown|not stated|not specified)?[\s:\"'`.-]*$", re.I)


class ExtractedPosting(BaseModel):
    title_original: str = Field(description="The job title exactly as written in the posting, in its language.")
    title_en: str = Field(
        description="The job title in English. Translate it if the posting is not in English, and drop "
        "gender tags such as (m/w/d). If the posting is in English, repeat the original title."
    )
    company: str = Field(description="The hiring company's name exactly as written. Never translate it.")
    location_en: str | None = Field(
        default=None,
        description="City and country in English (e.g. 'Cologne, Germany', not 'Köln'), or 'Remote', if stated.",
    )
    language: str | None = Field(
        default=None, description="Language the posting is written in, named in English, e.g. 'German'."
    )
    url: str | None = Field(default=None, description="Application or posting URL, only if it appears in the text.")

    @field_validator("title_original", "title_en", "company", "location_en", "language", "url", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and _NULLISH.match(value):
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("title_original", "company", "url")
    @classmethod
    def _must_appear_in_source(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Guards against made-up values: they must be copied from the pasted text."""
        source = (info.context or {}).get("source")
        if value is None or source is None:
            return value
        if _normalize(value) not in _normalize(source):
            fix = "use null" if info.field_name == "url" else "copy it exactly as written there"
            raise ValueError(f"{value!r} does not appear in the posting text; {fix}")
        return value

    @field_validator("language")
    @classmethod
    def _capitalize(cls, value: str | None) -> str | None:
        return value.capitalize() if value else value

    def to_posting_fields(self) -> dict:
        """English values go in the main fields; the original title is kept only if it differs."""
        title_en = _GENDER_TAG.sub("", self.title_en).strip() or self.title_en
        # An English posting whose title differs only by a gender tag needs no "original".
        same = _normalize(_GENDER_TAG.sub("", self.title_original)) == _normalize(title_en)
        return {
            "title": title_en,
            "title_original": None if same else self.title_original,
            "company": self.company,
            "location": self.location_en,
            "language": self.language,
            "url": self.url,
        }


SYSTEM_PROMPT = """\
You extract structured data from a job posting. Reply only with JSON matching the schema.
All fields are in English, translated if needed, except title_original and company, which
are copied exactly as they appear in the text. Do not invent anything. Use null for
anything the posting does not state."""


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
