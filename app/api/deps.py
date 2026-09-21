import uuid
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.curd.user import get_user_by_id
from app.db.session import AsyncSessionLocal
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 提取数据库依赖，供所有 API 路由使用
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exc
    sub = payload.get("sub")
    if sub is None:
        raise credentials_exc
    try:
        user_id = uuid.UUID(sub)
    except ValueError:
        raise credentials_exc
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exc
    return user