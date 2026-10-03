from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Workspace

settings = get_settings()


def get_or_create_default_workspace(db: Session) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.name == settings.default_workspace_name).first()
    if workspace:
        return workspace
    workspace = Workspace(name=settings.default_workspace_name)
    db.add(workspace)
    db.flush()
    return workspace