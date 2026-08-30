"""Contained workspace path resolution."""

from __future__ import annotations

from pathlib import Path

from .models import ForgeSettings, RunContext, Target


class UnsafePathError(ValueError):
    """Raised when a resolved workspace path escapes its configured root."""


class WorkspacePaths:
    """Resolve the fixed ROOT/workspace/domain/capability layout safely."""

    def __init__(self, settings: ForgeSettings) -> None:
        self._settings = settings

    @property
    def root(self) -> Path:
        return self._settings.root

    def _validate_candidate(self, candidate: Path, *, strict: bool) -> Path:
        current = self.root
        for component in candidate.relative_to(self.root).parts:
            current /= component
            if current.is_symlink() or current.is_junction():
                raise UnsafePathError(
                    "workspace paths must not contain symbolic links or junctions"
                )

        resolved = candidate.resolve(strict=strict)
        try:
            resolved.relative_to(self.root)
        except ValueError as error:
            raise UnsafePathError("resolved path is outside the configured root") from error
        if str(resolved) != str(candidate):
            raise UnsafePathError("workspace path must use its canonical identity")
        return candidate

    def _contained(self, *components: str) -> Path:
        candidate = self.root.joinpath(*components)
        return self._validate_candidate(candidate, strict=False)

    def workspace_directory(self) -> Path:
        return self._contained(self._settings.workspace)

    def target_directory(self, target: Target) -> Path:
        return self._contained(
            self._settings.workspace,
            target.domain,
            target.capability,
        )

    def run_directory(self, context: RunContext) -> Path:
        return self._contained(
            self._settings.workspace,
            context.target.domain,
            context.target.capability,
            "runs",
            context.run_id,
        )

    def prepare_run_directory(self, context: RunContext) -> Path:
        directory = self.run_directory(context)
        directory.mkdir(parents=True, exist_ok=True)
        return self._validate_candidate(directory, strict=True)

    def result_path(self, context: RunContext) -> Path:
        return self.run_directory(context) / self._settings.result_filename

    def manifest_path(self, context: RunContext) -> Path:
        return self.run_directory(context) / self._settings.manifest_filename
