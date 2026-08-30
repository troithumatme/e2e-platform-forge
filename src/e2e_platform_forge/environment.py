"""Small, explicit environment boundary for local filesystem settings."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

from .models import ForgeSettings


_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SUPPORTED_KEYS = frozenset({"DEFAULT_WORKSPACE", "FORGE_ROOT"})


def read_env_file(path: Path) -> dict[str, str]:
    """Read supported values from a simple UTF-8 ``.env`` file.

    Unknown keys are ignored so credentials can remain available to private
    adapters without entering the public core. Shell expansion is deliberately
    unsupported; values are treated as literal text.
    """

    if not path.exists():
        return {}
    if not path.is_file():
        raise ValueError(f"environment path is not a file: {path}")

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        if "=" not in line:
            raise ValueError(f"invalid .env assignment on line {line_number}")

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not _KEY_PATTERN.fullmatch(key):
            raise ValueError(f"invalid .env key on line {line_number}")
        if key not in _SUPPORTED_KEYS:
            continue

        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def resolve_settings(
    *,
    root: Path | None,
    workspace: str | None,
    env_file: Path,
    environ: Mapping[str, str] | None = None,
) -> ForgeSettings:
    """Resolve settings with CLI, process environment, then file precedence."""

    file_values = read_env_file(env_file)
    process_values = os.environ if environ is None else environ

    root_value = (
        str(root)
        if root is not None
        else process_values.get("FORGE_ROOT") or file_values.get("FORGE_ROOT")
    )
    if not root_value:
        raise ValueError(
            "FORGE_ROOT is required; pass --root or set it in the environment or .env"
        )

    workspace_value = (
        workspace
        or process_values.get("DEFAULT_WORKSPACE")
        or file_values.get("DEFAULT_WORKSPACE")
        or "DEMO"
    )
    return ForgeSettings(Path(root_value), workspace_value)
