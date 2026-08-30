from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory

from e2e_platform_forge.models import ForgeSettings, RunContext, Target
from e2e_platform_forge.paths import UnsafePathError, WorkspacePaths


class ModelAndPathTests(unittest.TestCase):
    def test_target_and_run_context_are_immutable(self) -> None:
        target = Target("automation", "example")
        context = RunContext(target, "EXAMPLE_RUN")

        with self.assertRaises(FrozenInstanceError):
            target.domain = "delivery"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            context.run_id = "CHANGED"  # type: ignore[misc]

    def test_unsafe_components_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Target("../escape", "example")
        with self.assertRaises(ValueError):
            Target("automation", "C:drive")
        with self.assertRaises(ValueError):
            ForgeSettings(Path.cwd(), "../escape")
        with self.assertRaises(ValueError):
            RunContext(Target("automation", "example"), "..")
        with self.assertRaises(ValueError):
            Target("Automation", "example")
        with self.assertRaises(ValueError):
            ForgeSettings(Path.cwd(), "demo_workspace")
        with self.assertRaises(ValueError):
            RunContext(Target("automation", "example"), "example_run")

    def test_paths_follow_the_contained_layout(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            settings = ForgeSettings(root, "DEMO_WORKSPACE")
            context = RunContext(Target("automation", "example"), "EXAMPLE_RUN")
            paths = WorkspacePaths(settings)

            expected = (
                root.resolve()
                / "DEMO_WORKSPACE"
                / "automation"
                / "example"
                / "runs"
                / "EXAMPLE_RUN"
            )
            self.assertEqual(paths.run_directory(context), expected)
            self.assertEqual(paths.prepare_run_directory(context), expected)
            self.assertTrue(expected.is_dir())

    def test_artifact_filenames_must_be_distinct(self) -> None:
        with self.assertRaises(ValueError):
            ForgeSettings(
                Path.cwd(),
                "DEMO_WORKSPACE",
                result_filename="same.json",
                manifest_filename="same.json",
            )
        with self.assertRaises(ValueError):
            ForgeSettings(
                Path.cwd(),
                "DEMO_WORKSPACE",
                result_filename="Result.json",
                manifest_filename="result.json",
            )

    def test_run_directory_alias_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            settings = ForgeSettings(Path(temporary_directory), "DEMO_WORKSPACE")
            context = RunContext(Target("automation", "example"), "EXAMPLE_RUN")
            paths = WorkspacePaths(settings)
            runs_directory = (
                settings.root
                / settings.workspace
                / context.target.domain
                / context.target.capability
                / "runs"
            )
            target_directory = runs_directory / "EXISTING_RUN"
            target_directory.mkdir(parents=True)
            alias_directory = runs_directory / context.run_id
            try:
                alias_directory.symlink_to(target_directory, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory symlinks are unavailable: {error}")

            with self.assertRaises(UnsafePathError):
                paths.prepare_run_directory(context)


if __name__ == "__main__":
    unittest.main()
