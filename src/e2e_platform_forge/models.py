"""Immutable configuration and execution context models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_RESERVED_DEVICE_NAMES = {
    "AUX",
    "CLOCK$",
    "CON",
    "NUL",
    "PRN",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def validate_component(value: str, label: str) -> str:
    """Return a path-safe single component or raise ``ValueError``.

    The intentionally small ASCII alphabet behaves consistently across common
    filesystems and prevents absolute paths, traversal, separators, and drive
    designators from entering the workspace layout.
    """

    if not isinstance(value, str) or not _SAFE_COMPONENT.fullmatch(value):
        raise ValueError(
            f"{label} must be 1-64 ASCII letters, numbers, dots, underscores, "
            "or hyphens, and must start with a letter or number"
        )
    if value.endswith("."):
        raise ValueError(f"{label} must not end with a dot")
    if value.split(".", 1)[0].upper() in _RESERVED_DEVICE_NAMES:
        raise ValueError(f"{label} is reserved on supported filesystems")
    return value


def validate_lower_component(value: str, label: str) -> str:
    """Require one lowercase identity to avoid cross-filesystem aliases."""

    normalized = validate_component(value, label)
    if normalized != normalized.lower():
        raise ValueError(f"{label} must be lowercase")
    return normalized


def validate_upper_component(value: str, label: str) -> str:
    """Require one uppercase identity to avoid cross-filesystem aliases."""

    normalized = validate_component(value, label)
    if normalized != normalized.upper():
        raise ValueError(f"{label} must be uppercase")
    return normalized


@dataclass(frozen=True, slots=True, order=True)
class Target:
    """A registered domain and capability pair."""

    domain: str
    capability: str

    def __post_init__(self) -> None:
        validate_lower_component(self.domain, "domain")
        validate_lower_component(self.capability, "capability")


@dataclass(frozen=True, slots=True)
class RunContext:
    """The caller-supplied identity of one deterministic run."""

    target: Target
    run_id: str

    def __post_init__(self) -> None:
        validate_upper_component(self.run_id, "run_id")


@dataclass(frozen=True, slots=True)
class ForgeSettings:
    """Explicit filesystem settings for a workspace.

    ``root`` is normalized once. Every remaining path component is validated
    before it can be joined beneath that root.
    """

    root: Path
    workspace: str
    result_filename: str = "result.json"
    manifest_filename: str = "manifest.json"

    def __post_init__(self) -> None:
        normalized_root = Path(self.root).expanduser().resolve(strict=False)
        if normalized_root.exists() and not normalized_root.is_dir():
            raise ValueError("root must identify a directory")
        object.__setattr__(self, "root", normalized_root)
        validate_upper_component(self.workspace, "workspace")
        validate_component(self.result_filename, "result_filename")
        validate_component(self.manifest_filename, "manifest_filename")
        if self.result_filename.casefold() == self.manifest_filename.casefold():
            raise ValueError(
                "result_filename and manifest_filename must be different on "
                "case-insensitive filesystems"
            )
