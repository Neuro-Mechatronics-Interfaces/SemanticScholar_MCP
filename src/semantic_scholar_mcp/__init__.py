"""Deterministic MCP wrappers for Semantic Scholar APIs."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("semantic-scholar-mcp")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = ["__version__"]