from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from e2e_platform_forge.demos import build_demo_registry, demo_input
from e2e_platform_forge.models import ForgeSettings, RunContext, Target
from e2e_platform_forge.orchestrator import Orchestrator
from e2e_platform_forge.registry import Capability
from e2e_platform_forge.validation import ValidationError, ValidationLayer


class RegistryAndValidationTests(unittest.TestCase):
    def test_registry_order_is_stable_and_duplicates_fail(self) -> None:
        registry = build_demo_registry()
        targets = [capability.target for capability in registry.capabilities()]
        self.assertEqual(targets, sorted(targets))

        with self.assertRaises(ValueError):
            registry.register(
                Capability(
                    target=Target("automation", "example"),
                    description="Duplicate synthetic example.",
                    handler=lambda payload: payload,
                )
            )

    def test_capability_version_uses_canonical_semantic_version(self) -> None:
        capability = Capability(
            target=Target("automation", "version-example"),
            description="Exercise semantic version validation.",
            handler=lambda payload: payload,
            version="12.3.0",
        )
        self.assertEqual(capability.version, "12.3.0")

        with self.assertRaises(ValueError):
            Capability(
                target=Target("automation", "invalid-version-example"),
                description="Reject a non-canonical semantic version.",
                handler=lambda payload: payload,
                version="01.2.3",
            )

    def _failure_layer(self, domain: str, payload: object) -> ValidationLayer:
        with TemporaryDirectory() as temporary_directory:
            orchestrator = Orchestrator(
                build_demo_registry(),
                ForgeSettings(Path(temporary_directory), "DEMO_WORKSPACE"),
            )
            with self.assertRaises(ValidationError) as raised:
                orchestrator.run(
                    RunContext(Target(domain, "example"), "EXAMPLE_RUN"),
                    payload,
                )
            return raised.exception.issues[0].layer

    def test_input_integrity_layer_rejects_wrong_shape(self) -> None:
        layer = self._failure_layer("automation", {"steps": "EXAMPLE_STEP"})
        self.assertEqual(layer, ValidationLayer.INPUT_INTEGRITY)

    def test_domain_rules_layer_rejects_duplicate_names(self) -> None:
        layer = self._failure_layer(
            "automation",
            {"steps": ["EXAMPLE_STEP", "EXAMPLE_STEP"]},
        )
        self.assertEqual(layer, ValidationLayer.DOMAIN_RULES)

    def test_publication_layer_rejects_unready_output(self) -> None:
        payload = demo_input("delivery")
        payload["items"][0]["ready"] = False
        layer = self._failure_layer("delivery", payload)
        self.assertEqual(layer, ValidationLayer.PUBLICATION_READINESS)


if __name__ == "__main__":
    unittest.main()
