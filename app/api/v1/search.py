import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.curd.meeting import get_meeting
from app.models.user import User
from app.schemas.search import SearchResponse
from app.services.llm_service import LlmService

router = APIRouter(tags=["Search"])


@router.get("/meetings/{meeting_id}/search", response_model=SearchResponse)
async def search_in_meeting(
    meeting_id: uuid.UUID,
    q: str = Query(..., min_length=1, description="检索词"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """在指定会议内做语义检索（先校验归属）"""
    meeting = await get_meeting(db, meeting_id, owner_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    results = await LlmService(db).semantic_search(
        q, owner_id=str(current_user.id), meeting_id=str(meeting_id), limit=limit
    )
    return SearchResponse(query=q, count=len(results), results=results)


@router.get("/search", response_model=SearchResponse)
async def search_all(
    q: str = Query(..., min_length=1, description="检索词"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """跨当前用户的全部会议做语义检索"""
    results = await LlmService(db).semantic_search(
        q, owner_id=str(current_user.id), limit=limit
    )
    return SearchResponse(query=q, count=len(results), results=results)