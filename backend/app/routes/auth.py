from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.collaboration import UserProfile
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def user_read(user: User, profile_completed: bool) -> UserRead:
    return UserRead.model_validate(user).model_copy(
        update={"profile_completed": profile_completed}
    )


def token_response(user: User, profile_completed: bool = False) -> TokenResponse:
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    return TokenResponse(
        access_token=token,
        user=user_read(user, profile_completed),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: DbSession) -> TokenResponse:
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
        phone=payload.phone,
        role="user",
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="用户名已存在") from None
    await session.refresh(user)
    return token_response(user, profile_completed=False)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: DbSession) -> TokenResponse:
    user = await session.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用")
    profile_completed = (
        await session.scalar(
            select(UserProfile.id).where(UserProfile.user_id == user.id)
        )
        is not None
    )
    return token_response(user, profile_completed=profile_completed)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser, session: DbSession) -> UserRead:
    profile_completed = (
        await session.scalar(
            select(UserProfile.id).where(UserProfile.user_id == user.id)
        )
        is not None
    )
    return user_read(user, profile_completed)
