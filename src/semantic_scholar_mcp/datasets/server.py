"""Deterministic MCP tools for the Semantic Scholar Datasets API."""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import quote

from mcp.server import MCPServer

from semantic_scholar_mcp.common import (
    SemanticScholarClient,
    require_nonempty,
)

mcp = MCPServer("Semantic Scholar Datasets")
_client = SemanticScholarClient()


def _segment(value: str, name: str) -> str:
    return quote(require_nonempty(value, name), safe="")


@mcp.tool()
async def list_releases() -> list[str]:
    """List available Semantic Scholar dataset release IDs."""
    result = await _client.request(
        "GET",
        "/datasets/v1/release/",
    )

    if not isinstance(result, list):
        raise TypeError("Semantic Scholar returned an unexpected releases response.")

    return cast(list[str], result)


@mcp.tool()
async def get_release(
    release_id: str = "latest",
) -> dict[str, Any]:
    """Get metadata describing one Semantic Scholar dataset release."""
    result = await _client.request(
        "GET",
        f"/datasets/v1/release/{_segment(release_id, 'release_id')}",
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected release response.")

    return result


@mcp.tool()
async def get_dataset(
    dataset_name: str,
    release_id: str = "latest",
) -> dict[str, Any]:
    """Get metadata and temporary download links for one dataset.

    This tool returns the upstream manifest only. It does not download shards.
    An API key is required by Semantic Scholar for this operation.
    """
    result = await _client.request(
        "GET",
        (
            f"/datasets/v1/release/"
            f"{_segment(release_id, 'release_id')}"
            f"/dataset/{_segment(dataset_name, 'dataset_name')}"
        ),
        require_api_key=True,
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected dataset response.")

    return result


@mcp.tool()
async def get_diffs(
    dataset_name: str,
    start_release_id: str,
    end_release_id: str = "latest",
) -> dict[str, Any]:
    """Get ordered incremental update/delete manifests between two releases.

    This tool returns diff metadata only. It does not download or apply files.
    An API key is required by Semantic Scholar for this operation.
    """
    result = await _client.request(
        "GET",
        (
            f"/datasets/v1/diffs/"
            f"{_segment(start_release_id, 'start_release_id')}"
            f"/to/{_segment(end_release_id, 'end_release_id')}"
            f"/{_segment(dataset_name, 'dataset_name')}"
        ),
        require_api_key=True,
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected dataset-diff response.")

    return result


def main() -> None:
    """Run the Datasets MCP server over stdio."""
    mcp.run("stdio")


if __name__ == "__main__":
    main()
