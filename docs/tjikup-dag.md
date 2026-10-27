# System tasks in the fleet DAG

Tjikup owns scheduling across home and system configuration. Chezetc still applies
managed files and runs its native before/once/onchange hooks, including the existing
configuration-refresh retry. Direct `chezetc apply` retains the native sequence.

`scripts/tjikup-plan.py` is the versioned adapter consumed by Dotjik. Its JSON
manifest enumerates every regular maintenance hook (except the banner). A missing,
added, or undeferable hook stops the workflow before Git or apply. Keep the system
adapter and Dotjik scheduler updates together when deploying this feature.

The native file pass sets `FLEET_DEFER_SYSTEM_HOOKS=1`; only audited hooks honor it.
Do not set this flag manually. The home wrapper hook installs the required sudo
environment allowlist before system files are applied. The scheduler renders each
system hook through Chezetc, retaining root template context, and syntax-checks the
whole system plan before any deferred system task starts. A config change during
rendering aborts the plan. Root commands run with noninteractive sudo; client
installers retain their existing desktop-user handoff.

RPM maintenance and Flatpak maintenance are separate tasks; Flatpak waits for RPM
packages so its executable is present on first apply. COPR/repository setup precedes
RPM maintenance. Independent application installers and home hooks can overlap.
DNF, Flatpak, Cargo, user/system systemd, storage, and networking resource locks are
shared across both layers. Installers that may invoke DNF retain that lock for the
whole hook. They still use their existing checks, update rules and scoped package
transactions. Plex exclusions and the Nginx ABI rebuild ordering remain intact.

The Tailscale reconciliation waits for home and system networking work before
enforcing the declared final network policy. Fedora release-upgrade prompting runs exclusively
at the end, after all home/system work, so a reboot cannot interrupt peer tasks.
Failures stop new dispatch, drain running tasks and block remaining work; already
completed work is not rolled back.

`FLEET_JOBS` controls the combined hook pool (default 4; 1 for serial diagnosis).
Each invocation saves private hook output and `timings.json` under the calling
user's `$XDG_STATE_HOME/tjikup/logs/apply-*` (default `~/.local/state`). Timings include
execution, dependency wait, resource/terminal wait, worker wait and start/end
offsets. Compare representative runs on each host before claiming a speedup.
The reported native system preparation time includes file application and rendering;
home native file application and home rendering have separate top-level durations,
alongside total apply time.

Tests use stub commands and temporary files. Rendering for fi/li/si is checked
without applying packages, files, services, network or storage to a real host.
