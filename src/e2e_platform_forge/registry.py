"""Capability definitions and deterministic registration."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from .models import Target
from .validation import Validator


Handler = Callable[[dict[str, object]], dict[str, object]]
_VERSION_PART = r"(?:0|[1-9][0-9]*)"
_VERSION_PATTERN = re.compile(rf"^{_VERSION_PART}\.{_VERSION_PART}\.{_VERSION_PART}$")


@dataclass(frozen=True, slots=True)
class Capability:
    """An executable handler and its validators."""

    target: Target
    description: str
    handler: Handler
    version: str = "1.0.0"
    input_integrity_validators: tuple[Validator, ...] = ()
    domain_rule_validators: tuple[Validator, ...] = ()
    publication_readiness_validators: tuple[Validator, ...] = ()

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("capability description must not be empty")
        if not _VERSION_PATTERN.fullmatch(self.version):
            raise ValueError("capability version must use MAJOR.MINOR.PATCH")


class CapabilityRegistry:
    """A registry with duplicate protection and stable iteration order."""

    def __init__(self) -> None:
        self._capabilities: dict[Target, Capability] = {}

    def register(self, capability: Capability) -> None:
        if capability.target in self._capabilities:
            raise ValueError(
                "capability is already registered: "
                f"{capability.target.domain}/{capability.target.capability}"
            )
        self._capabilities[capability.target] = capability

    def resolve(self, target: Target) -> Capability:
        try:
            return self._capabilities[target]
        except KeyError as error:
            raise LookupError(
                f"unknown capability: {target.domain}/{target.capability}"
            ) from error

    def capabilities(self) -> tuple[Capability, ...]:
        return tuple(
            self._capabilities[target] for target in sorted(self._capabilities)
        )
