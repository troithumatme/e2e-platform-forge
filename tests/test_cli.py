from __future__ import annotations

import json
import os
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from e2e_platform_forge.cli import main


class CliTests(unittest.TestCase):
    def test_list_and_sample_emit_json(self) -> None:
        listed = StringIO()
        sampled = StringIO()

        self.assertEqual(main(["list"], stdout=listed), 0)
        self.assertEqual(
            [item["domain"] for item in json.loads(listed.getvalue())["capabilities"]],
            ["automation", "delivery", "governance", "intelligence"],
        )
        self.assertEqual(main(["sample", "--domain", "automation"], stdout=sampled), 0)
        self.assertEqual(
            json.loads(sampled.getvalue()),
            {"steps": ["EXAMPLE_PREPARE", "EXAMPLE_COMPLETE"]},
        )

    def test_sample_can_write_portable_utf8_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "nested" / "sample.json"

            self.assertEqual(
                main(
                    [
                        "sample",
                        "--domain",
                        "governance",
                        "--output",
                        str(output_path),
                    ]
                ),
                0,
            )
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8"))["checks"][0]["name"],
                "EXAMPLE_CHECK_A",
            )

    def test_run_publishes_artifacts(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_path = root / "EXAMPLE_INPUT.json"
            input_path.write_text(
                '{"steps":["EXAMPLE_PREPARE","EXAMPLE_COMPLETE"]}',
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()

            exit_code = main(
                [
                    "run",
                    "--root",
                    str(root),
                    "--workspace",
                    "DEMO_WORKSPACE",
                    "--domain",
                    "automation",
                    "--run-id",
                    "EXAMPLE_RUN",
                    "--input",
                    str(input_path),
                ],
                stdout=stdout,
                stderr=stderr,
            )

            summary = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(summary["status"], "published")
            self.assertTrue(Path(summary["result"]).is_file())
            self.assertTrue(Path(summary["manifest"]).is_file())

    def test_run_reports_structured_validation_error(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_path = root / "EXAMPLE_INPUT.json"
            input_path.write_text('{"steps":[]}', encoding="utf-8")
            stderr = StringIO()

            exit_code = main(
                [
                    "run",
                    "--root",
                    str(root),
                    "--workspace",
                    "DEMO_WORKSPACE",
                    "--domain",
                    "automation",
                    "--run-id",
                    "EXAMPLE_RUN",
                    "--input",
                    str(input_path),
                ],
                stdout=StringIO(),
                stderr=stderr,
            )

            error = json.loads(stderr.getvalue())
            self.assertEqual(exit_code, 2)
            self.assertEqual(error["error"], "validation_failed")
            self.assertEqual(error["issues"][0]["layer"], "domain_rules")

    def test_run_reads_only_portable_root_settings_from_env_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            output_root = base / "artifacts"
            env_path = base / ".env"
            input_path = base / "input.json"
            env_path.write_text(
                f"FORGE_ROOT={output_root}\nDEFAULT_WORKSPACE=DEMO_ENV\n",
                encoding="utf-8",
            )
            input_path.write_text('{"steps":["EXAMPLE_STEP"]}', encoding="utf-8")
            stdout = StringIO()

            with patch.dict(os.environ, {}, clear=True):
                exit_code = main(
                    [
                        "run",
                        "--env-file",
                        str(env_path),
                        "--domain",
                        "automation",
                        "--run-id",
                        "ENV_RUN",
                        "--input",
                        str(input_path),
                    ],
                    stdout=stdout,
                    stderr=StringIO(),
                )

            self.assertEqual(exit_code, 0)
            result_path = Path(json.loads(stdout.getvalue())["result"])
            self.assertTrue(result_path.is_file())
            self.assertTrue(result_path.is_relative_to(output_root / "DEMO_ENV"))


if __name__ == "__main__":
    unittest.main()
