from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.database.engine import SessionLocal
from backend.services import auth_service
from backend.models.user import User
from backend.utils.exceptions import UnauthorizedError

bearer_scheme = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = auth_service.decode_token(credentials.credentials)
    if not user_id:
        raise UnauthorizedError("Invalid or expired token")
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise UnauthorizedError("User not found")
    return user
