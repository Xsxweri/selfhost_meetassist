import secrets
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.share_link import ShareLink


def _gen_token() -> str:
    return secrets.token_urlsafe(24)


async def create_share_link(
    db: AsyncSession, *, meeting_id: uuid.UUID, created_by: uuid.UUID | None,
    allow_download: bool = True, expires_in_days: int | None = None,
) -> ShareLink:
    """为会议创建共享链接"""
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    link = ShareLink(
        meeting_id=meeting_id,
        created_by=created_by,
        allow_download=allow_download,
        expires_at=expires_at,
        token=_gen_token(),
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def list_share_links(db: AsyncSession, meeting_id: uuid.UUID) -> list[ShareLink]:
    """获取会议的共享链接列表"""
    result = await db.execute(
        select(ShareLink)
        .where(ShareLink.meeting_id == meeting_id)
        .order_by(ShareLink.created_at.desc())
    )
    return list(result.scalars().all())


async def get_share_link_by_token(db: AsyncSession, token: str) -> ShareLink | None:
    """根据 token 获取共享链接"""
    result = await db.execute(select(ShareLink).where(ShareLink.token == token))
    return result.scalar_one_or_none()


async def revoke_share_link(db: AsyncSession, link: ShareLink) -> ShareLink:
    """撤销共享链接"""
    link.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(link)
    return link


def is_link_active(link: ShareLink) -> bool:
    """判断共享链接是否有效"""
    if link.revoked_at:
        return False
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        return False
    return True