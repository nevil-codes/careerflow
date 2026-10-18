from fastapi import APIRouter
from sqlmodel import col, select

from app.api.deps import SessionDep, get_or_404
from app.models import Posting, PostingCreate, PostingRead, PostingUpdate, utcnow

router = APIRouter(prefix="/postings", tags=["postings"])


def to_read(posting: Posting) -> PostingRead:
    app = posting.application
    return PostingRead.model_validate(
        posting,
        update={
            "application_id": app.id if app else None,
            "application_status": app.status if app else None,
        },
    )


@router.get("", response_model=list[PostingRead])
def list_postings(session: SessionDep, q: str | None = None) -> list[PostingRead]:
    query = select(Posting).order_by(col(Posting.created_at).desc(), col(Posting.id).desc())
    if q:
        pattern = f"%{q}%"
        query = query.where(col(Posting.title).ilike(pattern) | col(Posting.company).ilike(pattern))
    return [to_read(p) for p in session.exec(query)]


@router.post("", response_model=PostingRead, status_code=201)
def create_posting(data: PostingCreate, session: SessionDep) -> PostingRead:
    posting = Posting.model_validate(data)
    session.add(posting)
    session.commit()
    session.refresh(posting)
    return to_read(posting)


@router.get("/{posting_id}", response_model=PostingRead)
def get_posting(posting_id: int, session: SessionDep) -> PostingRead:
    return to_read(get_or_404(session, Posting, posting_id))


@router.patch("/{posting_id}", response_model=PostingRead)
def update_posting(posting_id: int, data: PostingUpdate, session: SessionDep) -> PostingRead:
    posting = get_or_404(session, Posting, posting_id)
    posting.sqlmodel_update(data.model_dump(exclude_unset=True))
    posting.updated_at = utcnow()
    session.commit()
    session.refresh(posting)
    return to_read(posting)


@router.delete("/{posting_id}", status_code=204)
def delete_posting(posting_id: int, session: SessionDep) -> None:
    """Also deletes the posting's application, its history and tasks."""
    session.delete(get_or_404(session, Posting, posting_id))
    session.commit()
