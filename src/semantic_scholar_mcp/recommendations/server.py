"""Deterministic MCP tools for the Semantic Scholar Recommendations API."""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from mcp.server import MCPServer

from semantic_scholar_mcp.common import (
    SemanticScholarClient,
    comma_separated,
    normalize_paper_id,
    require_nonempty_list,
    validate_limit,
)

mcp = MCPServer("Semantic Scholar Recommendations")
_client = SemanticScholarClient()


def _paper_segment(paper_id: str) -> str:
    # Preserve "/" because Semantic Scholar explicitly documents DOI:/URL:
    # identifiers in this path form; quote query/fragment/control characters.
    return quote(
        normalize_paper_id(paper_id),
        safe=":/",
    )


@mcp.tool()
async def recommend_for_paper(
    paper_id: str,
    limit: int = 20,
    fields: list[str] | None = None,
    pool: Literal["recent", "all-cs"] = "recent",
) -> dict[str, Any]:
    """Get Semantic Scholar recommendations from one positive seed paper.

    `pool` maps directly to the upstream `from` query parameter.
    """
    validate_limit(limit, maximum=500)

    result = await _client.request(
        "GET",
        (f"/recommendations/v1/papers/forpaper/{_paper_segment(paper_id)}"),
        params={
            "from": pool,
            "limit": limit,
            "fields": comma_separated(fields),
        },
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected recommendations response.")

    return result


@mcp.tool()
async def recommend_from_examples(
    positive_paper_ids: list[str],
    negative_paper_ids: list[str] | None = None,
    limit: int = 20,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get recommendations from caller-supplied positive and negative seeds."""
    validate_limit(limit, maximum=500)

    positive = [
        normalize_paper_id(value)
        for value in require_nonempty_list(
            positive_paper_ids,
            "positive_paper_ids",
        )
    ]

    negative = [normalize_paper_id(value) for value in (negative_paper_ids or []) if value.strip()]

    result = await _client.request(
        "POST",
        "/recommendations/v1/papers/",
        params={
            "limit": limit,
            "fields": comma_separated(fields),
        },
        json_body={
            "positivePaperIds": positive,
            "negativePaperIds": negative,
        },
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected recommendations response.")

    return result


def main() -> None:
    """Run the Recommendations MCP server over stdio."""
    mcp.run("stdio")


if __name__ == "__main__":
    main()
