"""Shared data types and small deterministic normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias
from urllib.parse import urlparse

JsonResponse: TypeAlias = dict[str, Any] | list[Any]


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Transport retry policy.

    ``max_retries`` counts retries after the initial request.
    """

    max_retries: int = 5
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    jitter_seconds: float = 0.25
    retry_status_codes: frozenset[int] = frozenset({429, 500, 502, 503, 504})

    def backoff_seconds(self, retry_index: int) -> float:
        """Return exponential backoff before retry ``retry_index`` (zero based)."""
        delay = self.base_delay_seconds * (2**retry_index)
        return min(delay, self.max_delay_seconds)


def comma_separated(values: list[str] | None) -> str | None:
    """Convert a list of API field/filter values to Semantic Scholar CSV syntax."""
    if values is None:
        return None

    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned:
        return None
    return ",".join(cleaned)


def require_nonempty(value: str, name: str) -> str:
    """Strip and validate a required string."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} must not be empty.")
    return cleaned


def require_nonempty_list(
    values: list[str],
    name: str,
    *,
    max_items: int | None = None,
) -> list[str]:
    """Strip and validate a required list of strings."""
    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned:
        raise ValueError(f"{name} must contain at least one value.")
    if max_items is not None and len(cleaned) > max_items:
        raise ValueError(f"{name} must contain at most {max_items} values.")
    return cleaned


def validate_limit(limit: int, *, maximum: int, minimum: int = 1) -> int:
    """Validate an API result limit."""
    if not minimum <= limit <= maximum:
        raise ValueError(f"limit must be between {minimum} and {maximum}.")
    return limit


def validate_offset(offset: int) -> int:
    """Validate a non-negative offset."""
    if offset < 0:
        raise ValueError("offset must be >= 0.")
    return offset


def normalize_paper_id(paper_id: str) -> str:
    """Normalize common paper identifiers without performing an API lookup.

    Accepted upstream identifiers include Semantic Scholar IDs and prefixed
    identifiers such as DOI:, ARXIV:, PMID:, PMCID:, CorpusId:, MAG:, ACL:,
    and URL:.

    As a convenience, a raw DOI or doi.org URL is converted to DOI:<doi>.
    """
    value = require_nonempty(paper_id, "paper_id")

    lowered = value.lower()
    doi_hosts = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
    )
    if lowered.startswith(doi_hosts):
        parsed = urlparse(value)
        doi = parsed.path.lstrip("/")
        if doi:
            return f"DOI:{doi}"

    if lowered.startswith("10.") and "/" in value:
        return f"DOI:{value}"

    canonical_prefixes = {
        "doi": "DOI",
        "arxiv": "ARXIV",
        "pmid": "PMID",
        "pmcid": "PMCID",
        "corpusid": "CorpusId",
        "mag": "MAG",
        "acl": "ACL",
        "url": "URL",
    }
    if ":" in value:
        prefix, remainder = value.split(":", 1)
        canonical = canonical_prefixes.get(prefix.lower())
        if canonical and remainder.strip():
            return f"{canonical}:{remainder.strip()}"

    return value


def normalize_author_id(author_id: str) -> str:
    """Normalize an author ID without resolving it."""
    return require_nonempty(author_id, "author_id")