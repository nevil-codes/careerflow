"""Database models and the Pydantic schemas shared with the API.

Each entity follows the SQLModel pattern: a ``*Base`` class holds the shared
fields, the ``table=True`` class adds DB-only columns, and ``*Read`` classes
are the API response schemas.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, Text, UniqueConstraint, event, inspect
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Session as SASession
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_type(enum_cls: type[StrEnum]) -> SAEnum:
    """Store enum *values* as VARCHAR with a CHECK constraint (portable, readable)."""
    return SAEnum(
        enum_cls,
        name=enum_cls.__name__.lower(),
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )


# --- Enums -----------------------------------------------------------------


class ItemType(StrEnum):
    EDUCATION = "education"
    JOB = "job"
    PROJECT = "project"
    COURSE = "course"
    SKILL = "skill"


class ItemStatus(StrEnum):
    COMPLETED = "completed"
    IN_PROGRESS = "in-progress"
    PLANNED = "planned"
    PAUSED = "paused"


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class DocumentKind(StrEnum):
    CV = "cv"
    COVER_LETTER = "cover-letter"
    OTHER = "other"


class TaskStatus(StrEnum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


# --- Profile ---------------------------------------------------------------


class ProfileBase(SQLModel):
    full_name: str
    headline: str | None = None
    email: str | None = None
    location: str | None = None
    # Locked: only the seed script (source of truth: candidate_context.md) may set it.
    german_level: str


class Profile(ProfileBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ProfileRead(ProfileBase):
    id: int


class ProfileItemBase(SQLModel):
    type: ItemType = Field(sa_type=enum_type(ItemType), index=True)
    title: str
    organization: str | None = None
    period: str | None = None
    # Null only for skills. Never inferred: it is copied verbatim from the source file.
    status: ItemStatus | None = Field(default=None, sa_type=enum_type(ItemStatus))
    description: str | None = Field(default=None, sa_type=Text)
    stack: list[str] = Field(default_factory=list, sa_type=JSON)
    metrics: list[str] = Field(default_factory=list, sa_type=JSON)
    link: str | None = None
    position: int = 0


class ProfileItem(ProfileItemBase, table=True):
    __tablename__ = "profile_item"
    __table_args__ = (UniqueConstraint("profile_id", "type", "title"),)

    id: int | None = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", index=True, ondelete="CASCADE")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ProfileItemRead(ProfileItemBase):
    id: int


# --- Job search (schema only in Phase 0) -----------------------------------


class Posting(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    company: str
    location: str | None = None
    url: str | None = None
    source: str | None = None
    language: str | None = None
    description: str | None = Field(default=None, sa_type=Text)
    posted_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Audit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    posting_id: int = Field(foreign_key="posting.id", index=True, ondelete="CASCADE")
    score: float | None = None
    summary: str | None = Field(default=None, sa_type=Text)
    details: dict = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=utcnow)


class Application(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    posting_id: int = Field(foreign_key="posting.id", index=True)
    status: ApplicationStatus = Field(
        default=ApplicationStatus.DRAFT, sa_type=enum_type(ApplicationStatus)
    )
    applied_at: datetime | None = None
    notes: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Document(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    application_id: int | None = Field(default=None, foreign_key="application.id", index=True)
    kind: DocumentKind = Field(sa_type=enum_type(DocumentKind))
    title: str
    content: str | None = Field(default=None, sa_type=Text)
    path: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class ProviderConfig(SQLModel, table=True):
    """LLM provider settings. Deliberately has no secret/API-key column."""

    __tablename__ = "provider_config"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    provider: str
    model: str | None = None
    base_url: str | None = None
    enabled: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    status: TaskStatus = Field(default=TaskStatus.TODO, sa_type=enum_type(TaskStatus))
    due_at: datetime | None = None
    application_id: int | None = Field(default=None, foreign_key="application.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)


# --- Integrity guards ------------------------------------------------------

# Set ``session.info[SOURCE_SYNC] = True`` to mark a session as syncing from
# candidate_context.md. Only such sessions may touch locked fields.
SOURCE_SYNC = "careerflow.source_sync"


class LockedFieldError(RuntimeError):
    pass


@event.listens_for(SASession, "before_flush")
def _guard_locked_fields(session: SASession, _ctx, _instances) -> None:
    if session.info.get(SOURCE_SYNC):
        return
    for obj in session.dirty:
        if isinstance(obj, Profile):
            if inspect(obj).attrs.german_level.history.has_changes():
                raise LockedFieldError(
                    "Profile.german_level is locked to candidate_context.md; re-run the seed instead."
                )
        elif isinstance(obj, ProfileItem):
            hist = inspect(obj).attrs.status.history
            if ItemStatus.IN_PROGRESS in hist.deleted and obj.status == ItemStatus.COMPLETED:
                raise LockedFieldError(
                    f"ProfileItem {obj.title!r} is in-progress in candidate_context.md "
                    "and cannot be marked completed here."
                )
