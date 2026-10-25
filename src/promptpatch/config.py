"""Read local configuration without displaying credentials or creating files."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError


class ConfigurationError(ValueError):
    """A safe configuration error suitable for CLI output."""


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    gemini_api_key: SecretStr | None = Field(default=None, repr=False, exclude=True)
    gemini_model: str | None = None
    db_path: Path = Path("data/promptpatch.sqlite3")
    checkpoint_db_path: Path = Path("data/checkpoints.sqlite3")
    demo_repo: Path = Path("samples/demo_git_repo")
    mode: Literal["live", "replay"] = "live"


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Read the supplied mapping or process environment; no .env auto-loading.

    Relative paths are relative to the caller's working directory. No directory
    creation, database initialization, or provider validation happens here.
    """
    env = os.environ if environ is None else environ
    values: dict[str, object] = {}
    names = {
        "GEMINI_API_KEY": "gemini_api_key",
        "GEMINI_MODEL": "gemini_model",
        "PROMPTPATCH_DB_PATH": "db_path",
        "PROMPTPATCH_CHECKPOINT_DB_PATH": "checkpoint_db_path",
        "PROMPTPATCH_DEMO_REPO": "demo_repo",
        "PROMPTPATCH_MODE": "mode",
    }
    for name, field in names.items():
        value = env.get(name)
        if value is not None and value.strip():
            values[field] = value
    try:
        return Settings(**values)
    except ValidationError:
        # Never echo environment values, including values put in the wrong field.
        raise ConfigurationError(
            "Invalid configuration. PROMPTPATCH_MODE must be live or replay; "
            "check configured paths and values locally."
        ) from None
