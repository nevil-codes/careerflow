from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.deps import SessionDep, get_or_404
from app.models import (
    Application,
    ApplicationCreate,
    ApplicationDetail,
    ApplicationRead,
    ApplicationStatus,
    ApplicationUpdate,
    Posting,
    TaskStatus,
    utcnow,
)

router = APIRouter(prefix="/applications", tags=["applications"])


def to_read(app: Application) -> ApplicationRead:
    return ApplicationRead.model_validate(
        app,
        update={
            "posting": app.posting,
            "open_tasks": sum(t.status != TaskStatus.DONE for t in app.tasks),
        },
    )


def to_detail(app: Application) -> ApplicationDetail:
    return ApplicationDetail.model_validate(
        to_read(app), update={"events": app.events, "tasks": app.tasks}
    )


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    session: SessionDep, status: ApplicationStatus | None = None
) -> list[ApplicationRead]:
    query = select(Application).order_by(col(Application.updated_at).desc())
    if status is not None:
        query = query.where(Application.status == status)
    return [to_read(a) for a in session.exec(query)]


@router.post("", response_model=ApplicationDetail, status_code=201)
def create_application(data: ApplicationCreate, session: SessionDep) -> ApplicationDetail:
    posting = get_or_404(session, Posting, data.posting_id)
    if posting.application is not None:
        raise HTTPException(409, f"Posting {posting.id} already has application {posting.application.id}")
    app = Application.model_validate(data)
    session.add(app)
    session.commit()
    session.refresh(app)
    return to_detail(app)


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(application_id: int, session: SessionDep) -> ApplicationDetail:
    return to_detail(get_or_404(session, Application, application_id))


@router.patch("/{application_id}", response_model=ApplicationDetail)
def update_application(
    application_id: int, data: ApplicationUpdate, session: SessionDep
) -> ApplicationDetail:
    """Any status may move to any other; every change is recorded in the history."""
    app = get_or_404(session, Application, application_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("status", app.status) is None:
        raise HTTPException(422, "status cannot be null")
    app.sqlmodel_update(changes)
    app.updated_at = utcnow()
    session.commit()
    session.refresh(app)
    return to_detail(app)


@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: int, session: SessionDep) -> None:
    """Also deletes its history and tasks. The posting is kept."""
    session.delete(get_or_404(session, Application, application_id))
    session.commit()
