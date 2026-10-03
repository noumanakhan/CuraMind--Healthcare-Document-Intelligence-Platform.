from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    name: str
    email: EmailStr
    role: Literal["admin", "clinician", "records", "viewer"]
    is_active: bool
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "clinician", "records", "viewer"]


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserListResponse(BaseModel):
    users: List[UserResponse]