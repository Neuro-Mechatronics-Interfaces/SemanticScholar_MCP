import pytest

import semantic_scholar_mcp.datasets.server as server


@pytest.mark.asyncio
async def test_list_releases(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        [
            "2026-08-18",
            "2026-08-11",
        ]
    )
    monkeypatch.setattr(server, "_client", fake)

    result = await server.list_releases()

    assert result[0] == "2026-08-18"

    fake.request.assert_awaited_once_with(
        "GET",
        "/datasets/v1/release/",
    )


@pytest.mark.asyncio
async def test_get_release(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "release_id": "2026-08-18",
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.get_release(
        "2026-08-18"
    )

    fake.request.assert_awaited_once_with(
        "GET",
        "/datasets/v1/release/2026-08-18",
    )


@pytest.mark.asyncio
async def test_get_dataset_requires_authenticated_client_operation(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "name": "papers",
            "files": [],
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.get_dataset(
        "papers",
        release_id="2026-08-18",
    )

    fake.request.assert_awaited_once_with(
        "GET",
        (
            "/datasets/v1/release/"
            "2026-08-18/dataset/papers"
        ),
        require_api_key=True,
    )


@pytest.mark.asyncio
async def test_get_dataset_does_not_download_files(
    monkeypatch,
    fake_client_factory,
) -> None:
    response = {
        "name": "papers",
        "files": [
            "https://example.invalid/papers-001.gz",
            "https://example.invalid/papers-002.gz",
        ],
    }

    fake = fake_client_factory(response)
    monkeypatch.setattr(server, "_client", fake)

    result = await server.get_dataset(
        "papers",
    )

    assert result == response
    assert fake.request.await_count == 1


@pytest.mark.asyncio
async def test_get_diffs(
    monkeypatch,
    fake_client_factory,
) -> None:
    fake = fake_client_factory(
        {
            "diffs": [],
        }
    )
    monkeypatch.setattr(server, "_client", fake)

    await server.get_diffs(
        dataset_name="papers",
        start_release_id="2026-08-11",
        end_release_id="2026-08-18",
    )

    fake.request.assert_awaited_once_with(
        "GET",
        (
            "/datasets/v1/diffs/"
            "2026-08-11/to/2026-08-18/papers"
        ),
        require_api_key=True,
    )