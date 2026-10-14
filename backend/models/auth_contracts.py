"""Strict public authentication contracts; never serialize persisted secrets."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["engineer", "reviewer", "admin"]


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or value.count("@") != 1 or any(c.isspace() for c in value):
        raise ValueError("Invalid email")
    local, domain = value.split("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("Invalid email")
    return value


def validate_roles(value: list[str]) -> list[str]:
    if not value or len(value) != len(set(value)) or not set(value) <= {"engineer", "reviewer", "admin"}:
        raise ValueError("Invalid roles")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(StrictModel):
    email: str
    password: str = Field(min_length=1, max_length=128)
    _email = field_validator("email")(normalize_email)


class ChangePassword(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class CreateUser(StrictModel):
    email: str
    display_name: str = Field(min_length=1, max_length=255)
    roles: list[Role]
    temporary_password: str = Field(min_length=6, max_length=128)
    _email = field_validator("email")(normalize_email)
    _roles = field_validator("roles")(validate_roles)


class UpdateUser(StrictModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    roles: list[Role] | None = None
    is_active: bool | None = None

    @field_validator("roles", "display_name", "is_active")
    @classmethod
    def non_null(cls, value, info):
        if value is None:
            raise ValueError("Explicit null is not allowed")
        return validate_roles(value) if info.field_name == "roles" else value


class ResetPassword(StrictModel):
    temporary_password: str = Field(min_length=6, max_length=128)


class PublicUser(StrictModel):
    id: UUID
    email: str
    display_name: str
    roles: list[Role]
    is_active: bool
    must_change_password: bool


def public_user(user) -> dict:
    return PublicUser(**{key: getattr(user, key) for key in PublicUser.model_fields}).model_dump(mode="json")
