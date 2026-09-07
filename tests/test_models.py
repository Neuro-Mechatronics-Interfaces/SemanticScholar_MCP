import pytest

from semantic_scholar_mcp.common.models import (
    comma_separated,
    normalize_author_id,
    normalize_paper_id,
    require_nonempty,
    require_nonempty_list,
    validate_limit,
    validate_offset,
)


def test_comma_separated() -> None:
    assert comma_separated(["title", "year", "authors"]) == "title,year,authors"
    assert comma_separated(["title", "", " year "]) == "title,year"
    assert comma_separated([]) is None
    assert comma_separated(None) is None


@pytest.mark.parametrize(
    ("input_id", "expected"),
    [
        (
            "10.1038/nature12373",
            "DOI:10.1038/nature12373",
        ),
        (
            "https://doi.org/10.1038/nature12373",
            "DOI:10.1038/nature12373",
        ),
        (
            "doi:10.1038/nature12373",
            "DOI:10.1038/nature12373",
        ),
        (
            "pmid:12345",
            "PMID:12345",
        ),
        (
            "arxiv:2301.12345",
            "ARXIV:2301.12345",
        ),
        (
            "a5de30adc5c22bc86e8cfabe7fbd07c052d196a8",
            "a5de30adc5c22bc86e8cfabe7fbd07c052d196a8",
        ),
    ],
)
def test_normalize_paper_id(input_id: str, expected: str) -> None:
    assert normalize_paper_id(input_id) == expected


def test_normalize_author_id_strips_whitespace() -> None:
    assert normalize_author_id(" 12345 ") == "12345"


def test_require_nonempty_rejects_empty() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        require_nonempty("   ", "query")


def test_require_nonempty_list() -> None:
    assert require_nonempty_list(
        [" a ", "", "b"],
        "values",
    ) == ["a", "b"]


def test_require_nonempty_list_rejects_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        require_nonempty_list([], "values")


def test_require_nonempty_list_enforces_maximum() -> None:
    with pytest.raises(ValueError, match="at most 2"):
        require_nonempty_list(
            ["a", "b", "c"],
            "values",
            max_items=2,
        )


@pytest.mark.parametrize("value", [1, 20, 100])
def test_validate_limit_accepts_range(value: int) -> None:
    assert validate_limit(value, maximum=100) == value


@pytest.mark.parametrize("value", [0, 101])
def test_validate_limit_rejects_out_of_range(value: int) -> None:
    with pytest.raises(ValueError):
        validate_limit(value, maximum=100)


def test_validate_offset() -> None:
    assert validate_offset(0) == 0
    assert validate_offset(100) == 100

    with pytest.raises(ValueError):
        validate_offset(-1)
