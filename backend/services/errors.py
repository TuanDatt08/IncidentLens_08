from __future__ import annotations

from typing import Any


class IncidentIngestionError(Exception):
    """Expected error that can be returned as a structured API 4xx/5xx error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        status_code: int = 422,
        package_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.status_code = status_code
        self.package_id = package_id

    def with_package_id(self, package_id: str) -> IncidentIngestionError:
        self.package_id = package_id
        return self

    def detail(self) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.field:
            detail["field"] = self.field
        if self.package_id:
            detail["package_id"] = self.package_id
        return detail
