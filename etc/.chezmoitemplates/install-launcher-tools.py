#!/usr/bin/env python3
"""Install pinned launcher tools into root-owned, versioned directories."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

HAMR_VERSION = '1.1.0'
GITFETCH_REV = '9ff4320267955e1634d424ed195902aeb2bf5947'


def run(*args):
    subprocess.run(args, check=True)


def download(url, digest, dest):
    urllib.request.urlretrieve(url, dest)
    if hashlib.sha256(dest.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f'Checksum mismatch: {url}')


def activate(name, target):
    link = Path('/usr/local/bin') / name
    if link.exists() and not link.is_symlink():
        raise RuntimeError(f'Refusing to replace unmanaged command: {link}')
    staged = link.with_name(name + '.new')
    staged.unlink(missing_ok=True)
    staged.symlink_to(target)
    staged.replace(link)


def main():
    Path('/usr/local/bin').mkdir(parents=True, exist_ok=True)
    hamr = Path('/opt/hamr') / HAMR_VERSION
    gitfetch = Path('/opt/gitfetch') / GITFETCH_REV[:12]
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        if not (hamr / '.installed').exists():
            archive = temp / 'hamr.tar.gz'
            download(f'https://github.com/Stewart86/hamr/releases/download/v{HAMR_VERSION}/hamr-linux-x86_64.tar.gz',
                     '8de771298311f54dc986f92b23a72dad4f87e23cb9bb59b7fd9bc6425dcf490b', archive)
            extracted = temp / 'hamr'
            with tarfile.open(archive) as tar:
                tar.extractall(extracted, filter='data')
            source = next(extracted.rglob('hamr-daemon')).parent
            run(str(source / 'hamr'), '--version')
            for name in ('hamr', 'hamr-daemon', 'hamr-gtk', 'hamr-tui'):
                libraries = subprocess.run(['ldd', str(source / name)], capture_output=True, text=True)
                if 'not found' in libraries.stdout:
                    raise RuntimeError(f'Missing libraries for {name}: {libraries.stdout}')
            hamr.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, hamr, dirs_exist_ok=True)
            (hamr / '.installed').touch()
        if not (gitfetch / '.installed').exists():
            archive = temp / 'gitfetch.tar.gz'
            download(f'https://codeload.github.com/Matars/gitfetch/tar.gz/{GITFETCH_REV}',
                     'd62af3b01e9da2b0ef4e6aa655f3701151b3ff219b062bd9b83321903f080d1b', archive)
            with tarfile.open(archive) as tar:
                tar.extractall(temp / 'gitfetch', filter='data')
            source = next((temp / 'gitfetch').iterdir())
            run('/usr/bin/python3', '-m', 'venv', str(gitfetch))
            run(str(gitfetch / 'bin/pip'), 'install', str(source))
            run(str(gitfetch / 'bin/gitfetch'), '--help')
            (gitfetch / '.installed').touch()
    for name in ('hamr', 'hamr-daemon', 'hamr-gtk', 'hamr-tui'):
        activate(name, hamr / name)
    activate('gitfetch', gitfetch / 'bin/gitfetch')


if __name__ == '__main__':
    main()
