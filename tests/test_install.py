import json
import tomllib

import pytest

from semantic_scholar_mcp import install


@pytest.fixture(autouse=True)
def isolate_api_key(monkeypatch):
    """Never touch the real environment variable or registry in tests."""
    monkeypatch.delenv(install.API_KEY_ENV, raising=False)
    monkeypatch.setattr(install, "_persist_user_env_var", _fail_persist)


def _fail_persist(name, value):  # pragma: no cover - guard, should not run
    raise AssertionError("_persist_user_env_var must be mocked in tests")


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(install.Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def _run(argv, python="C:\\venv\\Scripts\\python.exe", monkeypatch=None):
    monkeypatch.setattr(install, "_venv_python", lambda: python)
    return install.main(argv)


def test_creates_codex_config(home, monkeypatch):
    assert _run(["--codex-only"], monkeypatch=monkeypatch) == 0

    config = tomllib.loads((home / ".codex" / "config.toml").read_text(encoding="utf-8"))
    servers = config["mcp_servers"]
    assert set(install.SERVERS) <= set(servers)
    assert servers["s2ag"]["command"] == "C:\\venv\\Scripts\\python.exe"
    assert servers["s2ag"]["args"] == ["-m", "semantic_scholar_mcp.s2ag.server"]
    assert servers["s2ag"]["enabled"] is True


def test_creates_claude_config(home, monkeypatch):
    assert _run(["--claude-only"], monkeypatch=monkeypatch) == 0

    config = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    servers = config["mcpServers"]
    assert set(install.SERVERS) <= set(servers)
    assert servers["s2_datasets"]["command"] == "C:\\venv\\Scripts\\python.exe"
    assert servers["s2_datasets"]["args"] == ["-m", "semantic_scholar_mcp.datasets.server"]


def test_codex_preserves_existing_content(home, monkeypatch):
    codex = home / ".codex"
    codex.mkdir()
    (codex / "config.toml").write_text(
        'model = "gpt-5"\n\n[mcp_servers.other]\ncommand = "other"\nargs = ["serve"]\n',
        encoding="utf-8",
    )

    assert _run(["--codex-only"], monkeypatch=monkeypatch) == 0

    config = tomllib.loads((codex / "config.toml").read_text(encoding="utf-8"))
    assert config["model"] == "gpt-5"
    assert config["mcp_servers"]["other"]["command"] == "other"
    assert "s2ag" in config["mcp_servers"]


def test_claude_preserves_existing_content(home, monkeypatch):
    (home / ".claude.json").write_text(
        json.dumps({"foo": 1, "mcpServers": {"other": {"command": "x"}}}),
        encoding="utf-8",
    )

    assert _run(["--claude-only"], monkeypatch=monkeypatch) == 0

    config = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    assert config["foo"] == 1
    assert config["mcpServers"]["other"] == {"command": "x"}
    assert "s2ag" in config["mcpServers"]


def test_upsert_overwrites_stale_entry(home, monkeypatch):
    (home / ".claude.json").write_text(
        json.dumps({"mcpServers": {"s2ag": {"command": "OLD", "args": []}}}),
        encoding="utf-8",
    )

    assert _run(["--claude-only"], monkeypatch=monkeypatch) == 0

    config = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    assert config["mcpServers"]["s2ag"]["command"] == "C:\\venv\\Scripts\\python.exe"


def test_dry_run_writes_nothing(home, monkeypatch):
    assert _run(["--dry-run"], monkeypatch=monkeypatch) == 0

    assert not (home / ".codex" / "config.toml").exists()
    assert not (home / ".claude.json").exists()


def test_backup_created_when_editing(home, monkeypatch):
    (home / ".claude.json").write_text(json.dumps({"foo": 1}), encoding="utf-8")

    assert _run(["--claude-only"], monkeypatch=monkeypatch) == 0

    backup = home / ".claude.json.bak"
    assert backup.exists()
    assert json.loads(backup.read_text(encoding="utf-8")) == {"foo": 1}


def test_mutually_exclusive_scope_flags(home, monkeypatch):
    monkeypatch.setattr(install, "_venv_python", lambda: "python")
    with pytest.raises(SystemExit):
        install.main(["--codex-only", "--claude-only"])


def test_api_key_already_set_skips_prompt(monkeypatch, capsys):
    monkeypatch.setenv(install.API_KEY_ENV, "existing-key")

    def _no_prompt(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("getpass must not run when the key is already set")

    monkeypatch.setattr(install.getpass, "getpass", _no_prompt)

    install.configure_api_key(prompt=True)

    assert "already set" in capsys.readouterr().out


def test_api_key_prompt_persists_entered_value(monkeypatch, capsys):
    monkeypatch.setattr(install.sys, "platform", "win32")
    monkeypatch.setattr(install.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(install.getpass, "getpass", lambda prompt="": "  pasted-key  ")

    persisted = {}
    monkeypatch.setattr(
        install,
        "_persist_user_env_var",
        lambda name, value: persisted.update({name: value}),
    )

    install.configure_api_key(prompt=True)

    assert persisted == {install.API_KEY_ENV: "pasted-key"}
    assert "Stored" in capsys.readouterr().out


def test_api_key_empty_input_skips(monkeypatch, capsys):
    monkeypatch.setattr(install.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(install.getpass, "getpass", lambda prompt="": "   ")

    install.configure_api_key(prompt=True)

    assert "Skipped" in capsys.readouterr().out


def test_api_key_non_interactive_reports(monkeypatch, capsys):
    monkeypatch.setattr(install.sys.stdin, "isatty", lambda: False)

    install.configure_api_key(prompt=True)

    assert "interactive terminal" in capsys.readouterr().out


def test_no_api_key_flag_disables_check(home, monkeypatch, capsys):
    def _fail(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("configure_api_key must not run with --no-api-key")

    monkeypatch.setattr(install, "configure_api_key", _fail)
    assert _run(["--dry-run", "--no-api-key"], monkeypatch=monkeypatch) == 0
