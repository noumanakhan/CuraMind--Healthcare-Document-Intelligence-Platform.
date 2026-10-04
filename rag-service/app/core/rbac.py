from typing import Dict, FrozenSet, List, Optional
from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    id: str
    workspace_id: str
    role: str
    email: Optional[str] = None


ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "admin": frozenset({
        "patients:view", "patients:create", "patients:edit", "patients:archive",
        "documents:view", "documents:create", "documents:edit", "documents:archive",
        "clinical:review", "clinical:chart_view", "fields:confirm", "discharge:sign",
        "medications:review", "vitals:record", "immunizations:record", "labs:record",
        "appointments:manage", "appointments:view", "settings:manage", "users:manage",
        "audit:view", "rag:chat", "documents:compare",
    }),
    "clinician": frozenset({
        "patients:view", "documents:view", "documents:create",
        "clinical:review", "clinical:chart_view", "fields:confirm", "discharge:sign",
        "medications:review", "vitals:record", "immunizations:record", "labs:record",
        "appointments:view", "rag:chat", "documents:compare",
    }),
    "records": frozenset({
        "patients:view", "patients:create", "patients:edit", "documents:view",
        "documents:create", "documents:edit", "appointments:manage", "appointments:view",
        "documents:compare",
    }),
    "viewer": frozenset({
        "patients:view", "documents:view", "appointments:view", "rag:chat",
    }),
}


ALL_DOC_TYPES = ["lab_report", "clinical_note", "intake_form", "discharge_summary"]
NON_CLINICAL_DOC_TYPES = ["intake_form", "demographics_form"]


def user_has_permission(role: str, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, frozenset())
    return permission in perms


def get_allowed_document_types(role: str, is_patient_scoped: bool = True) -> Optional[List[str]]:
    """
    Returns the list of document types a user with `role` is permitted to search.
    If None, all document types are allowed.
    - Clinicians and Admins have full access across all types.
    - When searching workspace-wide without a patient scope, viewers and records staff cannot
      retrieve sensitive 'clinical_note' or 'discharge_summary' chunks.
    """
    if role in ("admin", "clinician"):
        return None  # All types allowed

    if role == "records":
        if is_patient_scoped:
            return ["intake_form", "lab_report", "discharge_summary"]
        return ["intake_form"]

    if role == "viewer":
        if is_patient_scoped:
            return ["intake_form", "lab_report"]
        return ["intake_form"]

    return []
