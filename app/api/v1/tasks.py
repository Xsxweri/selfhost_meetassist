from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.workers.celery_app import celery

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}")
async def api_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """查询异步任务状态：PENDING/STARTED/SUCCESS/FAILURE"""
    res = AsyncResult(task_id, app=celery)
    return {
        "task_id": task_id,
        "status": res.status,
        "ready": res.ready(),
        "result": res.result if res.ready() else None,
    }