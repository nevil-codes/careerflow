"""Sync the database from candidate_context.md (the source of truth).

Items are upserted by (type, title) so their IDs stay stable across re-seeds;
items no longer in the file are removed. After commit the stored statuses and
German level are re-read and compared with the file, and any drift is an error.
"""

from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import SOURCE_SYNC, Profile, ProfileItem, utcnow
from app.seed.parser import CandidateContext


class SeedIntegrityError(RuntimeError):
    pass


@dataclass
class SeedResult:
    profile_id: int
    created: int
    updated: int
    deleted: int


def seed_profile(session: Session, ctx: CandidateContext) -> SeedResult:
    session.info[SOURCE_SYNC] = True
    try:
        result = _apply(session, ctx)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.info.pop(SOURCE_SYNC, None)
    verify_seed(session, ctx)
    return result


def _apply(session: Session, ctx: CandidateContext) -> SeedResult:
    # Single-user app: there is at most one profile.
    profile = session.exec(select(Profile)).first()
    if profile is None:
        profile = Profile.model_validate(ctx.profile)
        session.add(profile)
        session.flush()
    elif _assign(profile, ctx.profile.model_dump()):
        profile.updated_at = utcnow()
    assert profile.id is not None

    existing = {
        (item.type, item.title): item
        for item in session.exec(select(ProfileItem).where(ProfileItem.profile_id == profile.id))
    }
    created = updated = 0
    for parsed in ctx.items:
        row = existing.pop((parsed.type, parsed.title), None)
        if row is None:
            session.add(ProfileItem.model_validate(parsed, update={"profile_id": profile.id}))
            created += 1
        elif _assign(row, parsed.model_dump()):
            row.updated_at = utcnow()
            updated += 1
    for stale in existing.values():
        session.delete(stale)

    return SeedResult(profile.id, created, updated, len(existing))


def _assign(row: Profile | ProfileItem, values: dict) -> bool:
    changed = False
    for key, value in values.items():
        if getattr(row, key) != value:
            setattr(row, key, value)
            changed = True
    return changed


def verify_seed(session: Session, ctx: CandidateContext) -> None:
    session.expire_all()
    profile = session.exec(select(Profile)).one()
    if profile.german_level != ctx.profile.german_level:
        raise SeedIntegrityError(
            f"german_level stored as {profile.german_level!r}, file says {ctx.profile.german_level!r}"
        )
    stored = {
        (item.type, item.title): item.status
        for item in session.exec(select(ProfileItem).where(ProfileItem.profile_id == profile.id))
    }
    expected = {(item.type, item.title): item.status for item in ctx.items}
    if stored != expected:
        drift = sorted(
            f"{t}:{title} stored={stored.get((t, title))} file={expected.get((t, title))}"
            for t, title in stored.keys() | expected.keys()
            if stored.get((t, title)) != expected.get((t, title))
        )
        raise SeedIntegrityError("status drift after seed: " + "; ".join(drift))
