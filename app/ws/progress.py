"""WebSocket endpoint for real-time task progress."""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.task_manager import task_manager

router = APIRouter()


@router.websocket("/ws/progress/{task_id}")
async def task_progress(websocket: WebSocket, task_id: int):
    await websocket.accept()
    try:
        while True:
            status = task_manager.get_status(task_id)
            if status is None:
                await websocket.send_json({"error": "not found"})
                break
            await websocket.send_json(status)
            if status["status"] in ("completed", "cancelled", "failed"):
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
