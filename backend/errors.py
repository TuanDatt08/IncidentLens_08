"""Errors shared by the backend services and the local API layer."""

from typing import Any


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
