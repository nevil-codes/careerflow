"""Database models and the Pydantic schemas shared with the API.

Each entity follows the SQLModel pattern: a ``*Base`` class holds the shared
fields, the ``table=True`` class adds DB-only columns, and ``*Read`` classes
are the API response schemas.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import field_validator
from sqlalchemy import JSON, Text, UniqueConstraint, event, inspect
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Session as SASession
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_type(enum_cls: type[StrEnum], name: str | None = None) -> SAEnum:
    """Store enum *values* as VARCHAR with a CHECK constraint (portable, readable).

    ``name`` names the CHECK constraint; pass one when a table has two columns of
    the same enum so the constraint names don't collide.
    """
    return SAEnum(
        enum_cls,
        name=name or enum_cls.__name__.lower(),
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


# --- Input validation helpers ---------------------------------------------


def _strip_or_none(value: object) -> object:
    """Trim strings; blank optional strings become None."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _not_null(value: object) -> object:
    """For PATCH schemas: a required field may be omitted but not cleared."""
    if value is None:
        raise ValueError("cannot be blank")
    return value


def _check_url(value: str | None) -> str | None:
    if value is not None and not value.startswith(("http://", "https://")):
        raise ValueError("must start with http:// or https://")
    return value


# --- Postings --------------------------------------------------------------


class PostingBase(SQLModel):
    # Fields are kept in English; for non-English postings the title as written is in
    # title_original (company names are never translated).
    title: str
    title_original: str | None = None
    company: str
    location: str | None = None
    url: str | None = None
    source: str | None = None
    language: str | None = None
    # The pasted job description, stored verbatim.
    description: str | None = Field(default=None, sa_type=Text)
    posted_at: datetime | None = None


class Posting(PostingBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    application: "Application" = Relationship(
        back_populates="posting", cascade_delete=True, sa_relationship_kwargs={"uselist": False}
    )


class PostingCreate(PostingBase):
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)

    _strip = field_validator(
        "title", "title_original", "company", "location", "url", "source", "language", mode="before"
    )(_strip_or_none)
    _url = field_validator("url")(_check_url)


class PostingUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1)
    title_original: str | None = None
    company: str | None = Field(default=None, min_length=1)
    location: str | None = None
    url: str | None = None
    source: str | None = None
    language: str | None = None
    description: str | None = None
    posted_at: datetime | None = None

    _strip = field_validator(
        "title", "title_original", "company", "location", "url", "source", "language", mode="before"
    )(_strip_or_none)
    _url = field_validator("url")(_check_url)
    _required = field_validator("title", "company")(_not_null)


class PostingFromText(SQLModel):
    """Paste-only intake: everything else is extracted from the text."""

    description: str

    @field_validator("description")
    @classmethod
    def _long_enough(cls, value: str) -> str:
        # Stored verbatim; only checked for substance.
        if len(value.strip()) < 40:
            raise ValueError("paste the full job description")
        return value


class PostingRead(PostingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    application_id: int | None = None
    application_status: ApplicationStatus | None = None


class PostingSummary(SQLModel):
    id: int
    title: str
    company: str


class Audit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    posting_id: int = Field(foreign_key="posting.id", index=True, ondelete="CASCADE")
    score: float | None = None
    summary: str | None = Field(default=None, sa_type=Text)
    details: dict = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=utcnow)


# --- Applications ----------------------------------------------------------


class Application(SQLModel, table=True):
    # One application per posting.
    __table_args__ = (UniqueConstraint("posting_id", name="uq_application_posting_id"),)

    id: int | None = Field(default=None, primary_key=True)
    posting_id: int = Field(foreign_key="posting.id", index=True)
    status: ApplicationStatus = Field(
        default=ApplicationStatus.DRAFT, sa_type=enum_type(ApplicationStatus)
    )
    applied_at: datetime | None = None
    notes: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    posting: Posting = Relationship(back_populates="application")
    events: list["ApplicationEvent"] = Relationship(
        back_populates="application",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "ApplicationEvent.id"},
    )
    tasks: list["Task"] = Relationship(back_populates="application", cascade_delete=True)


class ApplicationEvent(SQLModel, table=True):
    """Append-only status history. One row per status change, including creation."""

    __tablename__ = "application_event"

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", index=True, ondelete="CASCADE")
    from_status: ApplicationStatus | None = Field(
        default=None, sa_type=enum_type(ApplicationStatus, "ck_application_event_from_status")
    )
    to_status: ApplicationStatus = Field(
        sa_type=enum_type(ApplicationStatus, "ck_application_event_to_status")
    )
    created_at: datetime = Field(default_factory=utcnow)

    application: Application = Relationship(back_populates="events")


class ApplicationCreate(SQLModel):
    posting_id: int
    status: ApplicationStatus = ApplicationStatus.DRAFT
    applied_at: datetime | None = None
    notes: str | None = None


class ApplicationUpdate(SQLModel):
    status: ApplicationStatus | None = None
    applied_at: datetime | None = None
    notes: str | None = None


class ApplicationEventRead(SQLModel):
    id: int
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    created_at: datetime


class ApplicationRead(SQLModel):
    id: int
    posting_id: int
    status: ApplicationStatus
    applied_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    posting: PostingSummary
    open_tasks: int = 0


