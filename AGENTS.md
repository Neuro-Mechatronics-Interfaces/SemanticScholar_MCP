# AGENTS.md

## Purpose

This repository provides small, deterministic Model Context Protocol servers for the Semantic Scholar APIs.

It contains three independent MCP surfaces:

* `s2ag` — Semantic Scholar Academic Graph API
* `recommendations` — Semantic Scholar Recommendations API
* `datasets` — Semantic Scholar Datasets API

The MCP servers should remain thin wrappers around documented Semantic Scholar operations.

The agent or MCP client is responsible for higher-level research reasoning and orchestration.

## Core Principle

An MCP tool performs one documented Semantic Scholar operation.

It may:

* validate arguments;
* normalize identifiers;
* enforce API limits;
* perform bounded retry/backoff for transient failures;
* normalize API responses;
* cache exact responses where appropriate.

It must not:

* choose additional search terms;
* recursively traverse citations;
* automatically paginate to exhaustion;
* automatically request recommendations;
* rank papers using an LLM;
* summarize papers;
* infer scientific relevance;
* automatically download datasets;
* automatically retrieve PDFs;
* silently issue additional Semantic Scholar queries.

Except for bounded retry behavior following transient failures, one MCP invocation should correspond to one upstream Semantic Scholar API operation.

## Repository Structure

```text
src/
└── semantic_scholar_mcp/
    ├── common/
    │   ├── client.py
    │   ├── errors.py
    │   ├── models.py
    │   └── rate_limit.py
    ├── datasets/
    │   └── server.py
    ├── recommendations/
    │   └── server.py
    └── s2ag/
        └── server.py
```

Responsibilities should remain separated.

### `common/client.py`

Owns:

* HTTP transport;
* API-key injection;
* common request execution;
* timeouts;
* retry behavior;
* response parsing;
* common HTTP error translation.

It must not contain research-specific logic.

### `common/rate_limit.py`

Owns the rate limit shared by all Semantic Scholar MCP processes running on the machine.

The introductory authenticated Semantic Scholar rate is one request per second across endpoints. Do not implement an independent one-request-per-second limiter in each server process.

The limiter must therefore be interprocess-safe.

A reasonable implementation uses:

* a shared application-state directory;
* a filesystem lock;
* a persisted timestamp for the most recent request.

Default to at least approximately 1.05 seconds between upstream requests.

Do not increase the configured request rate unless the user has documented authorization from Semantic Scholar for a higher limit.

### `common/errors.py`

Defines stable application-level errors.

Prefer explicit errors such as:

* `AuthenticationError`
* `RateLimitError`
* `NotFoundError`
* `InvalidRequestError`
* `UpstreamServerError`
* `TransportError`

Do not leak arbitrary `httpx` exceptions through the MCP interface when a clearer stable error can be returned.

### `common/models.py`

Contains shared typed models or data structures when they materially improve API clarity.

Do not build a second comprehensive model of the entire Semantic Scholar schema unnecessarily.

Prefer preserving documented Semantic Scholar field names in returned data.

## MCP SDK

Use the current stable v2 line of the official Python MCP SDK.

For new server code, use:

```python
from mcp.server import MCPServer
```

rather than the deprecated v1 `FastMCP` interface.

Each `server.py` should expose:

```python
def main() -> None:
    ...
```

so it can be registered as a console-script entry point.

It should also remain directly runnable when practical:

```python
if __name__ == "__main__":
    main()
```

Use stdio as the default transport for these local MCP servers.

## API Authentication

Read the Semantic Scholar API key only from:

```text
SEMANTIC_SCHOLAR_API_KEY
```

The key is optional for operations that Semantic Scholar permits without authentication.

If present, send it using the documented API-key header.

Never:

* hard-code an API key;
* accept an API key as an MCP tool argument;
* commit a key to Git;
* print a key in logs;
* return a key in an MCP response;
* place a key in `.mcp.json`;
* place a key in `.codex/config.toml`;
* include a real key in tests.

If an endpoint requires authenticated access and no key is configured, return a clear authentication-required error.

