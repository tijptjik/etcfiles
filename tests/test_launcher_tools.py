"""Verify installer refuses corrupt downloads and unmanaged command replacement."""
import hashlib
import io
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'etc/.chezmoitemplates/install-launcher-tools.py'
spec = importlib.util.spec_from_file_location('launcher_tools', SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class LauncherToolsTests(unittest.TestCase):
    def test_download_rejects_mismatched_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'archive'
            with patch.object(installer.urllib.request, 'urlopen',
                              side_effect=lambda *args, **kwargs: io.BytesIO(b'wrong download')):
                with self.assertRaisesRegex(RuntimeError, 'Checksum mismatch'):
                    installer.download('https://example.invalid/tool', '0' * 64, target)
                installer.download('https://example.invalid/tool', hashlib.sha256(b'wrong download').hexdigest(), target)

    def test_activation_preserves_unmanaged_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = root / 'hamr'
            command.write_text('personal executable')
            with patch.object(installer, 'Path', return_value=root):
                with self.assertRaisesRegex(RuntimeError, 'unmanaged command'):
                    installer.activate('hamr', root / 'release/hamr')
            self.assertEqual(command.read_text(), 'personal executable')

    def test_activation_updates_existing_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = root / 'hamr'
            command.symlink_to(root / 'old/hamr')
            def run(*args):
                self.assertEqual(args[:2], ('sudo', '-n'))
                if args[2:4] == ('ln', '-sfn'):
                    Path(args[5]).unlink(missing_ok=True)
                    Path(args[5]).symlink_to(args[4])
                elif args[2:4] == ('mv', '-Tf'):
                    Path(args[4]).replace(args[5])
                else:
                    self.fail(f'Unexpected system command: {args}')
            with patch.object(installer, 'Path', side_effect=lambda p: root if p == '/usr/local/bin' else Path(p)), \
                 patch.object(installer, 'run', side_effect=run) as commands:
                self.assertTrue(installer.activate('hamr', root / 'new/hamr'))
                self.assertEqual(commands.call_count, 2)
                self.assertFalse(installer.activate('hamr', root / 'new/hamr'))
                self.assertEqual(commands.call_count, 2)
            self.assertEqual(command.readlink(), root / 'new/hamr')
