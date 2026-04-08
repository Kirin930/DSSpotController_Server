from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..deps import (
    get_auth_service,
    get_current_admin,
    get_db,
    require_current_admin_write,
)
from ...models.admin_user import AdminUser
from ...schemas.auth import (
    AdminUserResponse,
    AuthTokenResponse,
    CsrfTokenResponse,
    LoginRequest,
)
from ...services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    current_admin, session_token = auth_service.authenticate(
        db,
        payload.username,
        payload.password,
        client_ip=auth_service.get_client_ip(request),
    )
    auth_service.set_session_cookie(response, session_token)
    csrf_token = auth_service.issue_csrf_token(response, current_admin.username)
    return AuthTokenResponse(
        access_token=session_token,
        token_type="bearer",
        csrf_token=csrf_token,
    )


@router.get("/me", response_model=AdminUserResponse)
def me(current_admin: AdminUser = Depends(get_current_admin)) -> AdminUserResponse:
    return AdminUserResponse.model_validate(current_admin)


@router.get("/csrf", response_model=CsrfTokenResponse)
def csrf_token(
    response: Response,
    current_admin: AdminUser = Depends(get_current_admin),
    auth_service: AuthService = Depends(get_auth_service),
) -> CsrfTokenResponse:
    csrf_token = auth_service.issue_csrf_token(response, current_admin.username)
    return CsrfTokenResponse(csrf_token=csrf_token)


@router.post("/logout")
def logout(
    response: Response,
    _: AdminUser = Depends(require_current_admin_write),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    auth_service.clear_session_cookie(response)
    return {"message": "Logged out"}
