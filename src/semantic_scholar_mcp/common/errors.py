"""Stable application-level errors for Semantic Scholar requests."""

from __future__ import annotations

from typing import Any


class SemanticScholarError(Exception):
    """Base exception for errors exposed by the Semantic Scholar client."""

    code = "semantic_scholar_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        attempts: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.attempts = attempts
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.status_code is not None:
            result["status_code"] = self.status_code
        if self.attempts is not None:
            result["attempts"] = self.attempts
        if self.details:
            result["details"] = self.details
        return result

    def __str__(self) -> str:
        status = f" HTTP {self.status_code}" if self.status_code is not None else ""
        return f"{self.code}{status}: {self.message}"


class AuthenticationRequiredError(SemanticScholarError):
    code = "authentication_required"


class AuthenticationError(SemanticScholarError):
    code = "authentication_failed"


class InvalidRequestError(SemanticScholarError):
    code = "invalid_request"


class NotFoundError(SemanticScholarError):
    code = "not_found"


class RateLimitError(SemanticScholarError):
    code = "rate_limited"


class UpstreamServerError(SemanticScholarError):
    code = "upstream_error"


class TransportError(SemanticScholarError):
    code = "transport_error"


class InvalidResponseError(SemanticScholarError):
    code = "invalid_response"
