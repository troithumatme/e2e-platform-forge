"""Command-line interface for discovery, samples, and capability runs."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from .demos import build_demo_registry, demo_domains, demo_input
from .environment import resolve_settings
from .manifest import render_json
from .models import RunContext, Target
from .orchestrator import Orchestrator
from .validation import ValidationError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="e2e-platform-forge")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="list registered synthetic capabilities")

    sample = commands.add_parser("sample", help="write a synthetic JSON input to stdout")
    sample.add_argument("--domain", required=True, choices=demo_domains())
    sample.add_argument("--output", type=Path, help="write to a UTF-8 file instead")

    run = commands.add_parser("run", help="validate, execute, and publish a JSON run")
    run.add_argument("--root", type=Path, help="override FORGE_ROOT")
    run.add_argument("--workspace", help="override DEFAULT_WORKSPACE")
    run.add_argument("--env-file", type=Path, default=Path(".env"))
    run.add_argument("--domain", required=True, choices=demo_domains())
    run.add_argument("--capability", default="example")
    run.add_argument("--run-id", required=True)
    run.add_argument("--input", required=True, type=Path)
    return parser


def _error_payload(error: Exception) -> dict[str, object]:
    if isinstance(error, ValidationError):
        return {
            "error": "validation_failed",
            "issues": [issue.as_dict() for issue in error.issues],
        }
    return {"error": type(error).__name__, "message": str(error)}


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output_stream = stdout if stdout is not None else sys.stdout
    error_stream = stderr if stderr is not None else sys.stderr
    arguments = _parser().parse_args(argv)
    registry = build_demo_registry()

    if arguments.command == "list":
        output_stream.write(
            render_json(
                {
                    "capabilities": [
                        {
                            "capability": item.target.capability,
                            "description": item.description,
                            "domain": item.target.domain,
                        }
                        for item in registry.capabilities()
                    ]
                }
            )
        )
        return 0

    if arguments.command == "sample":
        sample_text = render_json(demo_input(arguments.domain))
        if arguments.output is None:
            output_stream.write(sample_text)
            return 0
        try:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(sample_text, encoding="utf-8", newline="\n")
        except OSError as error:
            error_stream.write(render_json(_error_payload(error)))
            return 2
        return 0

    try:
        payload = json.loads(arguments.input.read_text(encoding="utf-8"))
        settings = resolve_settings(
            root=arguments.root,
            workspace=arguments.workspace,
            env_file=arguments.env_file,
        )
        context = RunContext(
            Target(arguments.domain, arguments.capability),
            arguments.run_id,
        )
        outcome = Orchestrator(registry, settings).run(context, payload)
    except (json.JSONDecodeError, LookupError, OSError, TypeError, ValueError) as error:
        error_stream.write(render_json(_error_payload(error)))
        return 2

    output_stream.write(
        render_json(
            {
                "manifest": str(outcome.manifest_path),
                "result": str(outcome.result_path),
                "status": "published",
            }
        )
    )
    return 0
