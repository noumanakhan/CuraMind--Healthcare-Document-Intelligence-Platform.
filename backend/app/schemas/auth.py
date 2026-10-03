from typing import List, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints
from typing_extensions import Annotated

from app.schemas.users import UserResponse

RoleName = Literal["admin", "clinician", "records", "viewer"]
StrongPassword = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: StrongPassword


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


class PermissionResponse(BaseModel):
    role: RoleName
    permissions: List[str]