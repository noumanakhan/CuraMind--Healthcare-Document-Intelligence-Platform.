from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from app.api.v1.router import router
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import User, Workspace
from app.schemas import HealthResponse

settings = get_settings()

HARDCODED_ADMIN_EMAIL = "admin@gmail.com"
HARDCODED_ADMIN_PASSWORD = "allahmuhammad"
HARDCODED_ADMIN_NAME = "Admin"


def ensure_hardcoded_admin(db):
    workspace = db.query(Workspace).filter(Workspace.name == settings.default_workspace_name).first()
    if workspace is None:
        workspace = Workspace(name=settings.default_workspace_name)
        db.add(workspace)
        try:
            db.commit()
            db.refresh(workspace)
        except IntegrityError:
            db.rollback()
            workspace = db.query(Workspace).filter(Workspace.name == settings.default_workspace_name).first()

    if not workspace:
        return

    admin_user = db.query(User).filter(
        User.workspace_id == workspace.id,
        User.email == HARDCODED_ADMIN_EMAIL,
    ).first()

    if admin_user is None:
        admin_user = User(
            workspace_id=workspace.id,
            email=HARDCODED_ADMIN_EMAIL,
            name=HARDCODED_ADMIN_NAME,
            password_hash=hash_password(HARDCODED_ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    else:
        admin_user.role = "admin"
        admin_user.password_hash = hash_password(HARDCODED_ADMIN_PASSWORD)
        admin_user.is_active = True
        try:
            db.commit()
        except Exception:
            db.rollback()


from app.db.seed_demo_data import seed_demo_clinical_data


@asynccontextmanager
async def lifespan(application: FastAPI):
    # create_all is intended for local development only. Use versioned migrations in production.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_hardcoded_admin(db)
        seed_demo_clinical_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="CuraMind authentication and role-based access API",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.include_router(router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    return HealthResponse(status="ok", app=settings.app_name)
