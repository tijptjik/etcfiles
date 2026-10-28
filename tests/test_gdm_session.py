"""Exercise the client GDM session installer without touching system files."""
import configparser
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "etc/.chezmoiscripts/run_58-hyprland-gdm-session.fish.tmpl"
ENTRY = ROOT / "etc/.chezmoitemplates/hyprland-uwsm.desktop"


@unittest.skipUnless(
    all(shutil.which(name) for name in ("chezmoi", "fish", "desktop-file-validate")),
    "chezmoi, fish and desktop-file-validate are required",
)
class GdmSessionTests(unittest.TestCase):
    def test_client_session_installer(self):
        for host, client, deferred in (("li", True, False), ("li", True, True),
                                       ("fi", True, False), ("fi", True, True),
                                       ("si", False, False)):
            with self.subTest(host=host, deferred=deferred), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                config = work / "config.toml"
                config.write_text("[data]\nisClient = " + str(client).lower() + "\n")
                rendered = subprocess.run(
                    ["chezmoi", "--config", str(config), "--source", str(ROOT), "execute-template"],
                    input=HOOK.read_text(), text=True, capture_output=True, check=True,
                ).stdout
                script = work / "hook.fish"
                script.write_text(rendered)
                subprocess.run(["fish", "--no-config", "--no-execute", str(script)], check=True)
                # Only the expected install may pass through this fake sudo.
                sudo = work / "sudo"
                sudo.write_text("""#!/usr/bin/python3
import os
import subprocess
import sys
assert sys.argv[1:7] == ['-n', 'install', '-D', '-C', '-m', '644'], sys.argv
assert sys.argv[-1] == '/usr/local/share/wayland-sessions/hyprland-uwsm.desktop', sys.argv
raise SystemExit(subprocess.call(['/usr/bin/install', '-D', '-C', '-m', '644', sys.argv[-2], os.environ['TEST_SESSION_TARGET']]))
""")
                sudo.chmod(0o755)
                target = work / "installed/hyprland-uwsm.desktop"
                env = dict(os.environ, PATH=str(work) + os.pathsep + os.environ["PATH"],
                           TEST_SESSION_TARGET=str(target),
                           FLEET_DEFER_SYSTEM_HOOKS="1" if deferred else "0")
                command = ["fish", "--no-config", str(script)]
                subprocess.run(command, env=env, check=True)
                if not client or deferred:
                    self.assertFalse(target.exists())
                    continue
                self.assertEqual(target.read_bytes(), ENTRY.read_bytes())
                parsed = configparser.ConfigParser()
                parsed.read(target)
                argv = shlex.split(parsed["Desktop Entry"]["Exec"])
                self.assertEqual(argv[:4], ["uwsm", "start", "-g", "-1"])
                self.assertEqual(argv[4:], ["-e", "-D", "Hyprland", "hyprland.desktop"])
                before = target.stat().st_mtime_ns
                subprocess.run(command, env=env, check=True)
                self.assertEqual(target.stat().st_mtime_ns, before)
