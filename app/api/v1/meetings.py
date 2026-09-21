import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.curd.meeting import (
    create_meeting,
    delete_meeting,
    get_meeting,
    list_meetings,
    update_meeting,
)
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingResponse, MeetingUpdate

router = APIRouter(prefix="/meetings", tags=["Meetings"])

@router.post("", response_model=MeetingResponse, status_code=201)
async def api_create_meeting(
    meeting_in: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_meeting(db, meeting_in, owner_id=current_user.id)

@router.get("", response_model=list[MeetingResponse])
async def api_list_meetings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await list_meetings(db, skip=skip, limit=limit, owner_id=current_user.id)

@router.get("/{meeting_id}", response_model=MeetingResponse)
async def api_get_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = await get_meeting(db, meeting_id, owner_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting

@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def api_update_meeting(
    meeting_id: uuid.UUID,
    meeting_in: MeetingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = await get_meeting(db, meeting_id, owner_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return await update_meeting(db, meeting, meeting_in)

@router.delete("/{meeting_id}", status_code=204)
async def api_delete_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = await get_meeting(db, meeting_id, owner_id=current_user.id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await delete_meeting(db, meeting)