Do not repeatedly retry an authentication failure.

Semantic Scholar notes that inactive API keys may be removed after extended inactivity. Authentication failures must therefore fail gracefully rather than assuming a configured key remains permanently valid.

## Rate Limits and Service Protection

Semantic Scholar access must be conservative.

The project has successfully exercised the API without authentication and may also use an approved API key.

Unless an explicitly authorized higher rate is configured, assume:

```text
maximum upstream request rate: 1 request / second
```

across all Semantic Scholar APIs and all MCP processes using the same local installation.

### Do not circumvent limits

Never increase throughput by:

* alternating authenticated and unauthenticated requests;
* rotating API keys;
* running independent per-process rate-limit pools;
* launching concurrent requests to evade a shared limit;
* retrying `429` responses rapidly;
* using multiple agents to bypass the intended limit.

## Retry Policy

Retries are transport behavior and do not count as additional semantic operations.

Retry only transient conditions, including:

* HTTP `429`;
* appropriate `5xx` upstream failures;
* temporary network/connection failures.

When a `Retry-After` header is supplied, honor it.

Otherwise use bounded exponential backoff with modest jitter.

A suitable default is approximately:

```text
1 s
2 s
4 s
8 s
16 s
```

with a finite retry count.

Do not retry indefinitely.

Do not normally retry:

* `400`
* `401`
* `403`
* `404`

Return a structured error after retries are exhausted.

## Request Efficiency

Use the least expensive documented API operation suitable for the requested task.

Prefer batch or bulk endpoints when the caller has already supplied multiple identifiers.

Do not internally turn a single-paper request into a multi-paper search.

Request only explicitly required fields or a documented conservative default field set.

Do not retrieve abstracts, embeddings, citation contexts, or other comparatively large fields unless requested or required by the tool contract.

Pagination must remain caller-controlled.

If an upstream response includes a continuation token or offset, return it to the MCP client.

Do not automatically consume subsequent pages.

## S2AG Server

The `s2ag` MCP wraps the Semantic Scholar Academic Graph API.

Initial tools should include approximately:

```text
get_paper
get_papers
search_papers
search_papers_relevance
get_citations
get_references

get_author
get_authors
search_authors
get_author_papers
```

### Search behavior

Prefer the bulk paper-search endpoint for ordinary structured searches.

Expose relevance-ranked paper search separately because it has different semantics and potentially different cost.

Do not silently substitute one search endpoint for the other.

### Batch behavior

`get_papers` and `get_authors` should use documented batch endpoints.

Do not implement batch tools by looping over single-record API requests.

### Citation traversal

`get_citations` and `get_references` perform one page of one requested edge traversal.

They must not recursively explore the citation graph.

## Recommendations Server

The `recommendations` MCP should initially expose only:

```text
recommend_for_paper
recommend_from_examples
```

These correspond directly to Semantic Scholar recommendation operations.

Inputs such as positive and negative paper IDs must be supplied by the caller.

The MCP must not decide which papers should become positive or negative examples.

The MCP must not recursively feed recommendations back into the recommendation service.

The recommendation ranking returned by Semantic Scholar should be preserved.

Do not apply an additional model-generated relevance ranking.

## Datasets Server

The `datasets` MCP manages Semantic Scholar dataset metadata and manifests.

Initial tools should include:

```text
list_releases
get_release
get_dataset
get_diffs
```

The server may retrieve:

* available release identifiers;
* metadata describing a release;
* dataset metadata;
* official dataset download manifests or URLs;
* incremental update/delete manifests.

It must not automatically download large dataset payloads.

In particular, do not expose an MCP tool whose ordinary invocation can unexpectedly download tens or hundreds of gigabytes.

Actual corpus download/import operations should be implemented separately as explicit CLI or user-controlled maintenance commands if they become necessary.

## Dataset Safety

Dataset operations are potentially very large.

Never infer that a dataset should be downloaded because:

* a literature query returned few results;
* local search would be faster;
* an agent wants more context;
* a research question might benefit from broader coverage.

Downloading a Semantic Scholar corpus requires explicit user intent.

