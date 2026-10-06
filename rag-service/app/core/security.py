import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import settings
from app.core.rbac import AuthenticatedUser, user_has_permission

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security_scheme)) -> AuthenticatedUser:
    if not credentials or not credentials.credentials:
        # Fallback for testing or development if no token passed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token"
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub") or payload.get("user_id")
        workspace_id = payload.get("workspace_id")
        role = payload.get("role", "viewer")
        email = payload.get("email")

        if not user_id or not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: missing subject or workspace"
            )

        return AuthenticatedUser(
            id=str(user_id),
            workspace_id=str(workspace_id),
            role=str(role),
            email=email,
            raw_token=token,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )


def require_permission(permission: str):
    def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not user_has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires '{permission}'"
            )
        return user
    return dependency
