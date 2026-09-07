# SemanticScholar_MCP

Deterministic Model Context Protocol interfaces for the three Semantic Scholar API families:

* **S2AG** — Academic Graph search, metadata, authors, citations, and references.
* **Recommendations** — Semantic Scholar's paper recommendation service.
* **Datasets** — release discovery, dataset manifests, and incremental dataset updates.

The project intentionally provides thin API wrappers rather than an agentic literature-research system.

## Design

The central rule is:

> One MCP tool invocation represents one documented Semantic Scholar operation.

The servers perform transport-level work such as validation, authentication, rate limiting, retries, and response normalization.

They do not decide what literature is scientifically important.

For example:

```text
Agent
  │
  ├── "Search for paired-pulse TMS papers"
  │         │
  │         ▼
  │       S2AG MCP
  │         │
  │         ▼
  │    Semantic Scholar
  │
  ├── "Recommend papers from these three seed papers"
  │         │
  │         ▼
  │  Recommendations MCP
  │         │
  │         ▼
  │    Semantic Scholar
  │
  └── "Describe the latest S2ORC dataset release"
            │
            ▼
       Datasets MCP
            │
            ▼
       Semantic Scholar
```

Search expansion, scientific interpretation, summarization, citation-graph exploration strategy, and research synthesis remain responsibilities of the consuming agent.

## Repository Structure

```text
SemanticScholar_MCP/
├── src/
│   └── semantic_scholar_mcp/
│       ├── common/
│       │   ├── client.py
│       │   ├── errors.py
│       │   ├── models.py
│       │   ├── rate_limit.py
│       │   └── __init__.py
│       ├── datasets/
│       │   ├── server.py
│       │   └── __init__.py
│       ├── recommendations/
│       │   ├── server.py
│       │   └── __init__.py
│       ├── s2ag/
│       │   ├── server.py
│       │   └── __init__.py
│       └── __init__.py
├── tests/
├── AGENTS.md
├── CLAUDE.md
├── pyproject.toml
└── README.md
```

## Requirements

* Python 3.11 or newer
* Internet access to Semantic Scholar
* Optional Semantic Scholar API key

The implementation uses the current v2 line of the official Python MCP SDK.

## Installation

Create a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the package in editable mode with development dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Alternatively, with `uv`:

```powershell
uv venv --python 3.14
uv pip install -e ".[dev]"
```
Python 3.14 is not required; the project supports Python 3.11 and later. 

After configuring the Python package environment, optionally run tests:  

```powershell
pytest
ruff check .
ruff format --check .
```

