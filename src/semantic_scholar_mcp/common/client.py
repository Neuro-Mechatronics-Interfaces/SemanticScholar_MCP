"""HTTP transport shared by the Semantic Scholar MCP servers."""

from __future__ import annotations

import asyncio
import os
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

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
from .models import JsonResponse, RetryPolicy
from .rate_limit import SharedRateLimiter

API_BASE_URL = "https://api.semanticscholar.org"
API_KEY_ENV = "SEMANTIC_SCHOLAR_API_KEY"
USER_AGENT = "SemanticScholar-MCP/0.1"


class SemanticScholarClient:
    """Small async client with shared pacing and bounded transport retries."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        retry_policy: RetryPolicy | None = None,
        rate_limiter: SharedRateLimiter | None = None,
        connect_timeout_seconds: float = 10.0,
        read_timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv(API_KEY_ENV)) or None
        self.retry_policy = retry_policy or RetryPolicy()
        self.rate_limiter = rate_limiter or SharedRateLimiter()
        self.timeout = httpx.Timeout(
            connect=connect_timeout_seconds,
            read=read_timeout_seconds,
            write=30.0,
            pool=10.0,
        )
        self._http: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        require_api_key: bool = False,
    ) -> JsonResponse:
        """Perform exactly one semantic API operation, plus bounded retries."""
        if not path.startswith("/") or "://" in path:
            raise ValueError(
                "path must be an absolute Semantic Scholar API path, not a URL."
            )

        if require_api_key and not self.api_key:
            raise AuthenticationRequiredError(
                f"This Semantic Scholar operation requires {API_KEY_ENV}."
            )

        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        attempts = 0
        for retry_index in range(self.retry_policy.max_retries + 1):
            attempts += 1
            await self.rate_limiter.wait()

            try:
                response = await self._get_http().request(
                    method=method.upper(),
                    url=path,
                    params=self._clean_params(params),
                    json=json_body,
                    headers=headers,
                )
            except httpx.TransportError as exc:
                if retry_index < self.retry_policy.max_retries:
                    await asyncio.sleep(self._retry_delay(retry_index))
                    continue
                raise TransportError(
                    "Semantic Scholar request failed at the transport layer.",
                    retryable=True,
                    attempts=attempts,
                    details={"exception_type": type(exc).__name__},
                ) from exc

            if (
                response.status_code in self.retry_policy.retry_status_codes
                and retry_index < self.retry_policy.max_retries
            ):
                delay = self._retry_after_seconds(response)
                if delay is None:
                    delay = self._retry_delay(retry_index)
                await asyncio.sleep(delay)
                continue

            if 200 <= response.status_code < 300:
                return self._decode_json(response)

            raise self._error_from_response(response, attempts=attempts)

        raise AssertionError("unreachable")

    def _get_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=API_BASE_URL,
                timeout=self.timeout,
                follow_redirects=False,
            )
        return self._http

    @staticmethod
    def _clean_params(
        params: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not params:
            return None
        return {
            key: value
            for key, value in params.items()
            if value is not None
        }

    def _retry_delay(self, retry_index: int) -> float:
        base = self.retry_policy.backoff_seconds(retry_index)
        jitter = random.uniform(0.0, self.retry_policy.jitter_seconds)
        return base + jitter

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None

        try:
            return max(0.0, float(value))
        except ValueError:
            pass

        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            return max(
                0.0,
                (when - datetime.now(UTC)).total_seconds(),
            )
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _decode_json(response: httpx.Response) -> JsonResponse:
        if response.status_code == 204 or not response.content:
            return {}

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidResponseError(
                "Semantic Scholar returned a non-JSON response.",
                status_code=response.status_code,
            ) from exc

        if not isinstance(data, dict | list):
            raise InvalidResponseError(
                "Semantic Scholar returned an unexpected JSON value.",
                status_code=response.status_code,
            )
        return data

    def _error_from_response(
        self,
        response: httpx.Response,
        *,
        attempts: int,
    ) -> SemanticScholarError:
        message = self._extract_error_message(response)
        status = response.status_code

        if status == 400 or status == 422:
            return InvalidRequestError(
                message,
                status_code=status,
                attempts=attempts,
            )

        if status in {401, 403}:
            return AuthenticationError(
                message,
                status_code=status,
                attempts=attempts,
            )

        if status == 404:
            return NotFoundError(
                message,
                status_code=status,
                attempts=attempts,
            )

        if status == 429:
            return RateLimitError(
                message,
                status_code=status,
                retryable=True,
                attempts=attempts,
            )

        if status >= 500:
            return UpstreamServerError(
                message,
                status_code=status,
                retryable=True,
                attempts=attempts,
            )

        return SemanticScholarError(
            message,
            status_code=status,
            attempts=attempts,
        )

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                for key in ("message", "error"):
                    value = payload.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except ValueError:
            pass

        text = response.text.strip()
        if text:
            return text[:500]

        return response.reason_phrase or "Semantic Scholar request failed."