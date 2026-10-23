"""Test user-context dispatch and COPR selection without package changes."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class DesktopUserTests(unittest.TestCase):
    def test_root_dispatches_to_desktop_user_with_correct_home_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, body in {
                'id': 'if [ "$#" = 1 ]; then echo 0; else echo 1000; fi',
                'getent': 'printf "desktop:x:1000:1000::%s:/bin/fish\\n" "$TEST_HOME"',
                'sudo': 'printf "%s\\n" "$@"; cat >/dev/null',
            }.items():
                path = root/name
                path.write_text('#!/bin/sh\n'+body+'\n')
                path.chmod(0o755)
            script = root/'hook.fish'
            script.write_text((REPO/'etc/.chezmoihelpers/desktop-user.fish').read_text()+'\necho SHOULD_NOT_RUN_AS_ROOT\n')
            result = subprocess.run(['fish', '--no-config', str(script)],
                env={**os.environ, 'PATH':f'{root}:/usr/bin:/bin', 'SUDO_USER':'desktop', 'TEST_HOME':tmp},
                capture_output=True,text=True,check=True)
            self.assertIn('-u\ndesktop\n', result.stdout)
            self.assertIn(f'XDG_CONFIG_HOME={tmp}/.config', result.stdout)
            self.assertIn('/usr/bin/fish', result.stdout)
            self.assertNotIn('SHOULD_NOT_RUN_AS_ROOT', result.stdout)

    def test_root_without_desktop_user_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'id').write_text('#!/bin/sh\necho 0\n');(root/'id').chmod(0o755)
            result=subprocess.run(['fish','--no-config',str(REPO/'etc/.chezmoihelpers/desktop-user.fish')],
                env={**os.environ,'PATH':f'{root}:/usr/bin:/bin','SUDO_USER':'root'},capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertIn('Cannot identify',result.stderr)
