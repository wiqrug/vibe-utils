# The upgrade

Brings a project set up by an older wiqrug to the installed one. **It changes the settings file and
makes the folders the settings name — never a document's content**, and it writes nothing until the
user has seen the plan and said yes. A release that rewrote a project unseen is one nobody installs
twice.

## 1 — the plan

```bash
wiqrug-check --run "${CLAUDE_PLUGIN_ROOT}/lib/upgrade.py" --plan
```

Show its output to the user exactly as printed — the release notes it quotes and every change line.
Then, by its first line:

- `cannot upgrade`: show the reason and stop. A project that is not set up is pointed at
  `/wiqrug:setup`; a refused settings file is the user's to fix by hand.
- `nothing to upgrade`: say so and stop.
- an upgrade plan: go on.

## 2 — the values nobody chose

Each `needs` line is a setting a release added without a value it could choose for every project.
Ask for each, one question at a time, with the settings example's reason for it
(`${CLAUDE_PLUGIN_ROOT}/lib/settings.example.md`) and a recommendation drawn from the project. **Never
fill one in by default**: `none` is an answer the user gives, not one you assume. Run the plan again
with every answer as `--set section.key=value` and show the new plan; it must have no `needs` line.

## 3 — the yes, then the apply

Ask: *apply this plan?* Anything but a yes is not one — answer the question, change a value and
show the plan again, or stop with nothing written.

On a yes, the same command with `--apply` in place of `--plan` and the same `--set` values:

```bash
wiqrug-check --run "${CLAUDE_PLUGIN_ROOT}/lib/upgrade.py" --apply
```

It writes exactly the plan it prints again, then the project check's answer: it must begin
`wiqrug: set up —` (or `wiqrug: setup in progress`, when setup itself was unfinished). If it does
not, or the command exits non-zero, show the output and stop.

## Report

The changes applied, as printed; the project check's line; and that nothing is committed — the
settings file and any new folder are the user's to review with `git status` and commit.
