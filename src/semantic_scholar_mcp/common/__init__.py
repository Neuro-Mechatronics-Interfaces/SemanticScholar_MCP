"""Shared transport, validation, and error utilities."""

from .client import API_KEY_ENV, SemanticScholarClient
from .errors import (
    AuthenticationError,
    AuthenticationRequiredError,
    InvalidRequestError,
    InvalidResponseError,
    NotFoundError,
    RateLimitError,
    SemanticScholarError,
    TransportError,
    UpstreamServerError,
)
from .models import (
    JsonResponse,
    RetryPolicy,
    comma_separated,
    normalize_author_id,
    normalize_paper_id,
    require_nonempty,
    require_nonempty_list,
    validate_limit,
    validate_offset,
)
from .rate_limit import DEFAULT_MIN_INTERVAL_SECONDS, SharedRateLimiter

__all__ = [
    "API_KEY_ENV",
    "DEFAULT_MIN_INTERVAL_SECONDS",
    "AuthenticationError",
    "AuthenticationRequiredError",
    "InvalidRequestError",
    "InvalidResponseError",
    "JsonResponse",
    "NotFoundError",
    "RateLimitError",
    "RetryPolicy",
    "SemanticScholarClient",
    "SemanticScholarError",
    "SharedRateLimiter",
    "TransportError",
    "UpstreamServerError",
    "comma_separated",
    "normalize_author_id",
    "normalize_paper_id",
    "require_nonempty",
    "require_nonempty_list",
    "validate_limit",
    "validate_offset",
]
