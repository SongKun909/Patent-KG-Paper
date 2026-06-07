"""Task routes: create, list, status, pause, resume, cancel."""
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from app.services.task_manager import task_manager
from app.database import new_session
from app.models.task import Task
from app.templating import templates

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


@router.post("/")
async def create_task(request: Request, patent_id: int = Query(...), user_id: int = None):
    task_id = await task_manager.submit(patent_id, user_id)
    if _is_htmx(request):
        status = task_manager.get_status(task_id)
        return HTMLResponse(
            f'<div class="text-green-400 p-2">Task #{task_id} created — Status: {status["status"]}</div>'
        )
    return {"task_id": task_id}


@router.get("/")
def list_tasks(request: Request):
    """List all tasks (for HTMX polling)."""
    db = new_session()
    try:
        tasks = db.query(Task).order_by(Task.created_at.desc()).limit(20).all()
        items = [
            {
                "id": t.id,
                "patent_id": t.patent_id,
                "status": t.status,
                "progress": t.progress,
                "current_step": t.current_step or "pending",
                "result_count": t.result_count,
                "error_message": t.error_message,
            }
            for t in tasks
        ]
        if _is_htmx(request):
            return templates.TemplateResponse(
                "partials/task_rows.html",
                {"request": request, "tasks": items},
            )
        return {"tasks": items}
    finally:
        db.close()


@router.get("/{task_id}")
async def get_task(request: Request, task_id: int):
    status = task_manager.get_status(task_id)
    if status is None:
        raise HTTPException(404, "Task not found")
    if _is_htmx(request):
        return HTMLResponse(
            f"""<div class="bg-gray-700 p-4 rounded">
            <div class="flex justify-between"><span>Task #{status['id']}</span>
            <span class="px-2 py-1 rounded text-xs bg-{ 'green' if status['status']=='completed' else 'blue' if status['status']=='running' else 'gray' }-600">{status['status']}</span></div>
            <div class="w-full bg-gray-600 rounded h-2 mt-2"><div class="bg-blue-500 h-2 rounded" style="width:{status['progress']}%"></div></div>
            <div class="text-sm text-gray-400 mt-1">{status.get('current_step','')} — {status.get('result_count',0)} results</div></div>"""
        )
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
