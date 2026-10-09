# 01: The settings file, in full

Advances:   wiqrug-setup
Touches:    .claude/wiqrug.md

<!-- wiqrug template: setup's first ticket, always 01. Setup fills every <placeholder> from the
confirmed playback before a subagent reads it; nothing here is decided by the subagent. -->

## What to build

Rewrite the settings file at wiqrug.md in the .claude folder from the in-progress one setup wrote, with every
setting the playback agreed and its reason beside it, in the shape of the plugin's settings
example. `wiqrug.state` becomes `complete`; `wiqrug.version` stays the installed version. A setting
played back as `none` is written `none`, never left blank and never given a default.

The agreed settings, verbatim from the playback:

```text
<every `section.key = value` line of the playback's Settings>
```

## Acceptance

- [ ] `wiqrug-check` exits 0 and its first line begins `wiqrug: set up —`
- [ ] `wiqrug-check` prints each line of the agreed settings above, its paths made absolute

## Comments
