"""Exercise system apply policy with no live system changes."""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

# The runner is an external dependency, not vendored into the system config repo.
root = Path(__file__).resolve().parents[1]
if os.environ.get("TOOLTJIK_REPO"):
    sys.path.insert(0, str(Path(os.environ["TOOLTJIK_REPO"]) / "apps/tjikup/src"))
else:
    for candidate in (root.parent / "tooltjik", Path.home() / "code/tooltjik"):
        if (candidate / "apps/tjikup/src").is_dir():
            sys.path.insert(0, str(candidate / "apps/tjikup/src"))
            break
spec = importlib.util.spec_from_file_location(
    "system_apply", root / "scripts/tjikup-apply.py"
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class ApplyTests(unittest.TestCase):
    def test_refresh_is_reported_once_and_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            config.write_text("before")

            def command(*args, **kwargs):
                self.assertEqual(kwargs["env"]["TJIKUP_QUIET_CONFIG"], "1")
                self.assertEqual(
                    args[0], ["wrapper", "--source", str(root / "etc"), "apply"]
                )
                config.write_text("after")

            with (
                patch.object(policy, "run_stream", side_effect=command) as run,
                patch.object(policy, "stage_result") as status,
            ):
                policy.apply(root, "wrapper", config)
            self.assertEqual(run.call_count, 2)
            status.assert_called_once_with(
                "CONFIG", "Chezetc", "configuration refreshed"
            )

    def test_unchanged_config_is_not_retried(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(policy, "run_stream") as run,
        ):
            root = Path(directory)
            policy.apply(root, "wrapper", root / "absent")
            run.assert_called_once()

    def test_failures_propagate_without_retry(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(
                policy, "run_stream", side_effect=policy.UpdateError("failed")
            ) as run,
        ):
            root = Path(directory)
            with self.assertRaises(policy.UpdateError):
                policy.apply(root, "wrapper", root / "absent")
            run.assert_called_once()

    def test_skip_conflicts_supplies_repeated_answers(self):
        with policy.conflict_input(["wrapper", "apply"], True) as (command, answers):
            self.assertEqual(command[-2:], ["--no-tty", "--interactive=false"])
            self.assertEqual(answers.readline(), b"skip\n")
            self.assertEqual(answers.readline(), b"skip\n")
