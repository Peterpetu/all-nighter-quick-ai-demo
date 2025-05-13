# file: app/agents/task_creation_agent.py

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

import dateparser
from pydantic import BaseModel, Field, ValidationError
from pydantic.fields import FieldInfo
from pydantic_ai import RunContext
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from app.agents.base import BaseAgent
from app.db import get_session
from app.models import Task, TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)

# Sub-tool outputs
class TaskCreationOutput(BaseModel):
    id: Optional[int] = Field(None, description="Task ID")
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    completed: Optional[bool] = False
    error: Optional[str] = Field(None, description="Error message, if any")

class TaskDeletionOutput(BaseModel):
    id: Optional[int] = Field(None, description="Task ID")
    deleted: Optional[bool] = False
    error: Optional[str] = Field(None, description="Error message, if any")


class TaskCreationAgent(BaseAgent):
    """
    Agent that can create, update, and delete tasks via internal sub-tools.
    The final output from this agent is plain text summarizing the result.
    """

    def __init__(self):
        # Load system prompt
        prompt_path = Path(__file__).parent / "system_prompts" / "task_creation_agent.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Missing system prompt: {prompt_path}")
        system_prompt = prompt_path.read_text(encoding="utf-8")

        # We'll produce a final plain string describing success/failure
        super().__init__(
            model="openai:gpt-4o",
            system_prompt=system_prompt,
            tools=[],
            output_type=str,
            memory_size=100,
        )

        # ---- Create Tool ----
        @self.agent.tool
        async def create_task(
            ctx: RunContext,
            title: str = Field(..., description="Task title"),
            description: Optional[str] = Field(None, description="Task description"),
            due_date: Optional[str] = Field(
                None, description="Due date (free-form, e.g. 'tomorrow at 9am')"
            ),
        ) -> TaskCreationOutput:
            """
            Sub-tool: actually create a task in the DB.
            The LLM calls this function to do the real DB operation.
            """
            if isinstance(title, FieldInfo):
                title = None
            if isinstance(description, FieldInfo):
                description = None
            if isinstance(due_date, FieldInfo):
                due_date = None

            parsed_due_obj = None
            parsed_due_str = None
            if due_date:
                parsed_due_obj = dateparser.parse(
                    due_date,
                    settings={
                        "RELATIVE_BASE": datetime.utcnow(),
                        "PREFER_DATES_FROM": "future"
                    },
                )
                if parsed_due_obj:
                    parsed_due_str = parsed_due_obj.isoformat()
                else:
                    logger.warning("dateparser failed on due_date=%r", due_date)

            # Validate payload
            try:
                payload = TaskCreate(
                    title=title,
                    description=description,
                    due_date=parsed_due_obj,
                )
            except ValidationError as e:
                logger.error("Invalid create payload: %s", e, exc_info=True)
                return TaskCreationOutput(error=f"Invalid data: {e}")

            # Persist
            try:
                session = next(get_session())
                task = Task.from_orm(payload)
                session.add(task)
                session.commit()
                session.refresh(task)
            except SQLAlchemyError as e:
                logger.error("DB error creating task: %s", e, exc_info=True)
                return TaskCreationOutput(error="Database error when creating task")
            except Exception as e:
                logger.error("Unexpected create error: %s", e, exc_info=True)
                return TaskCreationOutput(error="Unexpected error when creating task")

            return TaskCreationOutput(
                id=task.id,
                title=task.title,
                description=task.description,
                due_date=parsed_due_str or (task.due_date.isoformat() if task.due_date else None),
                completed=task.completed,
            )

        # ---- Update Tool ----
        @self.agent.tool
        async def update_task(
            ctx: RunContext,
            id: int = Field(..., description="ID of the task to update"),
            title: Optional[str] = Field(None, description="New title"),
            description: Optional[str] = Field(None, description="New description"),
            due_date: Optional[str] = Field(None, description="New due date"),
            completed: Optional[bool] = Field(None, description="Mark done?"),
        ) -> TaskCreationOutput:
            if isinstance(title, FieldInfo):
                title = None
            if isinstance(description, FieldInfo):
                description = None
            if isinstance(due_date, FieldInfo):
                due_date = None
            if isinstance(completed, FieldInfo):
                completed = None

            try:
                task_id = int(id)
            except (TypeError, ValueError):
                return TaskCreationOutput(error=f"Invalid task ID: {id}")

            # 3. Parse new due_date
            parsed_due_obj = None
            parsed_due_str = None
            if due_date is not None:
                parsed_due_obj = dateparser.parse(
                    due_date,
                    settings={
                        "RELATIVE_BASE": datetime.utcnow(),
                        "PREFER_DATES_FROM": "future"
                    },
                )
                if parsed_due_obj:
                    parsed_due_str = parsed_due_obj.isoformat()
                else:
                    logger.warning("dateparser failed on due_date=%r", due_date)

            # 4. Fetch existing task
            session = next(get_session())
            task = session.exec(select(Task).where(Task.id == task_id)).one_or_none()
            if not task:
                return TaskCreationOutput(error=f"Task {task_id} not found")

            # 5. Build update payload
            try:
                updates = TaskUpdate(
                    title=title,
                    description=description,
                    due_date=parsed_due_obj,
                    completed=completed,
                )
            except ValidationError as e:
                logger.error("Invalid update payload: %s", e, exc_info=True)
                return TaskCreationOutput(error=f"Invalid data: {e}")

            update_data = updates.dict(exclude_unset=True, exclude_none=True)
            if not update_data:
                return TaskCreationOutput(
                    error="No fields provided to update; please specify title, description, due_date, or completed."
                )

            # 6. Apply and commit
            for field_name, val in update_data.items():
                setattr(task, field_name, val)
            task.updated_at = datetime.utcnow()

            try:
                session.add(task)
                session.commit()
                session.refresh(task)
            except SQLAlchemyError as e:
                logger.error("DB error updating task: %s", e, exc_info=True)
                return TaskCreationOutput(error="Database error when updating task")
            except Exception as e:
                logger.error("Unexpected update error: %s", e, exc_info=True)
                return TaskCreationOutput(error="Unexpected error when updating task")

            # 7. Return updated record
            return TaskCreationOutput(
                id=task.id,
                title=task.title,
                description=task.description,
                due_date=parsed_due_str or (task.due_date.isoformat() if task.due_date else None),
                completed=task.completed,
            )

        # ---- Delete Tool ----
        @self.agent.tool
        async def delete_task(
            ctx: RunContext,
            id: int = Field(..., description="ID of the task to delete"),
        ) -> TaskDeletionOutput:
            try:
                task_id = int(id)
            except (TypeError, ValueError):
                return TaskDeletionOutput(error=f"Invalid task ID: {id}")

            try:
                session = next(get_session())
                task = session.exec(select(Task).where(Task.id == task_id)).one_or_none()
                if not task:
                    return TaskDeletionOutput(id=task_id, deleted=False, error="Task not found")
                session.delete(task)
                session.commit()
            except Exception as e:
                logger.error("Error deleting task: %s", e, exc_info=True)
                return TaskDeletionOutput(id=task_id, deleted=False, error="Error deleting task")

            return TaskDeletionOutput(id=task_id, deleted=True)

    async def run(
        self,
        user_message: str,
        injections: Optional[Dict[str, str]] = None,
        deps: Optional[int] = None,
    ) -> str:
        """
        We override run() to inject the current timestamp + existing tasks if we want.
        Then we rely on the LLM to call the relevant sub-tool(s) and produce a final textual summary.
        """
        now = datetime.utcnow().isoformat()

        session = next(get_session())
        tasks = session.exec(select(Task)).all()
        if tasks:
            existing_tasks = "\n".join(
                f"{t.id}: {t.title} (due {t.due_date.isoformat() if t.due_date else 'None'}, completed={t.completed})"
                for t in tasks
            )
        else:
            existing_tasks = "No existing tasks."

        inj: Dict[str, str] = {
            "Current timestamp": now,
            "Existing tasks": existing_tasks,
        }
        if injections:
            inj.update(injections)

        # Call the base run, expecting a final string
        result_str = await super().run(user_message, injections=inj, deps=deps)
        if not isinstance(result_str, str):
            # In case something else was returned
            result_str = str(result_str)
        return result_str