class Document(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    application_id: int | None = Field(default=None, foreign_key="application.id", index=True)
    kind: DocumentKind = Field(sa_type=enum_type(DocumentKind))
    title: str
    content: str | None = Field(default=None, sa_type=Text)
    path: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


# --- LLM providers -----------------------------------------------------------

# Provider kinds the app can talk to. Cloud providers come later; their keys will be
# read from the environment / OS keychain, never stored in this table.
ProviderKind = Literal["ollama", "anthropic"]


class ProviderConfigBase(SQLModel):
    name: str = Field(unique=True)
    provider: str
    model: str | None = None
    base_url: str | None = None
    # At most one config is enabled; it is the provider every LLM feature uses.
    enabled: bool = False


class ProviderConfig(ProviderConfigBase, table=True):
    """LLM provider settings. Deliberately has no secret/API-key column."""

    __tablename__ = "provider_config"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class ProviderConfigCreate(SQLModel):
    name: str = Field(min_length=1)
    provider: ProviderKind = "ollama"
    model: str | None = None
    base_url: str | None = None
    enabled: bool = False

    _strip = field_validator("name", "model", "base_url", mode="before")(_strip_or_none)
    _url = field_validator("base_url")(_check_url)


class ProviderConfigUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1)
    model: str | None = None
    base_url: str | None = None
    enabled: bool | None = None

    _strip = field_validator("name", "model", "base_url", mode="before")(_strip_or_none)
    _url = field_validator("base_url")(_check_url)
    _required = field_validator("name", "base_url", "enabled")(_not_null)


class ProviderConfigRead(ProviderConfigBase):
    id: int
    created_at: datetime


# --- Tasks -----------------------------------------------------------------


class TaskBase(SQLModel):
    title: str
    status: TaskStatus = Field(default=TaskStatus.TODO, sa_type=enum_type(TaskStatus))
    due_at: datetime | None = None
    application_id: int | None = Field(default=None, foreign_key="application.id", index=True)


class Task(TaskBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)

    application: Application | None = Relationship(back_populates="tasks")


class TaskCreate(TaskBase):
    title: str = Field(min_length=1)

    _strip = field_validator("title", mode="before")(_strip_or_none)


class TaskUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1)
    status: TaskStatus | None = None
    due_at: datetime | None = None

    _strip = field_validator("title", mode="before")(_strip_or_none)
    _required = field_validator("title", "status")(_not_null)


class TaskRead(TaskBase):
    id: int
    created_at: datetime


class ApplicationDetail(ApplicationRead):
    events: list[ApplicationEventRead]
    tasks: list[TaskRead]


# --- Integrity guards ------------------------------------------------------

# Set ``session.info[SOURCE_SYNC] = True`` to mark a session as syncing from
# candidate_context.md. Only such sessions may touch locked fields.
SOURCE_SYNC = "careerflow.source_sync"


class LockedFieldError(RuntimeError):
    pass


@event.listens_for(SASession, "before_flush")
def _guard_locked_fields(session: SASession, _ctx, _instances) -> None:
    """The profile tables are read-only except to the seed (candidate_context.md).

    This covers every writer, including future LLM features: they can read the
    profile but any insert, update or delete outside the seed fails the flush.
    """
    if session.info.get(SOURCE_SYNC):
        return
    for obj in session.dirty:
        if not session.is_modified(obj):
            continue
        if isinstance(obj, Profile):
            if inspect(obj).attrs.german_level.history.has_changes():
                raise LockedFieldError(
                    "Profile.german_level is locked to candidate_context.md; re-run the seed instead."
                )
            raise LockedFieldError(_READ_ONLY)
        if isinstance(obj, ProfileItem):
            hist = inspect(obj).attrs.status.history
            if ItemStatus.IN_PROGRESS in hist.deleted and obj.status == ItemStatus.COMPLETED:
                raise LockedFieldError(
                    f"ProfileItem {obj.title!r} is in-progress in candidate_context.md "
                    "and cannot be marked completed here."
                )
            raise LockedFieldError(_READ_ONLY)
    for obj in (*session.new, *session.deleted):
        if isinstance(obj, (Profile, ProfileItem)):
            raise LockedFieldError(_READ_ONLY)


_READ_ONLY = "The profile is read-only here; edit candidate_context.md and re-run the seed."


@event.listens_for(SASession, "before_flush")
def _record_application_history(session: SASession, _ctx, _instances) -> None:
    """Every application status change, from any code path, lands in application_event."""
    for obj in list(session.new):
        if isinstance(obj, Application):
            _on_status_change(obj, None)
    for obj in list(session.dirty):
        if isinstance(obj, Application):
            hist = inspect(obj).attrs.status.history
            if hist.has_changes() and hist.deleted and hist.deleted[0] != obj.status:
                _on_status_change(obj, hist.deleted[0])
                obj.updated_at = utcnow()


def _on_status_change(app: Application, previous: ApplicationStatus | None) -> None:
    app.events.append(ApplicationEvent(from_status=previous, to_status=app.status))
    if app.status != ApplicationStatus.DRAFT and app.applied_at is None:
        app.applied_at = utcnow()
