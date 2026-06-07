"""Task routes: create, status, pause, resume, cancel."""
from fastapi import APIRouter, HTTPException
from app.services.task_manager import task_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/")
async def create_task(patent_id: int, user_id: int = None):
    task_id = await task_manager.submit(patent_id, user_id)
    return {"task_id": task_id}


@router.get("/{task_id}")
async def get_task(task_id: int):
    status = task_manager.get_status(task_id)
    if status is None:
        raise HTTPException(404, "Task not found")
    return status


@router.post("/{task_id}/pause")
async def pause_task(task_id: int):
    await task_manager.pause(task_id)
    return {"status": "paused"}


@router.post("/{task_id}/resume")
async def resume_task(task_id: int):
    await task_manager.resume(task_id)
    return {"status": "resumed"}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int):
    await task_manager.cancel(task_id)
    return {"status": "cancelled"}
