from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import ItemType, Profile, ProfileItem, ProfileItemRead, ProfileRead

router = APIRouter(prefix="/profile", tags=["profile"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_profile(session: Session) -> Profile:
    profile = session.exec(select(Profile)).first()
    if profile is None:
        raise HTTPException(404, "No profile yet. Run the seed script: `uv run python -m app.seed`.")
    return profile


@router.get("", response_model=ProfileRead)
def get_profile(session: SessionDep) -> Profile:
    return _get_profile(session)


@router.get("/items", response_model=list[ProfileItemRead])
def list_profile_items(session: SessionDep, type: ItemType | None = None) -> list[ProfileItem]:
    profile = _get_profile(session)
    query = select(ProfileItem).where(ProfileItem.profile_id == profile.id)
    if type is not None:
        query = query.where(ProfileItem.type == type)
    return list(session.exec(query.order_by(ProfileItem.type, ProfileItem.position)))
