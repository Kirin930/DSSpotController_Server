from __future__ import annotations

from .common import ApiModel


class LoginRequest(ApiModel):
    username: str
    password: str


class AuthTokenResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    csrf_token: str


class CsrfTokenResponse(ApiModel):
    csrf_token: str


class AdminUserResponse(ApiModel):
    id: str
    username: str
