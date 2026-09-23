import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.curd.audit_log import list_audit_logs
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse

router = APIRouter(prefix="/audits", tags=["Audits"])


@router.get("", response_model=list[AuditLogResponse])
async def api_list_my_audits(
    meeting_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看当前用户的审计日志（可按会议过滤）"""
    return await list_audit_logs(
        db, user_id=current_user.id, meeting_id=meeting_id, skip=skip, limit=limit
    )