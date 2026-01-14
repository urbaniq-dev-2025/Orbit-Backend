from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_state_token,
    hash_password,
    verify_password,
    verify_state_token,
)
from app.models import User, UserOAuthAccount
from app.schemas.auth import (
    GoogleAuthCompleteRequest,
    GoogleAuthInitRequest,
    GoogleAuthInitResponse,
    LoginRequest,
    PasswordResetCompleteRequest,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    PasswordResetVerifyResponse,
    SignupRequest,
    Token,
    UserProfileUpdateRequest,
)
from app.schemas.user import UserPublic
from app.services.google_oauth import GoogleOAuthClient, GoogleOAuthError, GoogleUserInfo
from app.services import password_reset as password_reset_service
from app.services.email import EmailRateLimitError, get_email_dispatcher

router = APIRouter()
logger = get_logger(__name__)


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, session: deps.SessionDep) -> Token:
    hashed_pw = hash_password(payload.password)
    user = User(email=payload.email, hashed_password=hashed_pw, full_name=payload.full_name)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    await session.refresh(user)
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return Token(access_token=access, refresh_token=refresh, role=user.role)


@router.post("/signin", response_model=Token)
async def signin(payload: LoginRequest, session: deps.SessionDep) -> Token:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return Token(access_token=access, refresh_token=refresh, role=user.role)


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, session: deps.SessionDep) -> Token:
    from app.core.security import decode_token  # local import avoids cycle
    import uuid

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh" or payload.get("sub") is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    subject = payload["sub"]
    
    # Fetch user to get their role
    user_id = uuid.UUID(subject)
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    
    access = create_access_token(subject)
    new_refresh = create_refresh_token(subject)
    return Token(access_token=access, refresh_token=new_refresh, role=user.role)


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(deps.get_current_user)) -> UserPublic:
    return UserPublic.from_orm(current_user)


@router.put("/me", response_model=UserPublic)
async def update_profile(
    payload: UserProfileUpdateRequest,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> UserPublic:
    """Update current user profile."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    
    await session.commit()
    await session.refresh(current_user)
    return UserPublic.from_orm(current_user)


@router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
async def signout(
    current_user: User = Depends(deps.get_current_user),
    response: Response = None,
) -> Response:
    """
    Sign out user.
    Note: Since we use stateless JWT tokens, the client should delete the token.
    This endpoint is provided for consistency with the API requirements.
    """
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/google/init", response_model=GoogleAuthInitResponse)
async def google_init(payload: GoogleAuthInitRequest) -> GoogleAuthInitResponse:
    settings = get_settings()
    if not settings.google_oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured.",
        )

    redirect_uri = str(payload.redirect_uri)
    allowed_redirects = settings.google_allowed_redirects
    if allowed_redirects and redirect_uri not in allowed_redirects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri is not allowed.",
        )

    try:
        client = GoogleOAuthClient()
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured.",
        ) from exc

    state_token = create_state_token({"redirect_uri": redirect_uri})
    auth_url = client.build_authorization_url(
        redirect_uri=redirect_uri,
        state=state_token,
        scopes=payload.scopes,
        prompt=payload.prompt,
    )
    response = GoogleAuthInitResponse(auth_url=auth_url, state=state_token)
    return response.dict()


@router.post("/google/complete", response_model=Token)
async def google_complete(
    payload: GoogleAuthCompleteRequest,
    session: deps.SessionDep,
) -> Token:
    settings = get_settings()
    if not settings.google_oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured.",
        )

    try:
        state_payload = verify_state_token(payload.state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter."
        ) from exc

    redirect_uri = state_payload.get("redirect_uri")
    if not redirect_uri or not isinstance(redirect_uri, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state payload."
        )

    allowed_redirects = settings.google_allowed_redirects
    if allowed_redirects and redirect_uri not in allowed_redirects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri is not allowed.",
        )

    try:
        client = GoogleOAuthClient()
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured.",
        ) from exc

    try:
        user_info = await client.exchange_code(code=payload.code, redirect_uri=redirect_uri)
    except GoogleOAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if not user_info.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account must provide an email address.",
        )
    if not user_info.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email must be verified.",
        )

    user = await _get_or_create_google_user(session, user_info)
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return Token(access_token=access, refresh_token=refresh, role=user.role)


@router.post("/password/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    payload: PasswordResetRequest, session: deps.SessionDep
) -> dict[str, str]:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user:
        reset, code = await password_reset_service.issue_password_reset(session, user)
        dispatcher = get_email_dispatcher()
        try:
            await dispatcher.send_password_reset_code(user.email, code)
        except EmailRateLimitError:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many reset requests. Try again later.",
            ) from None
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "Failed to send password reset email", extra={"email": user.email}
            )
    return {
        "message": "If an account exists for that email, a reset code has been sent.",
    }


@router.post("/password/verify", response_model=PasswordResetVerifyResponse)
async def verify_password_reset_code(
    payload: PasswordResetVerifyRequest, session: deps.SessionDep
) -> PasswordResetVerifyResponse:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code"
        )

    try:
        reset = await password_reset_service.verify_reset_code(session, user, payload.code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code"
        ) from exc

    token = password_reset_service.build_reset_token(reset)
    return PasswordResetVerifyResponse(reset_token=token)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
async def complete_password_reset(
    payload: PasswordResetCompleteRequest, session: deps.SessionDep
) -> Response:
    try:
        user, reset = await password_reset_service.consume_reset_token(
            session, payload.reset_token
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        ) from exc

    await password_reset_service.finalize_password_reset(
        session, user, reset, payload.new_password
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _get_or_create_google_user(session: AsyncSession, user_info: GoogleUserInfo) -> User:
    account_stmt = select(UserOAuthAccount).where(
        UserOAuthAccount.provider == "google", UserOAuthAccount.subject == user_info.sub
    )
    account_result = await session.execute(account_stmt)
    account = account_result.scalar_one_or_none()
    if account:
        user_result = await session.execute(select(User).where(User.id == account.user_id))
        return user_result.scalar_one()

    user_stmt = select(User).where(User.email == user_info.email)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if user is None:
        random_secret = secrets.token_urlsafe(32)
        user = User(
            email=user_info.email,
            hashed_password=hash_password(random_secret),
            full_name=user_info.name,
            is_active=True,
            is_verified=user_info.email_verified,
        )
        session.add(user)
        await session.flush()
    else:
        if user_info.name and not user.full_name:
            user.full_name = user_info.name
        if user_info.email_verified and not user.is_verified:
            user.is_verified = True

    oauth_account = UserOAuthAccount(
        user_id=user.id,
        provider="google",
        subject=user_info.sub,
        email=user_info.email,
        email_verified=user_info.email_verified,
        profile=user_info.dict(),
    )
    session.add(oauth_account)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing_account = await session.execute(account_stmt)
        account = existing_account.scalar_one_or_none()
        if account:
            user_result = await session.execute(select(User).where(User.id == account.user_id))
            return user_result.scalar_one()
        raise

    await session.refresh(user)
    return user
