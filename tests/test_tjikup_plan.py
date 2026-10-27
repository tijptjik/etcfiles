"""Render the system plan and exercise split maintenance with synthetic commands."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_tjikup_apply

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('system_plan', ROOT / 'scripts/tjikup-plan.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def render(hook, host, temporary):
    config = temporary / 'config.json'
    config.write_text(json.dumps({'data': dict(isDesktop=host == 'fi', isLaptop=host == 'li',
        isClient=host != 'si', isServer=host == 'si')}))
    source = (ROOT / 'etc/.chezmoiscripts' / hook).read_text().replace('.chezmoi.hostname', json.dumps(host))
    return subprocess.run(['chezmoi', '--source', str(ROOT / 'etc'), '--config', str(config),
                           '--persistent-state', str(temporary / 'state.db'), 'execute-template'],
                          input=source, capture_output=True, text=True, check=True).stdout


class SystemPlanTests(unittest.TestCase):
    def test_inventory_fails_closed_when_a_hook_is_added_or_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / 'scripts', root / 'scripts')
            shutil.copytree(ROOT / 'etc/.chezmoiscripts', root / 'etc/.chezmoiscripts')
            self.assertTrue(policy.load_plan(root))
            extra = root / 'etc/.chezmoiscripts/run_59-new.fish'
            extra.write_text('exit 0\n')
            with self.assertRaisesRegex(policy.UpdateError, 'manifest mismatch'):
                policy.load_plan(root)
            extra.unlink()
            next((root / 'etc/.chezmoiscripts').glob('run_after_*')).unlink()
            with self.assertRaisesRegex(policy.UpdateError, 'manifest mismatch'):
                policy.load_plan(root)

    def test_native_apply_preserves_retry_and_passes_deferral(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / 'config'
            calls = []
            def run(*args, **kw):
                calls.append(kw['env']['FLEET_DEFER_SYSTEM_HOOKS'])
                config.write_text('refreshed')
            with patch.object(test_tjikup_apply.policy, 'run_stream', side_effect=run), \
                    patch.object(test_tjikup_apply.policy, 'stage_result'):
                test_tjikup_apply.policy.apply(Path(temporary), 'wrapper', config, defer_hooks=True)
            self.assertEqual(calls, ['1', '1'])

    def test_batch_renderer_uses_one_wrapper_call_and_checks_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            config = temp / 'config.json'
            config.write_text(json.dumps({'data': dict(isDesktop=True, isLaptop=False,
                isClient=True, isServer=False)}))
            wrapper = temp / 'wrapper'
            wrapper.write_text('#!/bin/sh\nexec chezmoi --config "$TEST_CONFIG" --persistent-state "$TEST_STATE" "$@"\n')
            wrapper.chmod(0o755)
            plan = policy.load_plan(ROOT)
            env = {**os.environ, 'TEST_CONFIG': str(config), 'TEST_STATE': str(temp / 'state')}
            with patch.object(policy, 'paths', return_value=(str(wrapper), config)):
                rendered = policy.render_hooks(ROOT, plan, env)
            self.assertEqual(set(rendered), {item['file'] for item in plan})
            for text in rendered.values():
                subprocess.run(['fish', '--no-config', '--no-execute'], input=text,
                               text=True, capture_output=True, check=True)
            with patch.object(policy, 'paths', return_value=('wrapper', config)), \
                    patch.object(policy.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{}', '')) as run:
                with self.assertRaisesRegex(policy.UpdateError, 'inventory'):
                    policy.render_hooks(ROOT, plan, env)
                run.assert_called_once()

    @unittest.skipUnless(shutil.which('fish') and shutil.which('chezmoi'), 'Fish and Chezmoi required')
    def test_every_host_renders_and_native_deferral_runs_no_hook_body(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            for host in ('fi', 'li', 'si'):
                for hook in sorted({item['file'] for item in policy.load_plan(ROOT)}):
                    with self.subTest(host=host, hook=hook):
                        text = render(hook, host, temp)
                        subprocess.run(['fish', '--no-config', '--no-execute'], input=text,
                                       text=True, capture_output=True, check=True)
                        result = subprocess.run(['fish', '--no-config'], input=text,
                            env={**os.environ, 'FLEET_DEFER_SYSTEM_HOOKS': '1'},
                            text=True, capture_output=True, timeout=5)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout, '')

    @unittest.skipUnless(shutil.which('fish') and shutil.which('chezmoi'), 'Fish and Chezmoi required')
    def test_split_package_phases_preserve_work_and_failure_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            text = render('run_30-system-update.fish.tmpl', 'fi', temp)
            # Replace only command boundaries, exercising the real phase branches.
            mocks = r'''
function _chezetc_system_log; end
function snapshot_rpm_versions; printf 'example\t1\n' > $argv[1]; end
function snapshot_flatpak_versions; printf 'example\t1\n' > $argv[1]; end
function snapshot_flatpak_refs; printf '' > $argv[1]; end
function report_package_updates; set -g package_update_count 0; end
function count_package_changes; set -g package_change_count 0; end
function count_removed_entries; set -g package_change_count 0; end
function step_run_dnf_update
    printf '%s\n' (string join ' ' -- $argv[2..]) >> "$TRACE"
    test "$FAIL_DNF" != 1
end
function step_run_quiet
    printf '%s\n' (string join ' ' -- $argv[2..]) >> "$TRACE"
end
function step_run_as; return 0; end
'''
            text = text.replace('setup_logging linux-dnf-update', 'setup_logging linux-dnf-update\n' + mocks)
            bindir = temp / 'bin'; bindir.mkdir()
            for name, body in {
                'rpm': 'echo 45', 'curl': 'echo \'[{"version":"45"}]\'',
                'sudo': 'echo UNEXPECTED_SUDO >&2; exit 99',
                'dnf': 'echo UNEXPECTED_DNF >&2; exit 99',
            }.items():
                path = bindir / name
                path.write_text('#!/bin/sh\n' + body + '\n'); path.chmod(0o755)
            outputs = {}
            for phase in ('all', 'rpm', 'flatpak', 'release'):
                trace = temp / phase
                env = {**os.environ, 'PATH': str(bindir) + ':' + os.environ['PATH'],
                       'FLEET_SYSTEM_PHASE': phase, 'FLEET_DEFER_SYSTEM_HOOKS': '0',
                       'TJIKUP_NO_SPIN': '1', 'TRACE': str(trace), 'FAIL_DNF': '0'}
                result = subprocess.run(['fish', '--no-config'], input=text, env=env,
                                        text=True, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs[phase] = trace.read_text().splitlines() if trace.exists() else []
            self.assertTrue(any('dnf update' in line for line in outputs['rpm']))
            self.assertTrue(any('dnf install' in line for line in outputs['rpm']))
            self.assertTrue(any('flatpak update' in line for line in outputs['flatpak']))
            self.assertFalse(any('flatpak ' in line for line in outputs['rpm']))
            self.assertFalse(any('dnf ' in line for line in outputs['flatpak']))
            self.assertEqual(outputs['release'], [])
            self.assertCountEqual(outputs['all'], outputs['rpm'] + outputs['flatpak'])
            env.update(FLEET_SYSTEM_PHASE='rpm', FAIL_DNF='1')
            result = subprocess.run(['fish', '--no-config'], input=text, env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
