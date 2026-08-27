import pytest

import semantic_scholar_mcp.s2ag.server as server


@pytest.mark.asyncio
async def test_get_paper_maps_to_expected_endpoint(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "paperId": "abc",
            "title": "Example",
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    result = await server.get_paper(
        "10.1038/nature12373",
        fields=["title", "year"],
    )

    assert result["title"] == "Example"

    fake.request.assert_awaited_once_with(
        "GET",
        "/graph/v1/paper/DOI:10.1038/nature12373",
        params={
            "fields": "title,year",
        },
    )


@pytest.mark.asyncio
async def test_get_papers_uses_batch_endpoint(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        [
            {"paperId": "a"},
            {"paperId": "b"},
        ]
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.get_papers(
        ["a", "10.1000/example"],
        fields=["title"],
    )

    fake.request.assert_awaited_once_with(
        "POST",
        "/graph/v1/paper/batch",
        params={
            "fields": "title",
        },
        json_body={
            "ids": [
                "a",
                "DOI:10.1000/example",
            ]
        },
    )


@pytest.mark.asyncio
async def test_get_papers_rejects_more_than_500(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory([])
    monkeypatch.setattr(server, "_client", fake)

    with pytest.raises(ValueError, match="at most 500"):
        await server.get_papers(
            [str(i) for i in range(501)]
        )

    fake.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_search_maps_token_without_auto_pagination(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "total": 1234,
            "token": "next-token",
            "data": [],
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    result = await server.search_papers(
        "transcranial magnetic stimulation",
        fields=["title", "year"],
        token="input-token",
        year="2020-2026",
        open_access_pdf=True,
    )

    assert result["token"] == "next-token"

    fake.request.assert_awaited_once_with(
        "GET",
        "/graph/v1/paper/search/bulk",
        params={
            "fields": "title,year",
            "publicationTypes": None,
            "openAccessPdf": "",
            "minCitationCount": None,
            "publicationDateOrYear": None,
            "year": "2020-2026",
            "venue": None,
            "fieldsOfStudy": None,
            "query": "transcranial magnetic stimulation",
            "token": "input-token",
            "sort": None,
        },
    )


@pytest.mark.asyncio
async def test_relevance_search_uses_offset_and_limit(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "total": 100,
            "offset": 20,
            "next": 40,
            "data": [],
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.search_papers_relevance(
        "SICI motor cortex",
        offset=20,
        limit=20,
    )

    args = fake.request.await_args

    assert args.args == (
        "GET",
        "/graph/v1/paper/search",
    )

    assert args.kwargs["params"]["query"] == "SICI motor cortex"
    assert args.kwargs["params"]["offset"] == 20
    assert args.kwargs["params"]["limit"] == 20


@pytest.mark.asyncio
async def test_relevance_search_rejects_limit_above_100(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory({})
    monkeypatch.setattr(server, "_client", fake)

    with pytest.raises(ValueError):
        await server.search_papers_relevance(
            "test",
            limit=101,
        )

    fake.request.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_citations_is_one_page_only(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "offset": 0,
            "next": 100,
            "data": [],
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    result = await server.get_citations(
        "abc",
        fields=["title"],
        offset=0,
        limit=100,
    )

    assert result["next"] == 100
    assert fake.request.await_count == 1

    fake.request.assert_awaited_once_with(
        "GET",
        "/graph/v1/paper/abc/citations",
        params={
            "fields": "title",
            "offset": 0,
            "limit": 100,
            "publicationDateOrYear": None,
        },
    )


@pytest.mark.asyncio
async def test_get_references_maps_exactly_once(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "data": [],
            "next": 50,
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.get_references(
        "abc",
        offset=0,
        limit=50,
    )

    fake.request.assert_awaited_once_with(
        "GET",
        "/graph/v1/paper/abc/references",
        params={
            "fields": None,
            "offset": 0,
            "limit": 50,
        },
    )


@pytest.mark.asyncio
async def test_get_author(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "authorId": "123",
            "name": "Ada Example",
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.get_author(
        "123",
        fields=["name", "paperCount"],
    )

    fake.request.assert_awaited_once_with(
        "GET",
        "/graph/v1/author/123",
        params={
            "fields": "name,paperCount",
        },
    )


@pytest.mark.asyncio
async def test_get_authors_uses_batch(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory([])
    monkeypatch.setattr(server, "_client", fake)

    await server.get_authors(
        ["1", "2"],
        fields=["name"],
    )

    fake.request.assert_awaited_once_with(
        "POST",
        "/graph/v1/author/batch",
        params={
            "fields": "name",
        },
        json_body={
            "ids": ["1", "2"],
        },
    )


@pytest.mark.asyncio
async def test_search_authors(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "total": 1,
            "data": [],
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.search_authors(
        "John Smith",
        fields=["name"],
        limit=10,
    )

    fake.request.assert_awaited_once_with(
        "GET",
        "/graph/v1/author/search",
        params={
            "query": "John Smith",
            "fields": "name",
            "offset": 0,
            "limit": 10,
        },
    )


@pytest.mark.asyncio
async def test_get_author_papers(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "data": [],
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.get_author_papers(
        "123",
        fields=["title"],
        offset=0,
        limit=100,
    )

    fake.request.assert_awaited_once_with(
        "GET",
        "/graph/v1/author/123/papers",
        params={
            "fields": "title",
            "offset": 0,
            "limit": 100,
            "publicationDateOrYear": None,
        },
    )