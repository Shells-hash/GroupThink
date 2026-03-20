import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from backend.dependencies import get_db, get_current_user
from backend.models.user import User
from backend.models.password_reset import PasswordResetToken
from backend.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut
from backend.services import auth_service
from backend.services.email_service import send_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if auth_service.get_user_by_username(db, body.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = auth_service.register_user(db, body.username, body.email, body.password)
    token = auth_service.create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth_service.create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == body.email).first()
    # Always return 200 — never reveal whether an email exists
    if not user:
        return {"detail": "If that email is registered, a reset link has been sent."}

    # Invalidate any existing unused tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False,  # noqa: E712
    ).delete()

    token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    reset = PasswordResetToken(user_id=user.id, token=token, expires_at=expires, used=False)
    db.add(reset)
    db.commit()

    background_tasks.add_task(send_reset_email, user.email, user.username, token)
    return {"detail": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == body.token,
        PasswordResetToken.used == False,  # noqa: E712
    ).first()

    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    # Make expires_at timezone-aware for comparison
    expires = reset.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if now > expires:
        raise HTTPException(status_code=400, detail="Reset link has expired")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = db.query(User).filter(User.id == reset.user_id).first()
    user.hashed_password = auth_service.hash_password(body.new_password)
    reset.used = True
    db.commit()

    return {"detail": "Password reset successfully"}
