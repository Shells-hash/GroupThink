import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.database.engine import init_db
from backend.dependencies import get_db
from backend.main import app
from backend.services.auth_service import create_access_token, register_user

TEST_DB_URL = "sqlite:///./test_groupthink.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    import backend.models  # noqa — register all models
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def user_and_token(db):
    user = register_user(db, "testuser", "test@example.com", "password123")
    token = create_access_token(user.id)
    return user, token


@pytest.fixture
def auth_headers(user_and_token):
    _, token = user_and_token
    return {"Authorization": f"Bearer {token}"}
