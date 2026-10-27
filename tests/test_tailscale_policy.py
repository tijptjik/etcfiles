"""Client apply resumes enrolled tailnets without enrolling or disconnecting."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TailscalePolicyTests(unittest.TestCase):
    def test_rendered_client_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for host in ('fi', 'li', 'si'):
                config = root / 'config.json'
                config.write_text(json.dumps({'data': {
                    'isDesktop': host == 'fi', 'isLaptop': host == 'li',
                    'isClient': host != 'si', 'isServer': host == 'si',
                }}))
                rendered = subprocess.run([
                    'chezmoi', '--source', str(ROOT / 'etc'), '--config', str(config),
                    '--persistent-state', str(root / 'state.db'), 'execute-template',
                    '-f', str(ROOT / 'etc/.chezmoiscripts/run_70-enable-tailscaled.fish.tmpl'),
                ], capture_output=True, text=True)
                self.assertEqual(rendered.returncode, 0, rendered.stderr)
                self.assertNotIn('tailscale down', rendered.stdout)
                syntax = subprocess.run(['fish', '--no-config', '--no-execute'],
                                        input=rendered.stdout, text=True, capture_output=True)
                self.assertEqual(syntax.returncode, 0, syntax.stderr)
                if host == 'si':
                    self.assertNotIn('tailscale set --accept-dns=false', rendered.stdout)
                    continue
                policy = rendered.stdout[rendered.stdout.index('# Keep ordinary DNS'):]
                harness = '''
function sudo; $argv; end
function timeout; set -e argv[1]; $argv; end
function step_skip_ok; end
function step_warn; echo warning; end
function step_fail; echo failure; end
function step_run_note; $argv[3..]; end
function tailscale
    echo (string join ' ' -- $argv) >> "$TRACE"
    switch $argv[1]
        case status; printf '{"BackendState":"%s"}\\n' "$TEST_STATE"
        case up; return $UP_STATUS
        case set; return 0
        case '*'; return 99
    end
end
'''
                for state, up_status, expected in [('Running', '0', 0), ('Stopped', '0', 0),
                                                   ('Stopped', '7', 1), ('NeedsLogin', '0', 0),
                                                   ('NeedsMachineAuth', '0', 0), ('Unavailable', '0', 1)]:
                    with self.subTest(host=host, state=state, up_status=up_status):
                        trace = root / 'trace'
                        trace.write_text('')
                        result = subprocess.run(['fish', '--no-config', '-c', harness + policy],
                            env={**os.environ, 'TEST_STATE': state, 'UP_STATUS': up_status, 'TRACE': str(trace)},
                            capture_output=True, text=True)
                        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
                        calls = trace.read_text().splitlines()
                        self.assertIn('set --accept-dns=false --accept-routes=false', calls)
                        self.assertEqual('up' in calls, state == 'Stopped')
                        self.assertNotIn('down', calls)
