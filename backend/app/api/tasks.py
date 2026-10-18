from fastapi import APIRouter
from sqlmodel import col, select

from app.api.deps import SessionDep, get_or_404
from app.models import Application, Task, TaskCreate, TaskRead, TaskStatus, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(
    session: SessionDep,
    application_id: int | None = None,
    status: TaskStatus | None = None,
    open: bool = False,
) -> list[Task]:
    """Ordered by due date (undated last). ``open=true`` hides done tasks."""
    query = select(Task).order_by(col(Task.due_at).is_(None), col(Task.due_at), col(Task.id))
    if application_id is not None:
        query = query.where(Task.application_id == application_id)
    if status is not None:
        query = query.where(Task.status == status)
    if open:
        query = query.where(Task.status != TaskStatus.DONE)
    return list(session.exec(query))


@router.post("", response_model=TaskRead, status_code=201)
def create_task(data: TaskCreate, session: SessionDep) -> Task:
    if data.application_id is not None:
        get_or_404(session, Application, data.application_id)
    task = Task.model_validate(data)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate, session: SessionDep) -> Task:
    task = get_or_404(session, Task, task_id)
    task.sqlmodel_update(data.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: SessionDep) -> None:
    session.delete(get_or_404(session, Task, task_id))
    session.commit()
