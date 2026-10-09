---
name: setup
description: Fit wiqrug to a project — check its dependencies, audit what it already has, interview the user about how it should be organised, play the result back, then build it as tickets on a branch of its own and prove it with a final check. Writes nothing until the user confirms.
argument-hint: "[--upgrade]"
disable-model-invocation: true
---

!`wiqrug-check --skill`

The first line above is the project check's answer. **If it says git is not installed, Python is
not installed, or the folder is not a git repository, show that line to the user exactly as it
is, and stop.** Write nothing, and never run `git init` — a folder becomes a repository only by
the user's own hand.

- The arguments are `--upgrade`, or it says the project was set up by an older wiqrug: read
  `${CLAUDE_SKILL_DIR}/upgrade.md` and follow it instead of everything below.
- It begins `wiqrug: set up —`: the project is already set up. Say so, and that
  `/wiqrug:setup --upgrade` is how a newer wiqrug is brought in; stop.
- It begins `wiqrug: setup in progress`: the playback was confirmed in an earlier session. If the
  queue folder it names holds `wiqrug-setup/`, resume the build from the first ticket not yet
  committed — step 5. If it does not, the playback was never written down: say so, and that
  deleting wiqrug.md in the `.claude` folder and running `/wiqrug:setup` again starts over; stop.
- It says the project is not set up, or that its settings file is refused: go on. A refused file
  is read as one more thing the audit found.

# Setup

Fits wiqrug to this project: what it has, how it should be organised, and the settings file every
other skill reads — built on a `wiqrug-setup` branch, one commit per ticket, and proved by a final
check. **Nothing is written until the user confirms the playback** — not a folder,
not a commit, not a line of `CLAUDE.md`. A tool that rewrites a project unasked is one nobody
installs twice.

## 1 — the audit

What the project already has, read before a single question:

!`wiqrug-check --skill --run ${CLAUDE_PLUGIN_ROOT}/lib/audit.py`

Its first line names the project's root — every path below and every path in the settings file is
relative to it, whatever folder this session stands in — and the installed wiqrug version.

Read what it found, in a background `Explore` subagent when there is much of it: the agent
instructions, every rule and project skill, other AI tools' instruction files — **read for rules
worth keeping, never edited** — the README, and the build and CI files behind the proposed "done"
command. Read `${CLAUDE_PLUGIN_ROOT}/lib/settings.example.md` too: it is every setting the
interview has to settle, each with its reason.

## 2 — the interview

The technique is pasted below from the `interview` skill; the questions are pasted after it.
Start from the audit: a question it answers becomes a recommendation, not a question. If nothing
follows either rule, read `${CLAUDE_PLUGIN_ROOT}/skills/interview/SKILL.md` and
`${CLAUDE_SKILL_DIR}/questions.md` and use them.

Two kinds of question are answered **one by one, never as a batch**: each change to an existing
`CLAUDE.md` (its own number, `C1`, `C2`, …; nothing removed without one), and each overlapping
project skill (keep, retire to the archive folder, or fold into the settings).

---

!`wiqrug-check --skill --run ${CLAUDE_PLUGIN_ROOT}/skills/grill-me/paste.py ${CLAUDE_PLUGIN_ROOT}/skills/interview/SKILL.md`

---

!`wiqrug-check --skill --run ${CLAUDE_PLUGIN_ROOT}/skills/grill-me/paste.py ${CLAUDE_SKILL_DIR}/questions.md`

---

## 3 — the playback

When the frontier is empty, play back in the interview's form, then what setup would write:

```text
Settings     <section.key = value> — one line per setting, every one; `none` where agreed
Folders      <path> — new | existing, kept where it is — per kind of document
Knowledge    Standard | Full — the templates laid down
CLAUDE.md    C1 accepted · C2 declined · … — or: a new one, outline below
Skills       <name>: keep | retire | fold — one line per overlap
Not touched  other AI tools' files; the application's code
Decisions    <decision>: user, round N | looked up: <source> | undecided: <what it waits on>
```

A setting with no value agreed is not filled in by default: it goes back into a round, or is
listed undecided — and then setup cannot finish, so say what it waits on. Then **wait for the
user's yes**. Anything else is the next round.

## 4 — after the yes: the settings file, in progress

The only thing written now: the settings file as wiqrug.md in the `.claude` folder at the
project's root (the root the audit's first line names), with exactly the two settings the rest of
setup needs — the installed version the audit named, and the agreed `documents.queue`:

````markdown
# wiqrug settings

Setup is in progress: this file holds only the queue's place until setup has built the rest.
Every setting is explained in the settings example that comes with wiqrug.

```ini wiqrug
[wiqrug]
version = <the installed version>
state = setup-in-progress

[documents]
queue = <the agreed queue folder, relative to the root>
```
````

Then run `wiqrug-check` and read its first line: it must begin `wiqrug: setup in progress`. If it
does not, show the line and stop. Nothing is committed yet; the file is the target the build
starts from.

## 5 — the build, ticket by ticket

Read `${CLAUDE_SKILL_DIR}/build.md` and follow it: the agreed setup written as a queue of tickets,
the `wiqrug-setup` branch, one subagent per ticket **one at a time**, one commit per ticket, then
the final check. The plugin's folder, which it names as `${CLAUDE_PLUGIN_ROOT}`, is
`${CLAUDE_PLUGIN_ROOT}` — write that path into every command it gives. The application's code is
never touched.

## Report

The final check's ✅/⚠️/❌ lines exactly as printed, the commits on `wiqrug-setup`, any ticket left
unbuilt with its failing command, and how to merge or delete the branch — build.md's step 5.
A ❌ on the done command is the project's own failing check, reported as the project's.
