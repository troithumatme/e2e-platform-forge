"""Validation primitives shared by capabilities and the orchestrator."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum


class ValidationLayer(StrEnum):
    INPUT_INTEGRITY = "input_integrity"
    DOMAIN_RULES = "domain_rules"
    PUBLICATION_READINESS = "publication_readiness"


@dataclass(frozen=True, slots=True, order=True)
class Finding:
    """A layer-independent finding returned by a validator."""

    path: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A finding associated with one of the three framework layers."""

    layer: ValidationLayer
    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "layer": self.layer.value,
            "path": self.path,
            "code": self.code,
            "message": self.message,
        }


Validator = Callable[[object], Iterable[Finding]]


class ValidationError(ValueError):
    """Raised with deterministic, structured issues when a layer fails."""

    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        summary = "; ".join(
            f"{issue.layer.value}:{issue.code}@{issue.path}" for issue in self.issues
        )
        super().__init__(summary or "validation failed")


def apply_validators(
    layer: ValidationLayer,
    subject: object,
    validators: Iterable[Validator],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    for validator in validators:
        findings = sorted(validator(subject))
        issues.extend(
            ValidationIssue(
                layer=layer,
                path=finding.path,
                code=finding.code,
                message=finding.message,
            )
            for finding in findings
        )
    return tuple(issues)


def json_object_findings(subject: object) -> tuple[Finding, ...]:
    """Validate strict, finite JSON with a JSON object at its root."""

    if not isinstance(subject, dict):
        return (Finding("$", "json_object_required", "value must be a JSON object"),)

    findings: list[Finding] = []

    def visit(value: object, path: str, ancestors: frozenset[int]) -> None:
        if value is None or isinstance(value, str | bool | int):
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                findings.append(
                    Finding(path, "finite_number_required", "JSON numbers must be finite")
                )
            return
        if isinstance(value, dict):
            identity = id(value)
            if identity in ancestors:
                findings.append(Finding(path, "cycle_detected", "JSON values must not cycle"))
                return
            if any(not isinstance(key, str) for key in value):
                findings.append(
                    Finding(path, "string_keys_required", "JSON object keys must be strings")
                )
                return
            next_ancestors = ancestors | {identity}
            for key in sorted(value):
                child_path = f"{path}.{key}" if key else f"{path}['']"
                visit(value[key], child_path, next_ancestors)
            return
        if isinstance(value, list):
            identity = id(value)
            if identity in ancestors:
                findings.append(Finding(path, "cycle_detected", "JSON values must not cycle"))
                return
            next_ancestors = ancestors | {identity}
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]", next_ancestors)
            return
        findings.append(
            Finding(path, "json_type_required", "value is not a supported JSON type")
        )

    visit(subject, "$", frozenset())
    return tuple(sorted(findings))
