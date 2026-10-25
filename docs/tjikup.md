# tjikup integration

The reusable runner is maintained in tooltjik/apps/tjikup. The dotfiles
repository declares the fleet workflow and handles repository synchronization;
this repository owns scripts/tjikup-apply.py and system configuration hooks.

The apply adapter uses the Chezetc wrapper with this checkout as its source,
preserves interactive prompts, accepts FLEET_SKIP_CONFLICTS=1 from the workflow,
and retries once after the wrapper refreshes its configuration. Routine refresh
messages are suppressed with TJIKUP_QUIET_CONFIG; one CONFIG row reports the
refresh. Errors remain fatal and warnings/prompts stay visible. The report and
terminal environment use the tjikup runtime protocol.

Deploy the matching tooltjik, dotfiles and Chezetc revisions together. No runner
code is vendored here. To test without changing /etc or invoking real hooks:

```sh
TOOLTJIK_REPO=~/code/tooltjik python3 -B -m unittest discover -s tests -p 'test_tjikup_apply.py' -v
```

These tests cover conflict input, retry and failure behavior, not live fleet
acceptance. Normal Chezetc hooks retain their existing order and scope.
