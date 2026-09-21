from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.curd.user import create_user, get_user_by_email
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    if await get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return await create_user(db, payload.email, hash_password(payload.password))


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserResponse)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user