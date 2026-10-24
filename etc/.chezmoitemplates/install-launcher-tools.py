#!/usr/bin/env python3
"""Install current stable Hamr and Gitfetch releases in versioned directories."""
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

HAMR_REPO = "Stewart86/hamr"
GITFETCH_REPO = "Matars/gitfetch"


def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def github_json(url):
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "chezetc-launcher-tools",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def latest_release(repo):
    releases = github_json(f"https://api.github.com/repos/{repo}/releases?per_page=100")
    for release in releases:
        tag = release.get("tag_name", "")
        if release.get("draft") or release.get("prerelease") or not tag.startswith("v"):
            continue
        version = tag[1:]
        if len(version.split(".")) != 3 or not all(part.isdecimal() for part in version.split(".")):
            continue
        return version, tag, release
    raise RuntimeError(f"No stable semantic-version release found for {repo}")


def release_asset(release, filename):
    asset = next((item for item in release.get("assets", [])
                  if item.get("name") == filename), None)
    if asset is None:
        raise RuntimeError(f"Release is missing {filename}")
    digest = asset.get("digest", "")
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest or ""):
        raise RuntimeError(f"Release asset {filename} has no SHA-256 digest")
    return asset["browser_download_url"], digest.split(":", 1)[1].lower()


def download(url, digest, dest):
    request = urllib.request.Request(url, headers={"User-Agent": "chezetc-launcher-tools"})
    with urllib.request.urlopen(request, timeout=60) as response, dest.open("wb") as output:
        shutil.copyfileobj(response, output)
    if hashlib.sha256(dest.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"Checksum mismatch: {url}")


def activate(name, target):
    link = Path("/usr/local/bin") / name
    if link.exists() and not link.is_symlink():
        raise RuntimeError(f"Refusing to replace unmanaged command: {link}")
    if link.is_symlink() and link.resolve() == Path(target).resolve():
        return False
    temporary = link.with_name(name + ".new")
    run("sudo", "-n", "ln", "-sfn", str(target), str(temporary))
    run("sudo", "-n", "mv", "-Tf", str(temporary), str(link))
    return True


def install_hamr():
    version, tag, release = latest_release(HAMR_REPO)
    archive_name = "hamr-linux-x86_64.tar.gz"
    url, digest = release_asset(release, archive_name)
    target = Path("/opt/hamr") / version
    changed = False
    marker = target / ".installed"
    if (not marker.is_file() or marker.read_text().strip() != digest
            or any(not (target / name).is_file() for name in ("hamr", "hamr-daemon", "hamr-gtk", "hamr-tui"))):
        with tempfile.TemporaryDirectory(prefix="chezetc-hamr-") as directory:
            temp = Path(directory)
            archive = temp / "hamr.tar.gz"
            download(url, digest, archive)
            extracted = temp / "hamr"
            extracted.mkdir()
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(extracted, filter="data")
            source = next(extracted.rglob("hamr-daemon")).parent
            subprocess.run([str(source / "hamr"), "--version"], check=True, stdout=subprocess.DEVNULL)
            for name in ("hamr", "hamr-daemon", "hamr-gtk", "hamr-tui"):
                libraries = subprocess.run(["ldd", str(source / name)], capture_output=True, text=True)
                if "not found" in libraries.stdout:
                    raise RuntimeError(f"Missing libraries for {name}: {libraries.stdout}")
            run("sudo", "-n", "install", "-d", "-m", "755", str(target))
            run("sudo", "-n", "cp", "-r", str(source) + "/.", str(target) + "/")
            run("sudo", "-n", "chown", "-R", "root:root", str(target))
            run("sudo", "-n", "chmod", "-R", "go-w", str(target))
            marker_file = temp / ".installed"
            marker_file.write_text(digest + "\n")
            run("sudo", "-n", "install", "-m", "644", str(marker_file), str(marker))
        changed = True
    for name in ("hamr", "hamr-daemon", "hamr-gtk", "hamr-tui"):
        changed = activate(name, target / name) or changed
    print(f"Hamr {version}: installed or already current")
    return changed


def install_gitfetch():
    version, tag, _ = latest_release(GITFETCH_REPO)
    commit_data = github_json(f"https://api.github.com/repos/{GITFETCH_REPO}/commits/{tag}")
    revision = commit_data.get("sha", "")
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise RuntimeError(f"GitHub returned an invalid Gitfetch commit for {tag}")
    target = Path("/opt/gitfetch") / revision[:12]
    changed = False
    marker = target / ".installed"
    if not marker.is_file() or marker.read_text().strip() != revision:
        with tempfile.TemporaryDirectory(prefix="chezetc-gitfetch-") as directory:
            temp = Path(directory)
            source = temp / "source"
            run("git", "clone", "--quiet", "--depth", "1", "--branch", tag,
                f"https://github.com/{GITFETCH_REPO}.git", str(source))
            actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
            if actual != revision:
                raise RuntimeError(f"Gitfetch tag {tag} resolved to {actual}, expected {revision}")
            run("sudo", "-n", "install", "-d", "-m", "755", str(target.parent))
            if not (target / "bin/python").is_file():
                run("/usr/bin/python3", "-m", "venv", str(target))
            run(str(target / "bin/pip"), "install", "--upgrade", "--force-reinstall", str(source))
            run(str(target / "bin/gitfetch"), "--help", stdout=subprocess.DEVNULL)
            marker_file = temp / ".installed"
            marker_file.write_text(revision + "\n")
            run("sudo", "-n", "install", "-d", "-m", "755", str(target))
            run("sudo", "-n", "chown", "-R", "root:root", str(target))
            run("sudo", "-n", "install", "-m", "644", str(marker_file), str(marker))
        changed = True
    changed = activate("gitfetch", target / "bin/gitfetch") or changed
    print(f"Gitfetch {version} ({revision[:12]}): installed or already current")
    return changed


def main():
    if os.uname().machine != "x86_64":
        raise RuntimeError("Hamr and Gitfetch releases are currently available for x86_64 only")
    Path("/usr/local/bin").mkdir(parents=True, exist_ok=True)
    changed = install_hamr()
    changed = install_gitfetch() or changed
    print("CHEZETC_RESULT=changed" if changed else "CHEZETC_RESULT=unchanged")


if __name__ == "__main__":
    main()