Bulk datasets should normally live outside this Git repository.

## Semantic Scholar License

All use of the Semantic Scholar APIs and datasets must comply with the applicable Semantic Scholar/AI2 license and documentation.

Do not implement features intended to:

* evade service limits;
* redistribute protected API data improperly;
* expose API credentials;
* bypass access controls;
* use Semantic Scholar data outside permitted terms.

If Semantic Scholar data is later displayed publicly, review the then-current attribution requirements before implementing that display.

The current API license includes specific attribution requirements for public use of Semantic Scholar data.

## HTTP Client

Use one shared HTTP-client implementation.

Prefer `httpx`.

Centralize base URLs and request construction rather than duplicating them between MCP servers.

Do not construct arbitrary caller-provided URLs and fetch them.

The client should only communicate with documented Semantic Scholar API hosts and endpoints.

Set explicit connection and read timeouts.

Do not disable TLS verification.

## Response Behavior

Return structured data suitable for another program to consume.

Preserve stable identifiers when available, particularly:

* Semantic Scholar `paperId`;
* DOI;
* PMID;
* arXiv ID;
* Semantic Scholar author IDs.

Do not convert API responses into prose summaries.

Do not discard continuation metadata.

Do not silently hide upstream fields explicitly requested by the caller.

If normalization is performed, it must be deterministic and documented.

## Logging

MCP stdio uses stdout for protocol traffic.

Application diagnostics must therefore not write arbitrary text to stdout.

Use stderr or the MCP SDK's supported logging facilities for diagnostics.

Never log API keys.

Avoid logging full response bodies by default.

## Testing

Tests belong under `tests/`.

Unit tests must not depend on the live Semantic Scholar service.

Mock HTTP responses using `respx` or an equivalent `httpx`-compatible mechanism.

Tests should cover at minimum:

* API-key header inclusion and omission;
* request URL and parameter construction;
* field handling;
* batch requests;
* continuation-token preservation;
* shared rate limiting;
* `429` handling;
* `Retry-After`;
* bounded exponential backoff;
* transient `5xx` retries;
* non-retryable `4xx` behavior;
* authentication-required dataset operations;
* structured error translation;
* each MCP tool mapping to exactly the intended upstream operation.

Tests should verify that tools do **not**:

* automatically paginate;
* recursively traverse;
* issue recommendations opportunistically;
* trigger dataset downloads;
* make undocumented extra API calls.

## Integration Tests

Live Semantic Scholar integration tests must be opt-in.

They should not run as part of the ordinary unit-test suite.

Mark them explicitly, for example:

```text
integration
```

and skip them unless the developer intentionally enables them.

Integration tests must respect the same shared rate limiter as production code.

Keep live tests small.

Do not create large citation traversals merely to test connectivity.

## Code Quality

Use type hints for public functions and MCP tool signatures.

Prefer small functions and explicit data flow.

Avoid unnecessary framework abstractions.

Do not introduce:

* an ORM;
* a vector database;
* an LLM dependency;
* agent frameworks;
* background worker infrastructure;
* a general-purpose web crawler

unless the repository's requirements materially change.

Run before considering implementation work complete:

```text
pytest
ruff check .
ruff format --check .
```

## Adding Tools

Before adding an MCP tool:

1. identify the exact documented Semantic Scholar operation;
2. confirm that an existing tool does not already represent it;
3. define a narrow input schema;
4. determine authentication requirements;
5. determine pagination behavior;
6. determine rate-limit implications;
7. add unit tests verifying the exact HTTP operation;
8. document the new tool in `README.md`.

Do not add convenience tools that merely compose several existing MCP calls.

Composition belongs to the consuming agent unless there is a strong deterministic API-level reason otherwise.

## Scope Boundary

This repository answers:

> How can a caller deterministically access Semantic Scholar through MCP?

It does not answer:

> What literature is scientifically important?
>
> What conclusions should be drawn from a paper?
>
> What papers should a scientist read next?
>
> How should a research repository organize its scientific concepts?

Those are responsibilities of the consuming research system or agent.
