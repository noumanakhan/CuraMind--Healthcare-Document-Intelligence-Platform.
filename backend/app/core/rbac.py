from typing import Dict, FrozenSet

ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "admin": frozenset({
        "patients:view", "patients:create", "patients:edit", "patients:archive",
        "documents:view", "documents:create", "documents:edit", "documents:archive",
        "clinical:review", "clinical:chart_view", "fields:confirm", "discharge:sign",
        "medications:review", "vitals:record", "immunizations:record", "labs:record",
        "appointments:manage", "appointments:view", "settings:manage", "users:manage",
        "audit:view",
    }),
    "clinician": frozenset({
        "patients:view", "documents:view", "documents:create",
        "clinical:review", "clinical:chart_view", "fields:confirm", "discharge:sign",
        "medications:review", "vitals:record", "immunizations:record", "labs:record",
        "appointments:view",
    }),
    "records": frozenset({
        "patients:view", "patients:create", "patients:edit", "documents:view",
        "documents:create", "documents:edit", "appointments:manage", "appointments:view",
    }),
    "viewer": frozenset({
        "patients:view", "documents:view", "appointments:view",
    }),
}


ROLE_LABELS = {
    "admin": "Workspace admin",
    "clinician": "Clinician",
    "records": "Records staff",
    "viewer": "Read-only",
}


def permissions_for(role: str):
    return sorted(ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["viewer"]))