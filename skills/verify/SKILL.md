---
name: verify
description: Prove something is finished rather than written. Use before saying work is done, before writing a status marker, before handing somebody something to merge, and before answering "is this working?" — it runs the project's "done" command, reports it honestly, and names what it did not run.
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

# Verify

**Done means both halves: it ran against the real thing AND the automated checks are
green.** One without the other is ⚠️, never ✅.

## First — the questions no check can ask

No command can ask these, and each ships as a defect when nobody does:

- Does a value that could not be computed show **blank** or "unknown" — never `0`, never a
  plausible-looking default? A `0` where the answer is unknown is a number somebody acts on.
- Does every number shown say **how old it is** and where it came from?
- Does the screen or the message say **what to do** when something is missing, not only that
  it is missing?
- Is there now a **second implementation** of something that already existed? Two idioms for
  one job means one is wrong and nobody knows which. Collapse it now, not later.
- Did a check **fail to run** anywhere and get read as a pass? A command exiting 0 because it
  found nothing to do looks exactly like one that found everything correct.

## Then — the "done" command

The settings above name it: `done.command`, run from the repository's root, whatever folder
the session stands in. This skill adds no check of its own: what "done" means is the
project's, in one place.

```bash
cd "$(git rev-parse --show-toplevel)" && <done.command>
```

Read the exit code, never the tone of the output:

| exit | what it means |
|---|---|
| `0` | every check the command runs passed |
| `done.owed-exit`, when it is not `none` | every check it **could** run passed; one only a running environment can make is left — ⚠️, never ✅ |
| anything else | something failed: show the failing lines in full |

A command that prints a failure and exits 0 is a broken command, not a pass: say so.

**The unattended loop runs this same command as its code gate** — at every item's last commit,
after the build and again after the review's fixes, and once on the branch tip — and only it may
stop an item. Keep it to the checks whose failure should: the build, the types, the tests.

## Then — what the command did not run

Name each, so nobody reads silence as a pass:

- **A screen changed.** Where `browser.check` is a command, run it on the changed page with
  the item's assertions; where it is `none`, the screen is for a person to check, with steps.
- **An environment.** The command ran in this copy of the project; nothing it ran saw what an
  environment in `environments.list` is serving.
- **Data.** A change to how stored data is shaped, proved only against an empty store, has
  proved nothing about the data it maps.
- **Anything in `agents.never-touch`.** It was not touched to check it.

## Report

State plainly, in this order:

```
verified     <what> — <how, naming the command and its exit code>
NOT verified <what> — <why not: needs a browser, an environment, data, a person>
```

A gap named is a gap somebody can close. ✅ only when both halves hold; otherwise ⚠️ with the
reason, or 🚧. **Every claim points at a result from this session.**

Something that behaved unlike its documentation or common sense is a trap: call the Skill tool
with `wiqrug:file-knowledge` now, before the report.
