from __future__ import annotations

import hashlib
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import Mock, patch

from e2e_platform_forge.demos import build_demo_registry, demo_domains, demo_input
from e2e_platform_forge.manifest import json_digest
from e2e_platform_forge.models import ForgeSettings, RunContext, Target
from e2e_platform_forge.orchestrator import Orchestrator
from e2e_platform_forge.paths import UnsafePathError
from e2e_platform_forge.registry import Capability, CapabilityRegistry


class OrchestratorTests(unittest.TestCase):
    def test_each_synthetic_domain_writes_json_result_and_manifest(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            settings = ForgeSettings(Path(temporary_directory), "DEMO_WORKSPACE")
            orchestrator = Orchestrator(build_demo_registry(), settings)

            for domain in demo_domains():
                with self.subTest(domain=domain):
                    outcome = orchestrator.run(
                        RunContext(Target(domain, "example"), "EXAMPLE_RUN"),
                        demo_input(domain),
                    )
                    result_bytes = outcome.result_path.read_bytes()
                    manifest = json.loads(outcome.manifest_path.read_text(encoding="utf-8"))

                    self.assertEqual(json.loads(result_bytes), outcome.output)
                    self.assertEqual(outcome.output["domain"], domain)
                    self.assertEqual(outcome.output["example"], "DEMO")
                    self.assertEqual(
                        manifest["artifacts"]["result"]["sha256"],
                        hashlib.sha256(result_bytes).hexdigest(),
                    )
                    self.assertEqual(
                        [entry["layer"] for entry in manifest["validation"]],
                        [
                            "input_integrity",
                            "domain_rules",
                            "publication_readiness",
                        ],
                    )
                    self.assertEqual(
                        manifest["generator"],
                        {"name": "e2e-platform-forge", "version": "0.1.0"},
                    )
                    self.assertEqual(manifest["run"]["capability_version"], "1.0.0")

    def test_repeated_run_is_byte_deterministic(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            settings = ForgeSettings(Path(temporary_directory), "DEMO_WORKSPACE")
            orchestrator = Orchestrator(build_demo_registry(), settings)
            context = RunContext(Target("intelligence", "example"), "EXAMPLE_RUN")

            first = orchestrator.run(context, demo_input("intelligence"))
            first_result = first.result_path.read_bytes()
            first_manifest = first.manifest_path.read_bytes()
            second = orchestrator.run(context, demo_input("intelligence"))

            self.assertEqual(second.result_path.read_bytes(), first_result)
            self.assertEqual(second.manifest_path.read_bytes(), first_manifest)

    def test_run_id_cannot_overwrite_different_artifacts(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            settings = ForgeSettings(Path(temporary_directory), "DEMO_WORKSPACE")
            orchestrator = Orchestrator(build_demo_registry(), settings)
            context = RunContext(Target("automation", "example"), "EXAMPLE_RUN")
            orchestrator.run(context, {"steps": ["EXAMPLE_A"]})

            with self.assertRaises(FileExistsError):
                orchestrator.run(context, {"steps": ["EXAMPLE_B"]})

    def test_path_safety_precedes_capability_execution(self) -> None:
        target = Target("automation", "path-safety-example")
        handler = Mock(return_value={"status": "READY"})
        registry = CapabilityRegistry()
        registry.register(
            Capability(
                target=target,
                description="Verify path safety ordering.",
                handler=handler,
            )
        )
        with TemporaryDirectory() as temporary_directory:
            orchestrator = Orchestrator(
                registry,
                ForgeSettings(Path(temporary_directory), "DEMO_WORKSPACE"),
            )
            with (
                patch.object(
                    orchestrator._paths,
                    "run_directory",
                    side_effect=UnsafePathError("unsafe alias"),
                ),
                self.assertRaises(UnsafePathError),
            ):
                orchestrator.run(
                    RunContext(target, "EXAMPLE_RUN"),
                    {"value": "EXAMPLE"},
                )

        handler.assert_not_called()

    def test_conflicting_partial_run_fails_before_creating_result(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            settings = ForgeSettings(Path(temporary_directory), "DEMO_WORKSPACE")
            orchestrator = Orchestrator(build_demo_registry(), settings)
            context = RunContext(Target("automation", "example"), "EXAMPLE_RUN")
            run_directory = (
                settings.root
                / settings.workspace
                / "automation"
                / "example"
                / "runs"
                / context.run_id
            )
            run_directory.mkdir(parents=True)
            manifest_path = run_directory / settings.manifest_filename
            manifest_path.write_text("conflict\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                orchestrator.run(context, {"steps": ["EXAMPLE_A"]})

            self.assertFalse((run_directory / settings.result_filename).exists())
            self.assertEqual(manifest_path.read_text(encoding="utf-8"), "conflict\n")

    def test_artifact_symlink_cannot_write_outside_root(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            settings = ForgeSettings(base / "root", "DEMO_WORKSPACE")
            orchestrator = Orchestrator(build_demo_registry(), settings)
            context = RunContext(Target("automation", "example"), "EXAMPLE_RUN")
            run_directory = (
                settings.root
                / settings.workspace
                / "automation"
                / "example"
                / "runs"
                / context.run_id
            )
            run_directory.mkdir(parents=True)
            external = base / "outside.json"
            result_path = run_directory / settings.result_filename
            try:
                result_path.symlink_to(external)
            except OSError as error:
                self.skipTest(f"file symlinks are unavailable: {error}")

            with self.assertRaises(FileExistsError):
                orchestrator.run(context, {"steps": ["EXAMPLE_A"]})

            self.assertFalse(external.exists())
            self.assertFalse((run_directory / settings.manifest_filename).exists())

    def test_concurrent_conflicting_run_has_one_consistent_winner(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            def handler(payload: dict[str, object]) -> dict[str, object]:
                return {"domain": "automation", "value": payload["value"]}

            publication_barrier = Barrier(2)

            class SynchronizedOrchestrator(Orchestrator):
                @staticmethod
                def _assert_publishable(path: Path, content: str) -> None:
                    Orchestrator._assert_publishable(path, content)
                    if path.name == "manifest.json":
                        publication_barrier.wait(timeout=2)

            target = Target("automation", "concurrent-example")
            registry = CapabilityRegistry()
            registry.register(
                Capability(
                    target=target,
                    description="Exercise concurrent publication.",
                    handler=handler,
                )
            )
            settings = ForgeSettings(Path(temporary_directory), "DEMO_WORKSPACE")
            orchestrator = SynchronizedOrchestrator(registry, settings)
            context = RunContext(target, "EXAMPLE_RUN")
            payloads = ({"value": "EXAMPLE_A"}, {"value": "EXAMPLE_B"})

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(orchestrator.run, context, payload)
                    for payload in payloads
                ]
            successes = [future.result() for future in futures if future.exception() is None]
            failures = [future.exception() for future in futures if future.exception()]

            self.assertEqual(len(successes), 1)
            self.assertEqual(len(failures), 1)
            self.assertIsInstance(failures[0], FileExistsError)
            winner = successes[0]
            published_result = json.loads(winner.result_path.read_text(encoding="utf-8"))
            published_manifest = json.loads(
                winner.manifest_path.read_text(encoding="utf-8")
            )
            self.assertEqual(published_result, winner.output)
            winning_payload = next(
                payload for payload in payloads if payload["value"] == winner.output["value"]
            )
            self.assertEqual(
                published_manifest["input"]["sha256"],
                json_digest(winning_payload),
            )


if __name__ == "__main__":
    unittest.main()
