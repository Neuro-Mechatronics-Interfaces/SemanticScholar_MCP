from semantic_scholar_mcp.common.errors import (
    AuthenticationRequiredError,
    RateLimitError,
)


def test_error_to_dict() -> None:
    error = RateLimitError(
        "Too many requests",
        status_code=429,
        retryable=True,
        attempts=3,
    )

    assert error.to_dict() == {
        "code": "rate_limited",
        "message": "Too many requests",
        "retryable": True,
        "status_code": 429,
        "attempts": 3,
    }


def test_error_string() -> None:
    error = RateLimitError(
        "Too many requests",
        status_code=429,
    )

    assert str(error) == "rate_limited HTTP 429: Too many requests"


def test_authentication_required_error_code() -> None:
    error = AuthenticationRequiredError("API key required")

    assert error.code == "authentication_required"
    assert error.to_dict()["retryable"] is False
