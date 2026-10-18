"""Read-only profile context for prompts.

Builds a plain-text snapshot from the DB. Prompts never get ORM objects or a
session, and statuses / German level are passed through verbatim, with explicit
instructions not to restate them differently.
"""

from sqlmodel import Session, select

from app.models import ItemStatus, ItemType, Profile, ProfileItem

_SECTIONS = [
    (ItemType.EDUCATION, "Education"),
    (ItemType.JOB, "Experience"),
    (ItemType.PROJECT, "Projects"),
    (ItemType.COURSE, "Courses"),
]

PROFILE_RULES = """\
Rules for using the candidate profile:
- It is the only source of facts about the candidate. Never invent experience, skills or results.
- Each item's status is authoritative. Never describe an in-progress, planned or paused item as completed or finished.
- The German level is exactly as stated. Never round it up or claim a different level."""


def profile_context(session: Session) -> str | None:
    """The profile as prompt text, or None if no profile has been seeded."""
    profile = session.exec(select(Profile)).first()
    if profile is None:
        return None
    items = session.exec(
        select(ProfileItem)
        .where(ProfileItem.profile_id == profile.id)
        .order_by(ProfileItem.type, ProfileItem.position)
    ).all()

    lines = [f"Candidate: {profile.full_name}"]
    if profile.headline:
        lines.append(f"Headline: {profile.headline}")
    if profile.location:
        lines.append(f"Location: {profile.location}")
    lines.append(f"German level: {profile.german_level}")

    for item_type, heading in _SECTIONS:
        section = [i for i in items if i.type == item_type]
        if not section:
            continue
        lines += ["", f"## {heading}"]
        for item in section:
            lines.append(f"- {item.title} [status: {_status(item.status)}]")
            for label, value in (("Organization", item.organization), ("Period", item.period)):
                if value:
                    lines.append(f"  {label}: {value}")
            if item.stack:
                lines.append(f"  Stack: {', '.join(item.stack)}")
            for metric in item.metrics:
                lines.append(f"  Result: {metric}")
            if item.description:
                lines.append(f"  {item.description}")

    skills = [i.title for i in items if i.type == ItemType.SKILL]
    if skills:
        lines += ["", f"## Skills\n{', '.join(skills)}"]
    return "\n".join(lines)


def _status(status: ItemStatus | None) -> str:
    return status.value if status else "n/a"
