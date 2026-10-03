from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.rbac import permissions_for
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_refresh_token, verify_password
from app.db.session import get_db
from app.models import RefreshSession, User, Workspace
from app.schemas import AuthResponse, LoginRequest, MessageResponse, PermissionResponse, RegisterRequest, UserResponse
from app.services.audit import write_audit
from app.services.workspaces import get_or_create_default_workspace

settings = get_settings()
router = APIRouter()
DUMMY_PASSWORD_HASH = hash_password("timing-protection-dummy-password")


def set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="curamind_refresh",
        value=token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key="curamind_refresh",
        path="/api/v1/auth",
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
    )


def issue_session(db: Session, response: Response, user: User) -> AuthResponse:
    refresh_token = create_refresh_token()
    db.add(RefreshSession(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
    ))
    access_token = create_access_token(user.id, user.workspace_id, user.role)
    set_refresh_cookie(response, refresh_token)
    return AuthResponse(
        access_token=access_token,
        expires_in=settings.access_token_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if not settings.allow_public_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account registration is currently closed")

    workspace = get_or_create_default_workspace(db)
    normalized_email = str(payload.email).strip().lower()
    user = User(
        workspace_id=workspace.id,
        email=normalized_email,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        role="viewer",
    )
    db.add(user)
    try:
        db.flush()
        write_audit(db, "account.registered", user, target_user_id=user.id)
        auth_response = issue_session(db, response, user)
        db.commit()
        return auth_response
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    normalized_email = str(payload.email).strip().lower()
    workspace = db.query(Workspace).filter(Workspace.name == settings.default_workspace_name).first()
    user = None
    if workspace:
        user = db.query(User).filter(User.workspace_id == workspace.id, User.email == normalized_email).first()
    stored_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_matches = verify_password(payload.password, stored_hash)
    if user is None or not user.is_active or not password_matches:
        write_audit(db, "auth.login_failed", detail="Invalid credentials")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect")

    write_audit(db, "auth.login_succeeded", user)
    auth_response = issue_session(db, response, user)
    db.commit()
    return auth_response


@router.post("/auth/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get("curamind_refresh")
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is missing")

    session = db.query(RefreshSession).filter(RefreshSession.token_hash == hash_refresh_token(raw_token)).first()
    now = datetime.now(timezone.utc)
    if session is None or session.revoked_at is not None or session.expires_at.replace(tzinfo=session.expires_at.tzinfo or timezone.utc) <= now:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is invalid or expired")

    user = db.query(User).filter(User.id == session.user_id).first()
    if user is None or not user.is_active:
        session.revoked_at = now
        db.commit()
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is unavailable")

    session.revoked_at = now
    auth_response = issue_session(db, response, user)
    write_audit(db, "auth.session_refreshed", user)
    db.commit()
    return auth_response


@router.post("/auth/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get("curamind_refresh")
    if raw_token:
        session = db.query(RefreshSession).filter(RefreshSession.token_hash == hash_refresh_token(raw_token)).first()
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            user = db.query(User).filter(User.id == session.user_id).first()
            write_audit(db, "auth.logout", user)
            db.commit()
    clear_refresh_cookie(response)
    return MessageResponse(message="Signed out")


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.get("/auth/permissions", response_model=PermissionResponse)
def my_permissions(user: User = Depends(get_current_user)):
    return PermissionResponse(role=user.role, permissions=permissions_for(user.role))