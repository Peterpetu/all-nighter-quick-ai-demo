from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from sqlmodel import select, Session

from app.models import Task, TaskCreate, TaskRead, TaskUpdate
from app.db import get_session

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[TaskRead])
def read_tasks(session: Session = Depends(get_session)):
    return session.exec(select(Task)).all()

@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, session: Session = Depends(get_session)):
    task = Task.from_orm(payload)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@router.get("/{task_id}", response_model=TaskRead)
def read_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task

@router.put("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    session.delete(task)
    session.commit()

@router.patch("/{task_id}/complete", response_model=TaskRead)
def complete_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    task.completed = True
    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
