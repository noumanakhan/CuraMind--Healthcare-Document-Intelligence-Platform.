import argparse
import getpass
import sys
from pathlib import Path

# Ensure backend root is in sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.rbac import ROLE_PERMISSIONS
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import User, Workspace


def create_user(email: str, name: str, role: str):
    if role not in ROLE_PERMISSIONS:
        raise SystemExit("Role must be one of: admin, clinician, records, viewer")
    password = getpass.getpass("Set password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        settings = get_settings()
        workspace = db.query(Workspace).filter(Workspace.name == settings.default_workspace_name).first()
        if workspace is None:
            workspace = Workspace(name=settings.default_workspace_name)
            db.add(workspace)
            db.flush()
        user = User(
            workspace_id=workspace.id,
            email=email.strip().lower(),
            name=name.strip(),
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print("Created {} account for {}".format(role, email))
    except IntegrityError:
        db.rollback()
        raise SystemExit("An account with that email already exists in the workspace")
    finally:
        db.close()


from app.db.seed_demo_data import seed_demo_clinical_data


def seed_demo():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_clinical_data(db)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="CuraMind local account administration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create-user", help="Create a workspace account (use this to bootstrap the first admin)")
    create_parser.add_argument("--email", required=True)
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--role", choices=sorted(ROLE_PERMISSIONS), default="admin")

    subparsers.add_parser("seed-demo", help="Seed complete mock clinical dataset (patients, vault docs, appointments, vitals, labs, discharge drafts)")

    args = parser.parse_args()
    if args.command == "create-user":
        create_user(args.email, args.name, args.role)
    elif args.command == "seed-demo":
        seed_demo()


if __name__ == "__main__":
    main()