If you have already configured `SEMANTIC_SCHOLAR_API_KEY` as a system environment variable (see next section, [`Authentication`](#authentication)), you can also test live integration:  
```powershell
pytest --run-integration
```

_**Note**_: If you set the system environment variable to your API key **after** starting _any_ VSCode window, you need to close **all** VSCode windows to completely restart VSCode before the system environment will be captured by tools run through VSCode Extensions!


## Authentication

Semantic Scholar supports unauthenticated access to many API operations.

When an API key is available, expose it to the MCP processes through:

```powershell
$env:SEMANTIC_SCHOLAR_API_KEY = "..."
```

Do not place the key in:

* `.mcp.json`;
* `.codex/config.toml`;
* source code;
* committed `.env` files;
* test fixtures.

The MCP servers automatically use the key when it is present.

Operations that require authentication should return an explicit error when no key is configured. 

_**Note (again)**_: If you set the system environment variable to your API key **after** starting _any_ VSCode window, you need to close **all** VSCode windows to completely restart VSCode before the system environment will be captured by tools run through VSCode Extensions!

## Build Updates 

The scripts `.\rebuild.ps1` and `.\version.ps1` are provided as utilities to facilitate version updates when rebuilding:  

### `rebuild.ps1`

To rebuild without auto-incrementing the `patch` number, explicitly specify the switch:  
```powershell
.\rebuild.ps1 -SkipVersionIncrement
```
Otherwise, `.\rebuild.ps1` auto-increments the patch number in `pyproject.toml` directly.  

### `version.ps1`

To increment `<major> | <minor> | <patch>` without rebuilding:  
```powershell
.\version.ps1 patch -NoRebuild
```
To increment `minor` version, resetting `patch` to 0, and rebuild:  
```powershell
.\version.ps1 minor
```
To increment `major` version, resetting both `minor` and `patch` to 0, and rebuild:  
```powershell
.\version.ps1 major
```

## MCP Client Configuration

The three Semantic Scholar MCP servers can be configured either:

* **project-locally**, so they are available only within a particular repository; or
* **user-globally**, so they are available across repositories.

The servers are:

* `s2ag` — Semantic Scholar Academic Graph
* `s2_recommendations` — Semantic Scholar Recommendations API
* `s2_datasets` — Semantic Scholar Datasets API

The examples below assume this repository is installed at:

```text
C:\MyRepos\Python\SemanticScholar_MCP
```

Adjust the path as needed.

The examples deliberately invoke the virtual environment's Python interpreter with `python -m ...` rather than invoking the generated `semantic-scholar-*.exe` console launchers directly. This is recommended during local development on Windows because running console launchers can prevent `pip` from replacing them during an editable reinstall.

### Automated user-global registration

An optional installer can write the user-global Codex and Claude Code configuration for you, so you do not have to edit `~/.codex/config.toml` and `~/.claude.json` by hand.

Install it with the `install` extra (included in `dev`):

```powershell
python -m pip install -e ".[install]"
```

Then run:

```powershell
semantic-scholar-install
```

This upserts the three Semantic Scholar servers into:

* `~/.codex/config.toml` (Codex, `[mcp_servers.*]` tables), and
* `~/.claude.json` (Claude Code, `mcpServers` entries).

The interpreter path is derived from the environment the installer runs in (`sys.executable`), so the written configuration points at that virtual environment's `python.exe` and invokes each server as `python -m <module>`. Only the three Semantic Scholar entries are inserted or overwritten; all other content is preserved, and for Codex the file's comments and formatting are kept intact. A `.bak` copy of each edited file is written before changes.

Useful flags:

```powershell
semantic-scholar-install --dry-run    # Print the resulting config without writing
semantic-scholar-install --codex-only # Update only ~/.codex/config.toml
semantic-scholar-install --claude-only # Update only ~/.claude.json
```

After running the installer, verify the registrations with `codex mcp list` and `claude mcp list`.

Because Claude Code owns additional state in `~/.claude.json`, the manual `claude mcp add --scope user` flow documented below remains available if you prefer to let Claude Code manage its own file.

### Codex

Codex supports both user-global and project-local `config.toml` files.

#### Project-local Codex configuration

Create or edit:

```text
<project>/.codex/config.toml
```

For example:

```toml
[mcp_servers.s2ag]
command = 'C:\MyRepos\Python\SemanticScholar_MCP\.venv\Scripts\python.exe'
args = ["-m", "semantic_scholar_mcp.s2ag.server"]
startup_timeout_sec = 15
tool_timeout_sec = 120
enabled = true

[mcp_servers.s2_recommendations]
command = 'C:\MyRepos\Python\SemanticScholar_MCP\.venv\Scripts\python.exe'
args = ["-m", "semantic_scholar_mcp.recommendations.server"]
startup_timeout_sec = 15
tool_timeout_sec = 120
enabled = true

[mcp_servers.s2_datasets]
command = 'C:\MyRepos\Python\SemanticScholar_MCP\.venv\Scripts\python.exe'
args = ["-m", "semantic_scholar_mcp.datasets.server"]
startup_timeout_sec = 15
tool_timeout_sec = 120
enabled = true
```

Project-scoped Codex configuration is loaded only for projects that Codex considers trusted.

#### User-global Codex configuration

To make the servers available to Codex across projects, place the same configuration in:

```text
~/.codex/config.toml
```

On Windows this is normally:

```text
%USERPROFILE%\.codex\config.toml
```

For example:

```text
C:\Users\<username>\.codex\config.toml
```

The MCP server blocks themselves are identical to the project-local example above.

#### Verify Codex configuration

From a terminal:

```powershell
codex mcp list
```

Individual registrations can also be inspected with:

```powershell
codex mcp get s2ag
codex mcp get s2_recommendations
codex mcp get s2_datasets
```

### Claude Code

Claude Code distinguishes between project-shared and user-scoped MCP servers.

#### Project-local / project-shared Claude configuration

Create:

```text
<project>/.mcp.json
```

with:

```json
{
  "mcpServers": {
    "s2ag": {
      "command": "C:\\MyRepos\\Python\\SemanticScholar_MCP\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "semantic_scholar_mcp.s2ag.server"
      ]
    },
    "s2_recommendations": {
      "command": "C:\\MyRepos\\Python\\SemanticScholar_MCP\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "semantic_scholar_mcp.recommendations.server"
      ]
    },
    "s2_datasets": {
      "command": "C:\\MyRepos\\Python\\SemanticScholar_MCP\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "semantic_scholar_mcp.datasets.server"
      ]
    }
  }
}
```

This file can be committed to the consuming repository when the MCP configuration is intended to be shared with other users of that repository.

#### User-global Claude configuration

For global Claude Code configuration, the preferred approach is to let Claude Code manage the user-scoped MCP registrations.

Run:

```powershell
claude mcp add --scope user s2ag -- "C:\MyRepos\Python\SemanticScholar_MCP\.venv\Scripts\python.exe" -m semantic_scholar_mcp.s2ag.server

claude mcp add --scope user s2_recommendations -- "C:\MyRepos\Python\SemanticScholar_MCP\.venv\Scripts\python.exe" -m semantic_scholar_mcp.recommendations.server

claude mcp add --scope user s2_datasets -- "C:\MyRepos\Python\SemanticScholar_MCP\.venv\Scripts\python.exe" -m semantic_scholar_mcp.datasets.server
```

Claude Code currently stores user-scoped MCP configuration in:

```text
~/.claude.json
```

On Windows:

```text
%USERPROFILE%\.claude.json
```

Using `claude mcp add --scope user` is preferred over manually editing this file because Claude Code owns additional state in `.claude.json`.

Verify the registrations with:

```powershell
claude mcp list
```

If a particular Claude Code version has trouble loading user-scoped MCP servers, the project `.mcp.json` configuration is the simplest fallback.

### Semantic Scholar API Key

Many Semantic Scholar operations can work without authentication. Operations requiring an API key use:

```text
SEMANTIC_SCHOLAR_API_KEY
```

Do not commit the key to an MCP configuration file.

On Windows, it may be persisted as a user environment variable:

```powershell
[Environment]::SetEnvironmentVariable(
    "SEMANTIC_SCHOLAR_API_KEY",
    "YOUR_API_KEY",
    "User"
)
```

Restart VS Code, Codex, Claude Code, or other MCP hosts after setting the variable so newly launched MCP processes inherit it.

The MCP servers automatically use the key when it is present and otherwise remain unauthenticated where Semantic Scholar permits anonymous access.

### Project-local vs. user-global

A useful rule is:

| Scope   | Codex                  | Claude Code                   | Recommended when                                                   |
| ------- | ---------------------- | ----------------------------- | ------------------------------------------------------------------ |
| Project | `.codex/config.toml`   | `.mcp.json`                   | The repository explicitly depends on these research tools          |
| User    | `~/.codex/config.toml` | `claude mcp add --scope user` | You want Semantic Scholar available in many unrelated repositories |

For a research repository whose agents are explicitly expected to perform literature discovery, project-local configuration is usually preferable because the available research tooling travels with the repository.

For general personal access to Semantic Scholar from arbitrary projects, user-global configuration is more convenient.


## Shared Rate Limiting

Semantic Scholar's introductory authenticated rate limit applies across API endpoints rather than independently to each MCP server.

This repository therefore uses a shared interprocess limiter:

```text
S2AG MCP ────────────────┐
                         │
Recommendations MCP ─────┼── shared limiter ──> Semantic Scholar
                         │
Datasets MCP ────────────┘
```

The default implementation should allow no more than approximately one upstream request per second across all three local servers.

This matters when multiple hosts are running simultaneously, for example:

```text
VS Code / Codex
Claude Code
MCP Inspector
tests
```

The limiter should coordinate these processes rather than maintaining an independent clock in each one.

### Retry Behavior

Transient upstream failures may be retried using bounded exponential backoff.

Examples include:

* HTTP `429`;
* transient `5xx` responses;
* temporary network failures.

`Retry-After` is honored when provided.

Ordinary client errors such as invalid requests, rejected authentication, and missing resources are not repeatedly retried.

Retries are bounded; the MCP never retries indefinitely.

## S2AG MCP

Run:

```powershell
semantic-scholar-s2ag
```

or:

```powershell
python -m semantic_scholar_mcp.s2ag.server
```

The initial API surface is intended to include:

| Tool                      | Purpose                                    |
| ------------------------- | ------------------------------------------ |
| `get_paper`               | Retrieve one known paper                   |
| `get_papers`              | Batch-retrieve known papers                |
| `search_papers`           | Structured/bulk paper search               |
| `search_papers_relevance` | Relevance-ranked paper search              |
| `get_citations`           | Retrieve one page of papers citing a paper |
| `get_references`          | Retrieve one page of a paper's references  |
| `get_author`              | Retrieve one author                        |
| `get_authors`             | Batch-retrieve known authors               |
| `search_authors`          | Search authors                             |
| `get_author_papers`       | Retrieve one page of an author's papers    |

Pagination remains explicit.

A citation request does not recursively traverse the citation graph.

A search does not automatically issue follow-up searches.

## Recommendations MCP

Run:

```powershell
semantic-scholar-recommendations
```

or:

```powershell
python -m semantic_scholar_mcp.recommendations.server
```

The initial surface is intentionally small:

| Tool                      | Purpose                                                                |
| ------------------------- | ---------------------------------------------------------------------- |
| `recommend_for_paper`     | Request recommendations using one seed paper                           |
| `recommend_from_examples` | Request recommendations using supplied positive and negative paper IDs |

The server passes caller-selected seeds to Semantic Scholar.

It does not choose its own seeds or apply a second LLM-generated ranking to the results.

Example conceptual workflow:

```text
positive:
  paper A
  paper B
  paper C

negative:
  paper D

        │
        ▼

recommend_from_examples

        │
        ▼

Semantic Scholar recommendation ranking
```

## Datasets MCP

Run:

```powershell
semantic-scholar-datasets
```

or:

```powershell
python -m semantic_scholar_mcp.datasets.server
```

The initial tools are:

| Tool            | Purpose                                            |
| --------------- | -------------------------------------------------- |
| `list_releases` | List available dataset releases                    |
| `get_release`   | Inspect a particular release                       |
| `get_dataset`   | Obtain metadata/manifest information for a dataset |
| `get_diffs`     | Obtain update/delete manifests between releases    |

The Datasets MCP deliberately does **not** automatically download entire Semantic Scholar datasets.

Some Semantic Scholar datasets are very large. Retrieving a manifest is an appropriate MCP operation; initiating a multi-gigabyte corpus download requires explicit user-controlled tooling.

A future dedicated CLI may provide commands such as:

```text
s2-dataset download ...
s2-dataset update ...
s2-dataset verify ...
```

without making those operations implicit MCP behavior.

## Determinism

For this project, deterministic means that tool semantics are explicit and inspectable.

A tool may:

```text
validate input
    ↓
wait for rate limiter
    ↓
make one documented API request
    ↓
retry transient transport failures if necessary
    ↓
normalize response
    ↓
return structured data
```

A tool must not silently become:

```text
search
   ↓
search again with different terms
   ↓
fetch every page
   ↓
walk citations
   ↓
request recommendations
   ↓
rank with an LLM
   ↓
summarize papers
```

Higher-level orchestration belongs outside this repository.

## Pagination

Pagination is caller-controlled.

When Semantic Scholar returns a continuation token, offset, or equivalent cursor, the MCP returns that value.

The caller can explicitly request another page.

The MCP does not automatically fetch all available pages.

This protects both determinism and API usage.

## Fields

Where Semantic Scholar supports explicit response fields, tools should request only the fields needed by the caller.

A small default field set may be provided for usability.

Large fields such as abstracts or citation contexts should not be requested automatically unless part of the documented tool default.

## Errors

Upstream conditions should be translated into stable, understandable MCP errors.

Examples:

```text
authentication_required
rate_limited
not_found
invalid_request
upstream_error
transport_error
```

Where useful, the structured error may retain:

* HTTP status;
* retryability;
* number of attempts;
* Semantic Scholar error message.

Secrets must never be included.

## Development

Run unit tests:

```powershell
pytest
```

Run linting:

```powershell
ruff check .
```

Check formatting:

```powershell
ruff format --check .
```

Apply formatting:

```powershell
ruff format .
```

Live Semantic Scholar tests are marked separately:

```powershell
pytest --run-integration
```

Ordinary unit tests should mock HTTP interactions and must not consume Semantic Scholar API quota.

## Testing Philosophy

The most important tests verify API fidelity.

For every MCP tool, tests should confirm:

```text
input
  ↓
exact expected HTTP operation
  ↓
expected response normalization
```

Tests should also verify the absence of hidden behavior.

For example, a single citation request should generate one citation API operation—not automatically request subsequent pages or references.

## Relationship to Research Tools

This repository should remain domain-neutral.

For example, it can expose:

```text
paper A cites paper B
```

or:

```text
Semantic Scholar recommends paper C from seeds A and B
```

but it should not conclude:

```text
paper C is the strongest evidence for a particular neuroscience hypothesis
```

A separate research repository, Research MCP, or human researcher can make that interpretation.

This separation allows the Semantic Scholar layer to remain:

* deterministic;
* reusable;
* easy to test;
* independent of any specific scientific field;
* usable by different MCP hosts and agents.

## Semantic Scholar Usage

This project is intended for legitimate research use and must comply with the current Semantic Scholar API license and documentation.

API usage should:

* respect active rate limits;
* use batch/bulk operations where appropriate;
* request only needed fields;
* use bounded exponential backoff;
* protect API credentials;
* avoid unrestricted API crawling;
* prefer the Datasets API when truly corpus-scale access is required.

Public products or displays using Semantic Scholar response data may have additional attribution requirements. Review the current Semantic Scholar license before adding public-facing data presentation.

See `AGENTS.md` for the normative development and API-use rules for this repository.
