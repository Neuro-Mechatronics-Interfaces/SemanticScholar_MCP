"""Register the Semantic Scholar MCP servers with local agent hosts.

This console script writes user-global MCP configuration for Codex
(``~/.codex/config.toml``) and Claude Code (``~/.claude.json``) so the three
Semantic Scholar servers are available across projects.

Each server is invoked as ``<venv python> -m <module>`` rather than through the
generated ``.exe`` console launchers. The interpreter path is derived from the
installed location of this package, so the configuration keeps pointing at the
virtual environment the package was installed into.

Existing configuration is preserved: only the three Semantic Scholar server
entries are inserted or overwritten (upsert). All other content is left
untouched, and for Codex the file's comments and formatting are preserved.

If ``SEMANTIC_SCHOLAR_API_KEY`` is not already present in the environment, the
installer offers to store it as a persistent user environment variable (Windows
only). The key is never written into any MCP configuration file.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import sys
from pathlib import Path

# Server name -> module executed with ``python -m``.
SERVERS: dict[str, str] = {
    "s2ag": "semantic_scholar_mcp.s2ag.server",
    "s2_recommendations": "semantic_scholar_mcp.recommendations.server",
    "s2_datasets": "semantic_scholar_mcp.datasets.server",
}

API_KEY_ENV = "SEMANTIC_SCHOLAR_API_KEY"

# Codex-specific per-server timeouts, matching the documented example.
_CODEX_STARTUP_TIMEOUT_SEC = 15
_CODEX_TOOL_TIMEOUT_SEC = 120


def _venv_python() -> str:
    """Return the interpreter path for the environment this package lives in.

    ``sys.executable`` is the interpreter currently running the installer. When
    ``semantic-scholar-install`` is launched from a virtual environment's
    ``Scripts``/``bin`` directory, this is exactly the interpreter the MCP
    servers should use.
    """

    executable = sys.executable
    if not executable:
        raise RuntimeError(
            "Unable to determine the Python interpreter path (sys.executable is empty)."
        )
    return str(Path(executable).resolve())


def _codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def _claude_config_path() -> Path:
    return Path.home() / ".claude.json"


def _backup(path: Path) -> Path | None:
    """Copy ``path`` to ``path.bak`` before editing; return the backup path."""

    if not path.exists():
        return None
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    return backup


def _codex_server_table(python: str, module: str) -> dict[str, object]:
    return {
        "command": python,
        "args": ["-m", module],
        "startup_timeout_sec": _CODEX_STARTUP_TIMEOUT_SEC,
        "tool_timeout_sec": _CODEX_TOOL_TIMEOUT_SEC,
        "enabled": True,
    }


def _claude_server_entry(python: str, module: str) -> dict[str, object]:
    return {
        "command": python,
        "args": ["-m", module],
    }


def update_codex(python: str, *, dry_run: bool) -> str:
    """Upsert the Semantic Scholar servers into the user-global Codex config."""

    import tomlkit

    path = _codex_config_path()
    if path.exists():
        document = tomlkit.parse(path.read_text(encoding="utf-8"))
    else:
        document = tomlkit.document()

    mcp_servers = document.get("mcp_servers")
    if mcp_servers is None:
        mcp_servers = tomlkit.table()
        document["mcp_servers"] = mcp_servers

    for name, module in SERVERS.items():
        table = tomlkit.table()
        for key, value in _codex_server_table(python, module).items():
            table[key] = value
        mcp_servers[name] = table

    rendered = tomlkit.dumps(document)
    if dry_run:
        return rendered

    _backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return rendered


def update_claude(python: str, *, dry_run: bool) -> str:
    """Upsert the Semantic Scholar servers into the user-global Claude config."""

    path = _claude_config_path()
    if path.exists():
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if text.strip() else {}
    else:
        data = {}

    if not isinstance(data, dict):
        raise TypeError(f"{path} does not contain a JSON object.")

    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers

    for name, module in SERVERS.items():
        servers[name] = _claude_server_entry(python, module)

    rendered = json.dumps(data, indent=2) + "\n"
    if dry_run:
        return rendered

    _backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return rendered


def _persist_user_env_var(name: str, value: str) -> None:
    """Persist ``name=value`` as a user environment variable on Windows.

    Writes ``HKEY_CURRENT_USER\\Environment`` via ``winreg`` (avoiding the
    1024-character truncation of ``setx``) and broadcasts ``WM_SETTINGCHANGE``
    so newly launched processes inherit the value. This matches the ``"User"``
    scope of ``[Environment]::SetEnvironmentVariable``.
    """

    if sys.platform != "win32":
        raise RuntimeError("Persistent environment variables are only supported on Windows.")

    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    # Also set it for the current process so a following run sees it as present.
    os.environ[name] = value

    # Notify running processes (Explorer, shells) that the environment changed.
    try:
        import ctypes

        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_long()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Environment",
            SMTO_ABORTIFHUNG,
            5000,
            ctypes.byref(result),
        )
    except Exception:
        # The variable is persisted regardless; the broadcast is best-effort.
        pass


def configure_api_key(*, prompt: bool) -> None:
    """Ensure an API key is available, optionally prompting for one.

    When ``SEMANTIC_SCHOLAR_API_KEY`` is already set in the environment, this
    reports that and does nothing. Otherwise, if ``prompt`` is true and the
    session is interactive, it asks for a key (input is hidden and may be left
    empty to skip) and persists it as a user environment variable.
    """

    existing = os.environ.get(API_KEY_ENV, "").strip()
    if existing:
        print(f"{API_KEY_ENV} is already set; leaving it unchanged.")
        return

    if not prompt:
        return

    if not sys.stdin or not sys.stdin.isatty():
        print(f"{API_KEY_ENV} is not set. Run in an interactive terminal to be prompted for it.")
        return

    print(f"\n{API_KEY_ENV} is not set.")
    print("Paste your Semantic Scholar API key to store it, or press Enter to skip.")
    try:
        key = getpass.getpass(f"{API_KEY_ENV}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nSkipped API key configuration.")
        return

    if not key:
        print("Skipped API key configuration; continuing without an API key.")
        return

    if sys.platform != "win32":
        print(
            f"Set the key manually so future sessions inherit it, e.g.:\n"
            f'  export {API_KEY_ENV}="{key[:4]}..."'
        )
        return

    _persist_user_env_var(API_KEY_ENV, key)
    print(
        f"Stored {API_KEY_ENV} as a user environment variable. "
        "Restart terminals and MCP hosts so they inherit it."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="semantic-scholar-install",
        description=(
            "Register the Semantic Scholar MCP servers with the user-global "
            "Codex (~/.codex/config.toml) and Claude Code (~/.claude.json) "
            "configuration."
        ),
    )
    parser.add_argument(
        "--dry-run",
        "--print",
        dest="dry_run",
        action="store_true",
        help="Print the resulting configuration without writing any files.",
    )
    parser.add_argument(
        "--codex-only",
        action="store_true",
        help="Update only the Codex configuration.",
    )
    parser.add_argument(
        "--claude-only",
        action="store_true",
        help="Update only the Claude Code configuration.",
    )
    parser.add_argument(
        "--no-api-key",
        dest="api_key",
        action="store_false",
        help="Do not check for or prompt for SEMANTIC_SCHOLAR_API_KEY.",
    )
    args = parser.parse_args(argv)

    if args.codex_only and args.claude_only:
        parser.error("--codex-only and --claude-only are mutually exclusive.")

    python = _venv_python()

    do_codex = not args.claude_only
    do_claude = not args.codex_only

    if do_codex:
        rendered = update_codex(python, dry_run=args.dry_run)
        if args.dry_run:
            print(f"# --- {_codex_config_path()} ---")
            print(rendered)
        else:
            print(f"Updated {_codex_config_path()}")

    if do_claude:
        rendered = update_claude(python, dry_run=args.dry_run)
        if args.dry_run:
            print(f"// --- {_claude_config_path()} ---")
            print(rendered)
        else:
            print(f"Updated {_claude_config_path()}")

    if not args.dry_run:
        print(f"MCP servers point at: {python} -m <module>")

    if args.api_key and not args.dry_run:
        configure_api_key(prompt=True)
    elif args.api_key and args.dry_run:
        configure_api_key(prompt=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
