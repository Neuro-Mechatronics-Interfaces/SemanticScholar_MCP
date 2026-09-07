"""Deterministic MCP tools for the Semantic Scholar Academic Graph API."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from mcp.server import MCPServer

from semantic_scholar_mcp.common import (
    SemanticScholarClient,
    comma_separated,
    normalize_author_id,
    normalize_paper_id,
    require_nonempty,
    require_nonempty_list,
    validate_limit,
    validate_offset,
)

mcp = MCPServer("Semantic Scholar Academic Graph")
_client = SemanticScholarClient()


def _paper_segment(paper_id: str) -> str:
    # Preserve "/" because Semantic Scholar documents DOI:/URL: identifiers
    # directly in this path form; encode query/fragment/control characters.
    return quote(
        normalize_paper_id(paper_id),
        safe=":/",
    )


def _author_segment(author_id: str) -> str:
    return quote(
        normalize_author_id(author_id),
        safe="",
    )


def _search_filters(
    *,
    fields: list[str] | None,
    publication_types: list[str] | None,
    open_access_pdf: bool,
    min_citation_count: int | None,
    publication_date_or_year: str | None,
    year: str | None,
    venue: list[str] | None,
    fields_of_study: list[str] | None,
) -> dict[str, Any]:
    if min_citation_count is not None and min_citation_count < 0:
        raise ValueError("min_citation_count must be >= 0.")

    return {
        "fields": comma_separated(fields),
        "publicationTypes": comma_separated(publication_types),
        "openAccessPdf": "" if open_access_pdf else None,
        "minCitationCount": min_citation_count,
        "publicationDateOrYear": publication_date_or_year,
        "year": year,
        "venue": comma_separated(venue),
        "fieldsOfStudy": comma_separated(fields_of_study),
    }


@mcp.tool()
async def get_paper(
    paper_id: str,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get one paper by Semantic Scholar ID or supported external identifier."""
    result = await _client.request(
        "GET",
        f"/graph/v1/paper/{_paper_segment(paper_id)}",
        params={
            "fields": comma_separated(fields),
        },
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected paper response.")

    return result


@mcp.tool()
async def get_papers(
    paper_ids: list[str],
    fields: list[str] | None = None,
) -> list[Any]:
    """Batch-get up to 500 caller-supplied paper identifiers."""
    ids = [
        normalize_paper_id(value)
        for value in require_nonempty_list(
            paper_ids,
            "paper_ids",
            max_items=500,
        )
    ]

    result = await _client.request(
        "POST",
        "/graph/v1/paper/batch",
        params={
            "fields": comma_separated(fields),
        },
        json_body={
            "ids": ids,
        },
    )

    if not isinstance(result, list):
        raise TypeError("Semantic Scholar returned an unexpected paper-batch response.")

    return result


@mcp.tool()
async def search_papers(
    query: str,
    fields: list[str] | None = None,
    token: str | None = None,
    sort: str | None = None,
    publication_types: list[str] | None = None,
    open_access_pdf: bool = False,
    min_citation_count: int | None = None,
    publication_date_or_year: str | None = None,
    year: str | None = None,
    venue: list[str] | None = None,
    fields_of_study: list[str] | None = None,
) -> dict[str, Any]:
    """Run one token-paginated `/paper/search/bulk` request.

    This endpoint returns up to 1000 papers per upstream call and does not
    accept a `limit` argument. Pass the returned token explicitly for the
    next page.
    """
    params = _search_filters(
        fields=fields,
        publication_types=publication_types,
        open_access_pdf=open_access_pdf,
        min_citation_count=min_citation_count,
        publication_date_or_year=publication_date_or_year,
        year=year,
        venue=venue,
        fields_of_study=fields_of_study,
    )

    params.update(
        {
            "query": require_nonempty(query, "query"),
            "token": token,
            "sort": sort,
        }
    )

    result = await _client.request(
        "GET",
        "/graph/v1/paper/search/bulk",
        params=params,
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected bulk-search response.")

    return result


@mcp.tool()
async def search_papers_relevance(
    query: str,
    fields: list[str] | None = None,
    offset: int = 0,
    limit: int = 20,
    publication_types: list[str] | None = None,
    open_access_pdf: bool = False,
    min_citation_count: int | None = None,
    publication_date_or_year: str | None = None,
    year: str | None = None,
    venue: list[str] | None = None,
    fields_of_study: list[str] | None = None,
) -> dict[str, Any]:
    """Run one relevance-ranked `/paper/search` request.

    Relevance search is limited by Semantic Scholar to 100 results per call
    and 1000 relevance-ranked results total.
    """
    validate_offset(offset)
    validate_limit(
        limit,
        maximum=100,
    )

    params = _search_filters(
        fields=fields,
        publication_types=publication_types,
        open_access_pdf=open_access_pdf,
        min_citation_count=min_citation_count,
        publication_date_or_year=publication_date_or_year,
        year=year,
        venue=venue,
        fields_of_study=fields_of_study,
    )

    params.update(
        {
            "query": require_nonempty(query, "query"),
            "offset": offset,
            "limit": limit,
        }
    )

    result = await _client.request(
        "GET",
        "/graph/v1/paper/search",
        params=params,
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected relevance-search response.")

    return result


@mcp.tool()
async def get_citations(
    paper_id: str,
    fields: list[str] | None = None,
    offset: int = 0,
    limit: int = 100,
    publication_date_or_year: str | None = None,
) -> dict[str, Any]:
    """Get one page of papers that cite the requested paper."""
    validate_offset(offset)
    validate_limit(
        limit,
        maximum=1000,
    )

    result = await _client.request(
        "GET",
        (f"/graph/v1/paper/{_paper_segment(paper_id)}/citations"),
        params={
            "fields": comma_separated(fields),
            "offset": offset,
            "limit": limit,
            "publicationDateOrYear": publication_date_or_year,
        },
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected citations response.")

    return result


@mcp.tool()
async def get_references(
    paper_id: str,
    fields: list[str] | None = None,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """Get one page of references cited by the requested paper."""
    validate_offset(offset)
    validate_limit(
        limit,
        maximum=1000,
    )

    result = await _client.request(
        "GET",
        (f"/graph/v1/paper/{_paper_segment(paper_id)}/references"),
        params={
            "fields": comma_separated(fields),
            "offset": offset,
            "limit": limit,
        },
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected references response.")

    return result


@mcp.tool()
async def get_author(
    author_id: str,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get one Semantic Scholar author by author ID."""
    result = await _client.request(
        "GET",
        f"/graph/v1/author/{_author_segment(author_id)}",
        params={
            "fields": comma_separated(fields),
        },
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected author response.")

    return result


@mcp.tool()
async def get_authors(
    author_ids: list[str],
    fields: list[str] | None = None,
) -> list[Any]:
    """Batch-get up to 1000 Semantic Scholar author IDs."""
    ids = [
        normalize_author_id(value)
        for value in require_nonempty_list(
            author_ids,
            "author_ids",
            max_items=1000,
        )
    ]

    result = await _client.request(
        "POST",
        "/graph/v1/author/batch",
        params={
            "fields": comma_separated(fields),
        },
        json_body={
            "ids": ids,
        },
    )

    if not isinstance(result, list):
        raise TypeError("Semantic Scholar returned an unexpected author-batch response.")

    return result


@mcp.tool()
async def search_authors(
    query: str,
    fields: list[str] | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Search authors by name using one offset-paginated request."""
    validate_offset(offset)
    validate_limit(
        limit,
        maximum=1000,
    )

    result = await _client.request(
        "GET",
        "/graph/v1/author/search",
        params={
            "query": require_nonempty(query, "query"),
            "fields": comma_separated(fields),
            "offset": offset,
            "limit": limit,
        },
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected author-search response.")

    return result


@mcp.tool()
async def get_author_papers(
    author_id: str,
    fields: list[str] | None = None,
    offset: int = 0,
    limit: int = 100,
    publication_date_or_year: str | None = None,
) -> dict[str, Any]:
    """Get one page of papers associated with a Semantic Scholar author."""
    validate_offset(offset)
    validate_limit(
        limit,
        maximum=1000,
    )

    result = await _client.request(
        "GET",
        (f"/graph/v1/author/{_author_segment(author_id)}/papers"),
        params={
            "fields": comma_separated(fields),
            "offset": offset,
            "limit": limit,
            "publicationDateOrYear": publication_date_or_year,
        },
    )

    if not isinstance(result, dict):
        raise TypeError("Semantic Scholar returned an unexpected author-papers response.")

    return result


def main() -> None:
    """Run the S2AG MCP server over stdio."""
    mcp.run("stdio")


if __name__ == "__main__":
    main()
