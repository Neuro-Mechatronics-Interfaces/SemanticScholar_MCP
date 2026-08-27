from __future__ import annotations

from typing import Any

import pytest


class NoopRateLimiter:
    """Test limiter that records calls without sleeping."""

    def __init__(self) -> None:
        self.calls = 0

    async def wait(self) -> None:
        self.calls += 1


class FakeSemanticScholarClient:
    """Small deterministic stand-in for server mapping tests."""

    def __init__(self, response: Any) -> None:
        from unittest.mock import AsyncMock

        self.request = AsyncMock(return_value=response)


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run live Semantic Scholar integration tests.",
    )


def pytest_collection_modifyitems(config, items) -> None:
    if config.getoption("--run-integration"):
        return

    skip = pytest.mark.skip(
        reason="Use --run-integration to run live API tests."
    )

    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)

@pytest.fixture
def no_rate_limiter() -> NoopRateLimiter:
    return NoopRateLimiter()


@pytest.fixture
def fake_client_factory():
    def make(response: Any) -> FakeSemanticScholarClient:
        return FakeSemanticScholarClient(response)

    return make