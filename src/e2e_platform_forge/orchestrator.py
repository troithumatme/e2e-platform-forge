"""Fixed-order validation, execution, and artifact publication."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .manifest import build_manifest, render_json
from .models import ForgeSettings, RunContext
from .paths import WorkspacePaths
from .registry import CapabilityRegistry
from .validation import (
    ValidationError,
    ValidationIssue,
    ValidationLayer,
    apply_validators,
    json_object_findings,
)


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """Published artifacts and their normalized JSON values."""

    context: RunContext
    output: dict[str, object]
    manifest: dict[str, object]
    result_path: Path
    manifest_path: Path


class Orchestrator:
    """Execute registered capabilities through the three validation layers."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        settings: ForgeSettings,
    ) -> None:
        self._registry = registry
        self._settings = settings
        self._paths = WorkspacePaths(settings)

    @staticmethod
    def _normalized(value: dict[str, object]) -> dict[str, object]:
        # A strict JSON round trip prevents handlers from mutating caller-owned
        # objects and normalizes mappings to ordinary JSON containers.
        normalized = json.loads(render_json(value))
        if not isinstance(normalized, dict):
            raise TypeError("normalized JSON root must be an object")
        return normalized

    @staticmethod
    def _raise_if_any(issues: tuple[ValidationIssue, ...]) -> None:
        if issues:
            raise ValidationError(issues)

    @staticmethod
    def _assert_publishable(path: Path, content: str) -> None:
        """Reject a conflicting artifact before any output is written."""

        if path.exists():
            if (
                path.is_symlink()
                or not path.is_file()
                or path.read_text(encoding="utf-8") != content
            ):
                raise FileExistsError(
                    f"run artifact already exists with different content: {path}"
                )

    @staticmethod
    def _publish(path: Path, content: str) -> None:
        """Claim one artifact exclusively or verify the concurrent winner."""

        encoded = content.encode("utf-8")
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            if path.is_symlink() or not path.is_file() or path.read_bytes() != encoded:
                raise FileExistsError(
                    f"run artifact already exists with different content: {path}"
                ) from None
            return

        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            path.unlink(missing_ok=True)
            raise

    def run(self, context: RunContext, payload: object) -> RunOutcome:
        capability = self._registry.resolve(context.target)

        integrity_issues = apply_validators(
            ValidationLayer.INPUT_INTEGRITY,
            payload,
            (json_object_findings,),
        )
        self._raise_if_any(integrity_issues)
        integrity_issues = apply_validators(
            ValidationLayer.INPUT_INTEGRITY,
            payload,
            capability.input_integrity_validators,
        )
        self._raise_if_any(integrity_issues)

        domain_issues = apply_validators(
            ValidationLayer.DOMAIN_RULES,
            payload,
            capability.domain_rule_validators,
        )
        self._raise_if_any(domain_issues)

        # Reject path aliases before a capability can perform any work. The
        # path is checked again immediately before publication to catch drift.
        self._paths.run_directory(context)

        if not isinstance(payload, dict):
            raise TypeError("validated payload root must be an object")
        normalized_payload = self._normalized(payload)
        output = capability.handler(normalized_payload)

        publication_issues = apply_validators(
            ValidationLayer.PUBLICATION_READINESS,
            output,
            (json_object_findings,),
        )
        self._raise_if_any(publication_issues)
        publication_issues = apply_validators(
            ValidationLayer.PUBLICATION_READINESS,
            output,
            capability.publication_readiness_validators,
        )
        self._raise_if_any(publication_issues)

        normalized_output = self._normalized(output)
        manifest = build_manifest(
            context,
            self._settings,
            normalized_payload,
            normalized_output,
            capability.version,
        )

        run_directory = self._paths.prepare_run_directory(context)
        result_path = run_directory / self._settings.result_filename
        manifest_path = run_directory / self._settings.manifest_filename
        artifacts = (
            (result_path, render_json(normalized_output)),
            (manifest_path, render_json(manifest)),
        )
        for path, content in artifacts:
            self._assert_publishable(path, content)
        for path, content in artifacts:
            self._publish(path, content)

        return RunOutcome(
            context=context,
            output=normalized_output,
            manifest=manifest,
            result_path=result_path,
            manifest_path=manifest_path,
        )
