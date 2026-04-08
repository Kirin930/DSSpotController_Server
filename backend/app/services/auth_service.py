from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.security import (
    build_csrf_token,
    build_session_token,
    hash_secret,
    parse_session_token,
    verify_csrf_token,
    verify_secret,
)
from ..models.admin_user import AdminUser
from ..utils.time import utc_now
from .event_service import EventService


class LoginRateLimiter:
    def __init__(
        self,
        *,
        max_attempts: int,
        window_seconds: int,
        lockout_seconds: int,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._attempts_by_ip: dict[str, deque[float]] = defaultdict(deque)
        self._attempts_by_username: dict[str, deque[float]] = defaultdict(deque)
        self._ip_lockouts: dict[str, float] = {}
        self._username_lockouts: dict[str, float] = {}

    def _prune(self, bucket: deque[float], now: float) -> None:
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()

    def ensure_allowed(self, ip: str, username: str) -> None:
        now = time.time()
        if self._ip_lockouts.get(ip, 0) > now or self._username_lockouts.get(
            username, 0
        ) > now:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts, please try again later",
            )

    def register_failure(self, ip: str, username: str) -> None:
        now = time.time()
        ip_bucket = self._attempts_by_ip[ip]
        username_bucket = self._attempts_by_username[username]
        self._prune(ip_bucket, now)
        self._prune(username_bucket, now)
        ip_bucket.append(now)
        username_bucket.append(now)
        if len(ip_bucket) >= self.max_attempts:
            self._ip_lockouts[ip] = now + self.lockout_seconds
            ip_bucket.clear()
        if len(username_bucket) >= self.max_attempts:
            self._username_lockouts[username] = now + self.lockout_seconds
            username_bucket.clear()

    def register_success(self, ip: str, username: str) -> None:
        self._attempts_by_ip.pop(ip, None)
        self._attempts_by_username.pop(username, None)
        self._ip_lockouts.pop(ip, None)
        self._username_lockouts.pop(username, None)


class AuthService:
    def __init__(self, settings: Settings, event_service: EventService) -> None:
        self.settings = settings
        self.event_service = event_service
        self.rate_limiter = LoginRateLimiter(
            max_attempts=settings.login_max_attempts,
            window_seconds=settings.login_window_seconds,
            lockout_seconds=settings.login_lockout_seconds,
        )

    def ensure_default_admin(self, db: Session) -> AdminUser:
        admin_user = db.scalar(select(AdminUser).limit(1))
        if admin_user is not None:
            return admin_user

        admin_user = AdminUser(
            username=self.settings.default_admin_username,
            password_hash=hash_secret(self.settings.default_admin_password),
        )
        db.add(admin_user)
        self.event_service.log(
            db,
            "ADMIN_BOOTSTRAPPED",
            details=f"Bootstrapped default admin {admin_user.username}",
            actor_type="system",
            actor_id="bootstrap",
        )
        db.commit()
        db.refresh(admin_user)
        return admin_user

    def get_client_ip(self, request: Request) -> str:
        return request.client.host if request.client else "unknown"

    def authenticate(
        self, db: Session, username: str, password: str, *, client_ip: str
    ) -> tuple[AdminUser, str]:
        self.rate_limiter.ensure_allowed(client_ip, username)
        admin_user = db.scalar(
            select(AdminUser).where(AdminUser.username == username)
        )
        if (
            admin_user is None
            or not admin_user.is_active
            or not verify_secret(password, admin_user.password_hash)
        ):
            self.rate_limiter.register_failure(client_ip, username)
            self.event_service.log(
                db,
                "ADMIN_LOGIN_FAILURE",
                details=f"Failed login for username {username}",
                actor_type="admin",
                actor_id=username,
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        self.rate_limiter.register_success(client_ip, username)
        admin_user.last_login_at = utc_now()
        session_token = build_session_token(
            self.settings.secret_key,
            admin_user.username,
            self.settings.session_ttl_seconds,
        )
        self.event_service.log(
            db,
            "ADMIN_LOGIN_SUCCESS",
            details=f"Successful login for username {admin_user.username}",
            actor_type="admin",
            actor_id=admin_user.username,
        )
        db.commit()
        db.refresh(admin_user)
        return admin_user, session_token

    def set_session_cookie(self, response: Response, token: str) -> None:
        response.set_cookie(
            key=self.settings.session_cookie_name,
            value=token,
            httponly=True,
            samesite="lax",
            secure=self.settings.session_cookie_secure,
            max_age=self.settings.session_ttl_seconds,
        )

    def issue_csrf_token(self, response: Response, username: str) -> str:
        csrf_token = build_csrf_token(
            self.settings.secret_key,
            username,
            self.settings.csrf_ttl_seconds,
        )
        response.set_cookie(
            key=self.settings.csrf_cookie_name,
            value=csrf_token,
            httponly=False,
            samesite="lax",
            secure=self.settings.session_cookie_secure,
            max_age=self.settings.csrf_ttl_seconds,
        )
        return csrf_token

    def clear_session_cookie(self, response: Response) -> None:
        response.delete_cookie(self.settings.session_cookie_name)
        response.delete_cookie(self.settings.csrf_cookie_name)

    def validate_csrf(self, request: Request, username: str) -> None:
        cookie_token = request.cookies.get(self.settings.csrf_cookie_name)
        header_token = request.headers.get(self.settings.csrf_header_name)
        if not cookie_token or not header_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing CSRF token",
            )
        if not hmac.compare_digest(cookie_token, header_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token",
            )
        if not verify_csrf_token(self.settings.secret_key, cookie_token, username):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Expired or invalid CSRF token",
            )

    def get_current_admin(self, db: Session, request: Request) -> AdminUser | None:
        authorization = request.headers.get("Authorization", "")
        bearer_token = None
        if authorization.startswith("Bearer "):
            bearer_token = authorization.split(" ", maxsplit=1)[1].strip()

        token = bearer_token or request.cookies.get(self.settings.session_cookie_name)
        if not token:
            return None

        username = parse_session_token(self.settings.secret_key, token)
        if username is None:
            return None

        return db.scalar(select(AdminUser).where(AdminUser.username == username))

    def request_uses_bearer_token(self, request: Request) -> bool:
        authorization = request.headers.get("Authorization", "")
        return authorization.startswith("Bearer ")
