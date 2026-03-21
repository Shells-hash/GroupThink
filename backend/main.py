from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
import os

from backend.config import get_settings
from backend.database.engine import init_db
from backend.routers import auth, groups, threads, messages, plans, websocket, plan_chat, documents, uploads
from backend.routers import google_auth

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="GroupThink API",
    description="AI-powered collaborative planning for friend groups",
    version="0.1.0",
    lifespan=lifespan,
)

# SessionMiddleware required for Google OAuth state handling
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(auth.router)
app.include_router(google_auth.router)
app.include_router(groups.router)
app.include_router(threads.router)
app.include_router(messages.router)
app.include_router(plans.router)
app.include_router(websocket.router)
app.include_router(plan_chat.router)
app.include_router(documents.router)
app.include_router(uploads.router)

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")

    uploads_path = os.path.join(os.path.dirname(__file__), "..", "uploads")
    os.makedirs(uploads_path, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))
