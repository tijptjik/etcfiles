"""Versioned system hook policy for the fleet scheduler; Chezmoi owns file state."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from tjikup.runtime import UpdateError

API_VERSION = 1


def load_plan(repo):
    plan = json.loads((repo / "scripts/tjikup-plan.json").read_text())
    directory = repo / "etc/.chezmoiscripts"
    actual = {p.name for p in directory.iterdir()
              if re.match(r"run_(?:\d|after_)", p.name) and p.name != "run_00-header.sh"}
    expected = {item["file"] for item in plan}
    if actual != expected:
        raise UpdateError("System hook manifest mismatch: " + ", ".join(sorted(actual ^ expected)))
    for name in expected:
        if "FLEET_DEFER_SYSTEM_HOOKS" not in (directory / name).read_text():
            raise UpdateError(f"System hook cannot be deferred: {name}")
    return plan


def paths():
    managed = Path("/opt/chezetc/chezetc")
    wrapper = shutil.which("chezetc") or str(managed if managed.is_file() else Path.home() / ".tools/chezetc/chezetc")
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "chezmoi/chezetc/chezmoi.toml"
    return wrapper, config


def apply_files(repo):
    # Use the existing adapter's conflict policy and configuration-refresh retry.
    spec = importlib.util.spec_from_file_location("fleet_system_apply", repo / "scripts/tjikup-apply.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    wrapper, config = paths()
    adapter.apply(repo, wrapper, config, skip_conflicts=os.environ.get("FLEET_SKIP_CONFLICTS") == "1",
                  defer_hooks=True)


def render_hooks(repo, plan, env):
    """Render the complete snapshot in one wrapper/configuration context."""
    wrapper, config = paths()
    filenames = sorted({item["file"] for item in plan})
    template = "{" + ",".join(json.dumps(name) + ':{{ includeTemplate ' +
        json.dumps('.chezmoiscripts/' + name) + ' . | toJson }}' for name in filenames) + "}"
    before = config.read_bytes() if config.is_file() else None
    result = subprocess.run([wrapper, "--source", str(repo / "etc"), "execute-template"], input=template,
                            env={**env, "TJIKUP_QUIET_CONFIG": "1"}, capture_output=True, text=True, timeout=120)
    after = config.read_bytes() if config.is_file() else None
    # Never dispatch a partial/stale plan after an out-of-band config change.
    if before != after:
        raise UpdateError("Chezetc configuration changed while preparing hooks; rerun tjikup")
    if result.returncode:
        raise UpdateError(f"cannot render system hooks: {result.stderr}")
    try:
        rendered = json.loads(result.stdout)
    except ValueError as error:
        raise UpdateError("System hook rendering did not return a complete plan") from error
    if not isinstance(rendered, dict) or set(rendered) != set(filenames) or not all(isinstance(s, str) for s in rendered.values()):
        raise UpdateError("System hook rendering returned an incompatible inventory")
    return rendered
