#!/usr/bin/env python3
"""Fleet system-apply policy. Invoked by the dotfiles tjikup workflow."""

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
import sys

from tjikup.runtime import UpdateError, run_stream, stage_result


def wrapper_path():
    """The managed wrapper owns the fleet's sudo environment allowlist."""
    managed = Path("/opt/chezetc/chezetc")
    launcher = Path("/usr/local/bin/chezetc")
    if managed.is_file():
        return str(launcher if launcher.is_file() else managed)
    return shutil.which("chezetc") or str(Path.home() / ".tools/chezetc/chezetc")


@contextmanager
def conflict_input(command, skip):
    if not skip:
        yield command, None
        return
    with subprocess.Popen(["yes", "skip"], stdout=subprocess.PIPE) as answers:
        try:
            yield [*command, "--no-tty", "--interactive=false"], answers.stdout
        finally:
            answers.stdout.close()
            answers.terminate()
            answers.wait()


def apply(repo, wrapper, config, *, skip_conflicts=False, defer_hooks=False):
    environment = {
        **os.environ,
        "CHEZMOI_SKIP_SPLASH": "1",
        "TJIKUP_SKIP_PREFLIGHT": "1",
        "TJIKUP_QUIET_CONFIG": "1",
    }
    if defer_hooks:
        environment["FLEET_DEFER_SYSTEM_HOOKS"] = "1"
    before = config.read_bytes() if config.is_file() else None

    def once():
        with conflict_input(
            [str(wrapper), "--source", str(repo / "etc"), "apply"], skip_conflicts
        ) as (command, stdin):
            run_stream(command, repo, env=environment, timeout=1800, stdin=stdin)

    once()
    after = config.read_bytes() if config.is_file() else None
    if before != after:
        stage_result("CONFIG", "Chezetc", "configuration refreshed")
        once()


def main():
    repo = Path(__file__).resolve().parents[1]
    wrapper = wrapper_path()
    config = Path.home() / ".config/chezmoi/chezetc/chezmoi.toml"
    apply(
        repo,
        wrapper,
        config,
        skip_conflicts=os.environ.get("FLEET_SKIP_CONFLICTS") == "1",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UpdateError as error:
        print(f"chezetc apply: {error}", file=sys.stderr)
        raise SystemExit(1)
