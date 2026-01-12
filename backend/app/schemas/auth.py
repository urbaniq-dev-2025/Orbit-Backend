from __future__ import annotations

from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, root_validator, constr


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(LoginRequest):
    full_name: Optional[str] = None


class GoogleAuthInitRequest(BaseModel):
    redirect_uri: AnyHttpUrl = Field(..., alias="redirectUri")
    scopes: Optional[List[str]] = None
    prompt: Optional[str] = None

    class Config:
        allow_population_by_field_name = True

    @root_validator(pre=True)
    def _coerce_redirect_alias(cls, values: dict[str, object]) -> dict[str, object]:
        if not isinstance(values, dict):
            return values
        redirect_value = values.get("redirect_uri") or values.get("redirectUri")
        if redirect_value:
            values["redirect_uri"] = redirect_value
        return values


class GoogleAuthInitResponse(BaseModel):
    auth_url: AnyHttpUrl
    authUrl: AnyHttpUrl = Field(..., alias="authUrl")
    state: str

    class Config:
        allow_population_by_field_name = True

    @root_validator(pre=True)
    def _sync_auth_urls(cls, values: dict[str, object]) -> dict[str, object]:
        if not isinstance(values, dict):
            return values
        url = values.get("auth_url") or values.get("authUrl")
        if url is None:
            return values
        values["auth_url"] = url
        values["authUrl"] = url
        return values


class GoogleAuthCompleteRequest(BaseModel):
    code: str
    state: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetVerifyRequest(BaseModel):
    email: EmailStr
    code: constr(regex=r"^\d{6}$")  # type: ignore[valid-type]


class PasswordResetVerifyResponse(BaseModel):
    reset_token: str = Field(..., alias="resetToken")

    class Config:
        allow_population_by_field_name = True


class PasswordResetCompleteRequest(BaseModel):
    reset_token: str = Field(..., alias="resetToken")
    new_password: str = Field(..., alias="newPassword", min_length=8)

    class Config:
        allow_population_by_field_name = True


