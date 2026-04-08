from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..models.admin_user import AdminUser
from ..services.auth_service import AuthService


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_node_service(request: Request):
    return request.app.state.node_service


def get_enrollment_service(request: Request):
    return request.app.state.enrollment_service


def get_spot_service(request: Request):
    return request.app.state.spot_service


def get_event_service(request: Request):
    return request.app.state.event_service


def get_playback_service(request: Request):
    return request.app.state.playback_service


def get_scheduler_service(request: Request):
    return request.app.state.scheduler_service


def get_connection_manager(request: Request):
    return request.app.state.connection_manager


def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> AdminUser:
    current_admin = auth_service.get_current_admin(db, request)
    if current_admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_admin


def require_current_admin_write(
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    auth_service: AuthService = Depends(get_auth_service),
) -> AdminUser:
    if not auth_service.request_uses_bearer_token(request):
        auth_service.validate_csrf(request, current_admin.username)
    return current_admin
