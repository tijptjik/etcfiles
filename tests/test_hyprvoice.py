"""Hyprvoice installation must fail before touching the live binary."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / 'etc/.chezmoiscripts/run_54-install-hyprvoice.fish.tmpl').read_text()
FUNCTION = TEXT[TEXT.index('function install_hyprvoice'):TEXT.index('\nstep_run_quiet')]


class HyprvoiceInstallerTests(unittest.TestCase):
    def run_hook(self, stubs):
        return subprocess.run(['fish', '--no-config', '-c', FUNCTION + '\n' + stubs + '\ninstall_hyprvoice'], capture_output=True, text=True)

    def test_unsupported_architecture_does_not_install(self):
        result = self.run_hook('function uname; echo aarch64; end\nfunction sudo; echo UNEXPECTED_INSTALL; end')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('x86_64', result.stderr)
        self.assertNotIn('UNEXPECTED_INSTALL', result.stdout)

    def test_bad_checksum_preserves_existing_installation(self):
        result = self.run_hook('''
function uname; echo x86_64; end
function rpm; return 0; end
function curl; touch $argv[-1]; end
function sha256sum; return 1; end
function sudo; echo UNEXPECTED_INSTALL; end
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('existing binary retained', result.stderr)
        self.assertNotIn('UNEXPECTED_INSTALL', result.stdout)
