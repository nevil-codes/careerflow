from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import Session, SQLModel

from app.db import get_session

SessionDep = Annotated[Session, Depends(get_session)]


def get_or_404[T: SQLModel](session: Session, model: type[T], id: int) -> T:
    obj = session.get(model, id)
    if obj is None:
        raise HTTPException(404, f"{model.__name__} {id} not found")
    return obj
