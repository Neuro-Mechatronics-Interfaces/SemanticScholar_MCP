import pytest

import semantic_scholar_mcp.recommendations.server as server


@pytest.mark.asyncio
async def test_recommend_for_paper(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "recommendedPapers": [],
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.recommend_for_paper(
        "10.1038/nature12373",
        limit=25,
        fields=["title", "year"],
        pool="recent",
    )

    fake.request.assert_awaited_once_with(
        "GET",
        (
            "/recommendations/v1/papers/forpaper/"
            "DOI:10.1038/nature12373"
        ),
        params={
            "from": "recent",
            "limit": 25,
            "fields": "title,year",
        },
    )


@pytest.mark.asyncio
async def test_recommend_from_examples_preserves_seeds(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "recommendedPapers": [],
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.recommend_from_examples(
        positive_paper_ids=[
            "paper-a",
            "10.1000/example",
        ],
        negative_paper_ids=[
            "paper-b",
        ],
        limit=20,
        fields=["title"],
    )

    fake.request.assert_awaited_once_with(
        "POST",
        "/recommendations/v1/papers/",
        params={
            "limit": 20,
            "fields": "title",
        },
        json_body={
            "positivePaperIds": [
                "paper-a",
                "DOI:10.1000/example",
            ],
            "negativePaperIds": [
                "paper-b",
            ],
        },
    )


@pytest.mark.asyncio
async def test_recommendations_reject_limit_above_500(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory({})
    monkeypatch.setattr(server, "_client", fake)

    with pytest.raises(ValueError):
        await server.recommend_for_paper(
            "paper",
            limit=501,
        )

    fake.request.assert_not_awaited()