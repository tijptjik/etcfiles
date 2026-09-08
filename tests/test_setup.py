"""Exercise setup with isolated paths and stubbed package/render commands."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SETUP = Path(__file__).resolve().parents[1] / "setup.sh"
HARNESS = r'''
sudo() { return 0; }
uv() { return 0; }
chezmoi() { printf 'rendered configuration\n'; return "$RENDER_STATUS"; }
export -f sudo uv chezmoi
bash "$1"
'''


class SetupTests(unittest.TestCase):
    def test_render_replaces_config_only_on_success(self):
        for status in (0, 1):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / ".tools/chezetc").mkdir(parents=True)
                config = root / ".config/chezetc/chezetc.toml"
                config.parent.mkdir(parents=True)
                config.write_text("existing configuration\n")
                result = subprocess.run(
                    ["bash", "-c", HARNESS, "test-setup", str(SETUP)],
                    env={**os.environ, "HOME": str(root), "RENDER_STATUS": str(status)},
                    text=True, capture_output=True, timeout=10,
                )
                self.assertEqual(result.returncode, status, result.stdout + result.stderr)
                self.assertEqual(
                    config.read_text(),
                    "rendered configuration\n" if status == 0 else "existing configuration\n",
                )
                self.assertEqual(list(config.parent.glob(".chezetc.toml.*")), [])
                if status == 0:
                    self.assertEqual(config.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
