"""Deterministic JSON rendering and run manifest construction."""

from __future__ import annotations

import hashlib
import json

from .models import ForgeSettings, RunContext
from .validation import ValidationLayer
from .version import __version__


def render_json(value: object) -> str:
    """Render strict, stable, human-readable JSON with a final newline."""

    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def json_digest(value: object) -> str:
    return hashlib.sha256(render_json(value).encode("utf-8")).hexdigest()


def build_manifest(
    context: RunContext,
    settings: ForgeSettings,
    payload: dict[str, object],
    output: dict[str, object],
    capability_version: str,
) -> dict[str, object]:
    """Create a timestamp-free manifest so identical runs are byte-identical."""

    return {
        "artifacts": {
            "result": {
                "path": settings.result_filename,
                "sha256": json_digest(output),
            }
        },
        "input": {"sha256": json_digest(payload)},
        "generator": {
            "name": "e2e-platform-forge",
            "version": __version__,
        },
        "run": {
            "capability": context.target.capability,
            "capability_version": capability_version,
            "domain": context.target.domain,
            "id": context.run_id,
            "workspace": settings.workspace,
        },
        "schema_version": "1.0",
        "validation": [
            {"layer": layer.value, "status": "passed"}
            for layer in (
                ValidationLayer.INPUT_INTEGRITY,
                ValidationLayer.DOMAIN_RULES,
                ValidationLayer.PUBLICATION_READINESS,
            )
        ],
    }
