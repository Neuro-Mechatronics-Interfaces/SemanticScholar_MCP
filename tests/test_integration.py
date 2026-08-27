import os

import pytest

from semantic_scholar_mcp.common import (
    RetryPolicy,
    SemanticScholarClient,
    SharedRateLimiter,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_unauthenticated_paper_lookup(
    monkeypatch,
) -> None:
    """Verify basic unauthenticated Semantic Scholar connectivity.

    This intentionally performs only one inexpensive direct paper lookup.
    """
    monkeypatch.delenv(
        "SEMANTIC_SCHOLAR_API_KEY",
        raising=False,
    )

    client = SemanticScholarClient(
        api_key=None,
        retry_policy=RetryPolicy(
            max_retries=2,
        ),
        rate_limiter=SharedRateLimiter(),
    )

    try:
        result = await client.request(
            "GET",
            "/graph/v1/paper/DOI:10.1038/nature12373",
            params={
                "fields": "title,year",
            },
        )
    finally:
        await client.aclose()

    assert isinstance(result, dict)
    assert result["title"] == "Nanometer scale thermometry in a living cell"
    assert result["year"] == 2013


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_authenticated_dataset_release() -> None:
    """Exercise an authenticated API operation only when a key is available."""
    if not os.getenv("SEMANTIC_SCHOLAR_API_KEY"):
        pytest.skip(
            "SEMANTIC_SCHOLAR_API_KEY is not configured."
        )

    client = SemanticScholarClient()

    try:
        result = await client.request(
            "GET",
            "/datasets/v1/release/latest",
        )
    finally:
        await client.aclose()

    assert isinstance(result, dict)