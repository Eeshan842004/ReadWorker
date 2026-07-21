from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth.dependencies import get_current_user
from app.auth.jwt_handler import create_access_token, hash_password, verify_password
from app.auth.models import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from app.database.connection import get_session
from app.database.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    async with get_session() as session:
        existing = await session.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")
        user = User(email=payload.email, hashed_password=hash_password(payload.password))
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id, {"email": user.email}))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id, {"email": user.email}))


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)):
    return UserPublic(id=user.id, email=user.email)
