"""Verify installer refuses corrupt downloads and unmanaged command replacement."""
import hashlib
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
            def retrieve(url, dest):
                dest.write_bytes(b'wrong download')
            with patch.object(installer.urllib.request, 'urlretrieve', side_effect=retrieve):
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
            with patch.object(installer, 'Path', return_value=root):
                installer.activate('hamr', root / 'new/hamr')
            self.assertEqual(command.readlink(), root / 'new/hamr')
