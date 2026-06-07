"""Task manager with pause/cancel/resume and checkpoint resume."""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.database import new_session
from app.models.task import Task
from app.models.patent import Patent
from app.models.quintuple import Quintuple

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages extraction task lifecycle via asyncio + PostgreSQL state machine."""

    def __init__(self):
        self._running: dict[int, asyncio.Task] = {}

    async def submit(self, patent_id: int, user_id: int = None) -> int:
        db = new_session()
        try:
            existing = (
                db.query(Task)
                .filter(Task.patent_id == patent_id, Task.status == "completed")
                .first()
            )
            if existing:
                return existing.id

            task = Task(patent_id=patent_id, user_id=user_id, status="pending")
            db.add(task)
            db.commit()
            db.refresh(task)
            task_id = task.id
            task.status = "queued"
            db.commit()

            asyncio_task = asyncio.create_task(self._execute(task_id))
            self._running[task_id] = asyncio_task
            return task_id
        finally:
            db.close()

    async def pause(self, task_id: int):
        db = new_session()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task and task.status in Task.PAUSABLE_STATUSES:
                task.status = "paused"
                db.commit()
        finally:
            db.close()

    async def resume(self, task_id: int):
        db = new_session()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task and task.status in Task.RESUMABLE_STATUSES:
                task.status = "queued"
                db.commit()
                asyncio_task = asyncio.create_task(self._execute(task_id))
                self._running[task_id] = asyncio_task
        finally:
            db.close()

    async def cancel(self, task_id: int):
        db = new_session()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task and task.status in Task.CANCELLABLE_STATUSES:
                task.status = "cancelled"
                db.commit()
            t = self._running.pop(task_id, None)
            if t and not t.done():
                t.cancel()
        finally:
            db.close()

    def get_status(self, task_id: int) -> Optional[dict]:
        db = new_session()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None
            return {
                "id": task.id,
                "patent_id": task.patent_id,
                "status": task.status,
                "progress": task.progress,
                "current_step": task.current_step,
                "error": task.error_message,
                "result_count": task.result_count,
            }
        finally:
            db.close()

    async def _execute(self, task_id: int):
        db = new_session()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return
            task.status = "running"
            task.started_at = datetime.utcnow()
            db.commit()

            patent = db.query(Patent).filter(Patent.id == task.patent_id).first()
            if not patent:
                task.status = "failed"
                task.error_message = "Patent not found"
                db.commit()
                return

            # Step 1: Parse PDF
            await self._check_pause_cancel(task_id, db)
            self._update_progress(task, db, 10, "parsing_pdf")
            from app.services.pipeline_service import run_pipeline_for_patent

            # Step 2-4: Run pipeline
            quints = await run_pipeline_for_patent(
                patent,
                progress_callback=lambda p, step: self._update_progress(
                    task, db, 10 + int(p * 0.8), step
                ),
            )

            # Step 5: Save results
            await self._check_pause_cancel(task_id, db)
            self._update_progress(task, db, 95, "saving_results")
            for q in quints:
                db.add(
                    Quintuple(
                        patent_id=patent.id,
                        task_id=task_id,
                        name=q.name,
                        value=q.value,
                        relation=q.relation,
                        object=q.object,
                        condition=q.condition,
                        source_text=q.source_text,
                        confidence=q.confidence,
                    )
                )

            task.status = "completed"
            task.progress = 100
            task.result_count = len(quints)
            task.completed_at = datetime.utcnow()
            db.commit()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            db_err = new_session()
            try:
                t = db_err.query(Task).filter(Task.id == task_id).first()
                if t and t.status not in Task.TERMINAL_STATUSES:
                    t.status = "failed"
                    t.error_message = str(e)[:500]
                    db_err.commit()
            finally:
                db_err.close()
        finally:
            self._running.pop(task_id, None)
            db.close()

    async def _check_pause_cancel(self, task_id: int, db):
        while True:
            db.expire_all()
            task = db.query(Task).filter(Task.id == task_id).first()
            if task.status == "cancelled":
                raise asyncio.CancelledError()
            if task.status != "paused":
                break
            await asyncio.sleep(1)

    def _update_progress(self, task, db, progress: int, step: str):
        task.progress = min(progress, 99)
        task.current_step = step
        db.commit()


task_manager = TaskManager()
