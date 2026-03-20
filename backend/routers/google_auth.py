import secrets
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from backend.dependencies import get_db
from backend.models.user import User
from backend.services.auth_service import create_access_token, hash_password
from backend.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["google-auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google")
async def google_login(request: Request):
    if not settings.google_client_id or not settings.google_client_secret:
        return RedirectResponse(url="/#/login?error=Google+sign-in+is+not+configured+on+this+server")
    # Build redirect_uri — strip trailing slash to avoid double-slash
    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse(url="/#/login?error=Google+sign-in+failed")

    user_info = token.get("userinfo")
    if not user_info:
        return RedirectResponse(url="/#/login?error=Could+not+get+user+info")

    google_id = user_info.get("sub")
    email = user_info.get("email", "")
    name = user_info.get("given_name") or user_info.get("name", "").split()[0] or "user"

    # Find existing user by google_id or email
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()

    if user:
        # Link google_id if not already set
        if not user.google_id:
            user.google_id = google_id
            db.commit()
    else:
        # Create new user — generate a unique username from their name
        base_username = name.lower().replace(" ", "")[:20]
        username = base_username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(secrets.token_hex(32)),  # unguessable, login via Google only
            google_id=google_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token(user.id)
    return RedirectResponse(url=f"/#/oauth-callback?token={jwt_token}")
