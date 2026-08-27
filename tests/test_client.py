from unittest.mock import AsyncMock

import httpx
import pytest

import semantic_scholar_mcp.common.client as client_module
from semantic_scholar_mcp.common.client import SemanticScholarClient
from semantic_scholar_mcp.common.errors import (
    AuthenticationError,
    AuthenticationRequiredError,
    InvalidResponseError,
    NotFoundError,
    RateLimitError,
)
from semantic_scholar_mcp.common.models import RetryPolicy


@pytest.mark.asyncio
async def test_unauthenticated_request_does_not_send_api_key(
    monkeypatch,
    respx_mock,
    no_rate_limiter,
) -> None:
    monkeypatch.delenv(
        "SEMANTIC_SCHOLAR_API_KEY",
        raising=False,
    )

    route = respx_mock.get(
        "https://api.semanticscholar.org/graph/v1/paper/test"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "paperId": "test",
                "title": "Test Paper",
            },
        )
    )

    client = SemanticScholarClient(
        rate_limiter=no_rate_limiter,
        retry_policy=RetryPolicy(max_retries=0),
    )

    try:
        result = await client.request(
            "GET",
            "/graph/v1/paper/test",
        )
    finally:
        await client.aclose()

    assert result["paperId"] == "test"

    request = route.calls.last.request

    assert "x-api-key" not in request.headers


@pytest.mark.asyncio
async def test_authenticated_request_sends_api_key(
    respx_mock,
    no_rate_limiter,
) -> None:
    route = respx_mock.get(
        "https://api.semanticscholar.org/graph/v1/paper/test"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"paperId": "test"},
        )
    )

    client = SemanticScholarClient(
        api_key="test-key",
        rate_limiter=no_rate_limiter,
        retry_policy=RetryPolicy(max_retries=0),
    )

    try:
        await client.request(
            "GET",
            "/graph/v1/paper/test",
        )
    finally:
        await client.aclose()

    assert route.calls.last.request.headers["x-api-key"] == "test-key"


@pytest.mark.asyncio
async def test_required_api_key_fails_before_http_request(
    monkeypatch,
    no_rate_limiter,
) -> None:
    monkeypatch.delenv(
        "SEMANTIC_SCHOLAR_API_KEY",
        raising=False,
    )

    client = SemanticScholarClient(
        rate_limiter=no_rate_limiter,
    )

    with pytest.raises(AuthenticationRequiredError):
        await client.request(
            "GET",
            "/datasets/v1/release/latest/dataset/papers",
            require_api_key=True,
        )

    assert no_rate_limiter.calls == 0


@pytest.mark.asyncio
async def test_not_found_is_translated(
    respx_mock,
    no_rate_limiter,
) -> None:
    route = respx_mock.get(
        "https://api.semanticscholar.org/graph/v1/paper/missing"
    ).mock(
        return_value=httpx.Response(
            404,
            json={"message": "Paper not found"},
        )
    )

    client = SemanticScholarClient(
        rate_limiter=no_rate_limiter,
        retry_policy=RetryPolicy(max_retries=0),
    )

    try:
        with pytest.raises(NotFoundError) as exc:
            await client.request(
                "GET",
                "/graph/v1/paper/missing",
            )
    finally:
        await client.aclose()

    assert exc.value.status_code == 404
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_authentication_error_is_not_retried(
    monkeypatch,
    respx_mock,
    no_rate_limiter,
) -> None:
    route = respx_mock.get(
        "https://api.semanticscholar.org/graph/v1/paper/test"
    ).mock(
        return_value=httpx.Response(
            401,
            json={"message": "Invalid API key"},
        )
    )

    fake_sleep = AsyncMock()
    monkeypatch.setattr(
        client_module.asyncio,
        "sleep",
        fake_sleep,
    )

    client = SemanticScholarClient(
        api_key="bad-key",
        rate_limiter=no_rate_limiter,
        retry_policy=RetryPolicy(
            max_retries=5,
            jitter_seconds=0,
        ),
    )

    try:
        with pytest.raises(AuthenticationError):
            await client.request(
                "GET",
                "/graph/v1/paper/test",
            )
    finally:
        await client.aclose()

    assert route.call_count == 1
    fake_sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_429_honors_retry_after_and_retries(
    monkeypatch,
    respx_mock,
    no_rate_limiter,
) -> None:
    route = respx_mock.get(
        "https://api.semanticscholar.org/graph/v1/paper/test"
    ).mock(
        side_effect=[
            httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"message": "Too Many Requests"},
            ),
            httpx.Response(
                200,
                json={"paperId": "test"},
            ),
        ]
    )

    fake_sleep = AsyncMock()
    monkeypatch.setattr(
        client_module.asyncio,
        "sleep",
        fake_sleep,
    )

    client = SemanticScholarClient(
        rate_limiter=no_rate_limiter,
        retry_policy=RetryPolicy(
            max_retries=1,
            jitter_seconds=0,
        ),
    )

    try:
        result = await client.request(
            "GET",
            "/graph/v1/paper/test",
        )
    finally:
        await client.aclose()

    assert result == {"paperId": "test"}
    assert route.call_count == 2
    assert no_rate_limiter.calls == 2
    fake_sleep.assert_awaited_once_with(0.0)


@pytest.mark.asyncio
async def test_429_becomes_error_after_retries_exhausted(
    monkeypatch,
    respx_mock,
    no_rate_limiter,
) -> None:
    route = respx_mock.get(
        "https://api.semanticscholar.org/graph/v1/paper/test"
    ).mock(
        return_value=httpx.Response(
            429,
            headers={"Retry-After": "0"},
            json={"message": "Too Many Requests"},
        )
    )

    fake_sleep = AsyncMock()
    monkeypatch.setattr(
        client_module.asyncio,
        "sleep",
        fake_sleep,
    )

    client = SemanticScholarClient(
        rate_limiter=no_rate_limiter,
        retry_policy=RetryPolicy(
            max_retries=1,
            jitter_seconds=0,
        ),
    )

    try:
        with pytest.raises(RateLimitError) as exc:
            await client.request(
                "GET",
                "/graph/v1/paper/test",
            )
    finally:
        await client.aclose()

    assert route.call_count == 2
    assert exc.value.attempts == 2
    assert exc.value.retryable is True


@pytest.mark.asyncio
async def test_non_json_success_is_rejected(
    respx_mock,
    no_rate_limiter,
) -> None:
    respx_mock.get(
        "https://api.semanticscholar.org/graph/v1/paper/test"
    ).mock(
        return_value=httpx.Response(
            200,
            text="not-json",
        )
    )

    client = SemanticScholarClient(
        rate_limiter=no_rate_limiter,
        retry_policy=RetryPolicy(max_retries=0),
    )

    try:
        with pytest.raises(InvalidResponseError):
            await client.request(
                "GET",
                "/graph/v1/paper/test",
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_arbitrary_external_url_is_rejected(
    no_rate_limiter,
) -> None:
    client = SemanticScholarClient(
        rate_limiter=no_rate_limiter,
    )

    with pytest.raises(ValueError):
        await client.request(
            "GET",
            "https://example.com/evil",
        )