import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.consent import Consent, ConsentType, ConsentAction

async def create_consent(db:AsyncSession, meeting_id:uuid.UUID, user_id:uuid.UUID, consent_type:ConsentType,action:ConsentAction,
ip_address:str | None = None, user_agent:str | None = None, note:str | None = None,
) -> Consent:
    """创建授权事件"""
    consent = Consent(
        meeting_id=meeting_id,
        user_id=user_id,
        consent_type=consent_type.value,
        action=action.value,
        ip_address=ip_address,
        user_agent=user_agent,
        note=note,
    )
    db.add(consent)
    await db.commit()
    await db.refresh(consent)
    return consent

async def list_consents(db:AsyncSession, meeting_id:uuid.UUID, user_id:uuid.UUID) -> list[Consent]:
    """按时间倒序取所有事件"""
    result = await db.execute(
       select(Consent)
       .where(Consent.meeting_id == meeting_id, Consent.user_id == user_id)
       .order_by(Consent.created_at.desc())
    )
    return list(result.scalars().all())

async def get_consent_status(db:AsyncSession, meeting_id:uuid.UUID, user_id: uuid.UUID) -> list[dict]:
    """按类型取最新事件，计算当前生效状态"""
    rows = await list_consents(db, meeting_id, user_id)
    latest: dict[str, Consent] = {}
    for r in rows:
        latest.setdefault(r.consent_type, r)
    status = []
    for t in ConsentType:
        rec = latest.get(t.value)
        status.append({
            "consent_type": t.value,
            "granted": bool(rec and rec.action == ConsentAction.GRANT.value),
            "updated_at": rec.created_at if rec else None,
        })
    return status