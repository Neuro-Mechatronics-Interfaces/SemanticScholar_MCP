import pytest
from mcp import Client

from semantic_scholar_mcp.datasets.server import mcp as datasets_mcp
from semantic_scholar_mcp.recommendations.server import (
    mcp as recommendations_mcp,
)
from semantic_scholar_mcp.s2ag.server import mcp as s2ag_mcp


@pytest.mark.asyncio
async def test_s2ag_tools_registered() -> None:
    async with Client(
        s2ag_mcp,
        raise_exceptions=True,
    ) as client:
        result = await client.list_tools()

    names = {tool.name for tool in result.tools}

    assert names == {
        "get_paper",
        "get_papers",
        "search_papers",
        "search_papers_relevance",
        "get_citations",
        "get_references",
        "get_author",
        "get_authors",
        "search_authors",
        "get_author_papers",
    }


@pytest.mark.asyncio
async def test_recommendation_tools_registered() -> None:
    async with Client(
        recommendations_mcp,
        raise_exceptions=True,
    ) as client:
        result = await client.list_tools()

    names = {tool.name for tool in result.tools}

    assert names == {
        "recommend_for_paper",
        "recommend_from_examples",
    }


@pytest.mark.asyncio
async def test_dataset_tools_registered() -> None:
    async with Client(
        datasets_mcp,
        raise_exceptions=True,
    ) as client:
        result = await client.list_tools()

    names = {tool.name for tool in result.tools}

    assert names == {
        "list_releases",
        "get_release",
        "get_dataset",
        "get_diffs",
    }


@pytest.mark.asyncio
async def test_tool_schema_exposes_pagination_explicitly() -> None:
    async with Client(
        s2ag_mcp,
        raise_exceptions=True,
    ) as client:
        result = await client.list_tools()

    tools = {
        tool.name: tool
        for tool in result.tools
    }

    citations = tools["get_citations"]

    properties = citations.input_schema["properties"]

    assert "offset" in properties
    assert "limit" in properties


@pytest.mark.asyncio
async def test_bulk_search_has_token_but_no_limit() -> None:
    async with Client(
        s2ag_mcp,
        raise_exceptions=True,
    ) as client:
        result = await client.list_tools()

    tools = {
        tool.name: tool
        for tool in result.tools
    }

    bulk_search = tools["search_papers"]

    properties = bulk_search.input_schema["properties"]

    assert "token" in properties
    assert "limit" not in properties