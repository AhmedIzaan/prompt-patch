"""Verify installation, configuration boundaries, and honest CLI behavior."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from promptpatch import __version__
from promptpatch.config import ConfigurationError, load_settings


def run_cli(tmp_path, *args, env=None):
    clean_env = {key: value for key, value in os.environ.items()
                 if not key.startswith(("GEMINI_", "PROMPTPATCH_"))}
    clean_env.update(env or {})
    return subprocess.run(
        [sys.executable, "-m", "promptpatch.cli", *args],
        cwd=tmp_path, env=clean_env, capture_output=True, text=True, check=False,
    )


def test_installed_package():
    from importlib.metadata import version

    assert version("promptpatch") == __version__


def test_configuration_defaults_and_overrides():
    defaults = load_settings({})
    assert defaults.gemini_api_key is None
    assert defaults.mode == "live"
    assert defaults.db_path == Path("data/promptpatch.sqlite3")
    settings = load_settings({
        "GEMINI_API_KEY": "test-secret-only",
        "GEMINI_MODEL": "test-model",
        "PROMPTPATCH_DB_PATH": "custom/domain.sqlite3",
        "PROMPTPATCH_CHECKPOINT_DB_PATH": "custom/checkpoints.sqlite3",
        "PROMPTPATCH_DEMO_REPO": "custom/repo",
        "PROMPTPATCH_MODE": "replay",
    })
    assert settings.gemini_api_key.get_secret_value() == "test-secret-only"
    assert settings.gemini_model == "test-model"
    assert settings.db_path == Path("custom/domain.sqlite3")
    assert settings.checkpoint_db_path == Path("custom/checkpoints.sqlite3")
    assert settings.demo_repo == Path("custom/repo")
    assert settings.mode == "replay"
    assert "test-secret-only" not in repr(settings)
    assert "test-secret-only" not in settings.model_dump_json()


def test_invalid_config_does_not_echo_input():
    with pytest.raises(ConfigurationError) as error:
        load_settings({"PROMPTPATCH_MODE": "secret-in-wrong-field"})
    assert "secret-in-wrong-field" not in str(error.value)


def test_help(tmp_path):
    result = run_cli(tmp_path, "--help")
    assert result.returncode == 0
    assert "doctor" in result.stdout and "init" in result.stdout


@pytest.mark.parametrize("key", ["", "test-secret-only"])
def test_doctor_is_local_safe_and_honest(tmp_path, key):
    result = run_cli(tmp_path, "doctor", env={"GEMINI_API_KEY": key})
    assert result.returncode == 0
    assert "Provider: not connected" in result.stdout
    assert ("set (not validated)" if key else "not set") in result.stdout
    assert "test-secret-only" not in result.stdout + result.stderr
    assert list(tmp_path.iterdir()) == []


def test_doctor_invalid_configuration(tmp_path):
    result = run_cli(tmp_path, "doctor", env={"PROMPTPATCH_MODE": "secret-in-wrong-field"})
    assert result.returncode == 2
    assert "Invalid configuration" in result.stderr
    assert "secret-in-wrong-field" not in result.stdout + result.stderr


def test_init_creates_domain_database_idempotently(tmp_path):
    result = run_cli(tmp_path, "init")
    assert result.returncode == 0
    assert "Domain database initialized" in result.stdout
    assert (tmp_path / "data/promptpatch.sqlite3").is_file()
    assert not (tmp_path / "data/checkpoints.sqlite3").exists()
    assert run_cli(tmp_path, "init").returncode == 0


def test_init_rejects_colliding_database_paths(tmp_path):
    result = run_cli(tmp_path, "init", env={
        "PROMPTPATCH_DB_PATH": "same.sqlite3",
        "PROMPTPATCH_CHECKPOINT_DB_PATH": "same.sqlite3",
    })
    assert result.returncode == 1
    assert "initialization failed" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_init_reports_filesystem_error_without_echoing_path(tmp_path):
    (tmp_path / "blocked").write_text("existing file")
    result = run_cli(tmp_path, "init", env={"PROMPTPATCH_DB_PATH": "blocked/private-value.sqlite3"})
    assert result.returncode == 1
    assert "initialization failed" in result.stderr
    assert "private-value" not in result.stderr
