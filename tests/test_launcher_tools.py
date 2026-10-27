"""Verify installer refuses corrupt downloads and unmanaged command replacement."""
import hashlib
import io
import importlib.util
from pathlib import Path
import tempfile
import shutil
import subprocess
import tarfile
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

    def test_repair_replaces_running_executable_and_then_skips_copy(self):
        """Use a real executing ELF file: the old cp command raises ETXTBSY."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = root / 'installed'
            target = releases / '1.1.0'
            target.mkdir(parents=True)
            names = ('hamr', 'hamr-daemon', 'hamr-gtk', 'hamr-tui')
            source = root / 'payload'
            source.mkdir()
            for name in names:
                shutil.copy2('/bin/sleep', source / name)
                shutil.copy2('/bin/sleep', target / name)
            archive = root / 'release.tar.gz'
            with tarfile.open(archive, 'w:gz') as stream:
                stream.add(source, arcname='hamr-linux-x86_64')
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            old_inode = (target / 'hamr-daemon').stat().st_ino
            process = subprocess.Popen([str(target / 'hamr-daemon'), '60'])
            real_run = subprocess.run

            def run(*args, **kwargs):
                self.assertEqual(args[:2], ('sudo', '-n'))
                if args[2] == 'chown':
                    return  # Keep the test entirely unprivileged.
                real_run(args[2:], check=True, **kwargs)

            try:
                with patch.object(installer, 'Path', side_effect=lambda p: releases if p == '/opt/hamr' else Path(p)), \
                        patch.object(installer, 'latest_release', return_value=('1.1.0', 'v1.1.0', {})), \
                        patch.object(installer, 'release_asset', return_value=('https://example.invalid/hamr', digest)), \
                        patch.object(installer, 'download', side_effect=lambda url, digest, dest: shutil.copyfile(archive, dest)) as download, \
                        patch.object(installer, 'run', side_effect=run), \
                        patch.object(installer, 'activate', return_value=False):
                    self.assertTrue(installer.install_hamr())
                    self.assertIsNone(process.poll())
                    self.assertNotEqual((target / 'hamr-daemon').stat().st_ino, old_inode)
                    self.assertEqual((target / '.installed').read_text().strip(), digest)
                    self.assertFalse(installer.install_hamr())
                    self.assertEqual(download.call_count, 1)
            finally:
                process.terminate()
                process.wait(timeout=5)

    def test_failed_payload_copy_does_not_publish_receipt_or_activate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'payload'
            source.mkdir()
            for name in ('hamr', 'hamr-daemon', 'hamr-gtk', 'hamr-tui'):
                shutil.copy2('/bin/sleep', source / name)
            archive = root / 'release.tar.gz'
            with tarfile.open(archive, 'w:gz') as stream:
                stream.add(source, arcname='hamr-linux-x86_64')
            releases = root / 'installed'
            def run(*args, **kwargs):
                if args[2] == 'cp':
                    raise subprocess.CalledProcessError(1, args)
                subprocess.run(args[2:], check=True, **kwargs)
            with patch.object(installer, 'Path', side_effect=lambda p: releases if p == '/opt/hamr' else Path(p)), \
                    patch.object(installer, 'latest_release', return_value=('1.1.0', 'v1.1.0', {})), \
                    patch.object(installer, 'release_asset', return_value=('https://example.invalid/hamr', 'a' * 64)), \
                    patch.object(installer, 'download', side_effect=lambda url, digest, dest: shutil.copyfile(archive, dest)), \
                    patch.object(installer, 'run', side_effect=run), \
                    patch.object(installer, 'activate') as activate:
                with self.assertRaises(subprocess.CalledProcessError):
                    installer.install_hamr()
                self.assertFalse((releases / '1.1.0/.installed').exists())
                activate.assert_not_called()
