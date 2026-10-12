---
name: update-knowledge
description: Use when work is finished or merged, before /clear, or when the owner says "write this up" or "we are done for today". With a slug, also for a queue's To file lines, its open decisions and its archiving; with --unattended, the loop's closing session.
argument-hint: "[<slug> [--unattended]]"
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

# Update knowledge

The closing check: file what was not filed, fix what the range made false, rewrite the Now and
Next, check the knowledge against its templates. The settings above name the documents and
`knowledge.level`. The range is every commit since this skill last finished in this working tree,
whichever session made them, plus the working tree itself:

```bash
git --no-pager log --oneline refs/worktree/wiqrug-update-knowledge..HEAD
git --no-pager status --short
```

`<base>` below is `refs/worktree/wiqrug-update-knowledge`. When the first command answers
*unknown revision*, this is the tree's first run: `<base>` is where the branch left the main
branch, `git merge-base <main> HEAD`. The test: **could somebody with no memory of this work pick
it up tomorrow and repeat none of it?**

## 1 — anything not filed yet

Knowledge is filed when learned; this step catches the rest. For each trap, question, answer,
term, decision or defect — and in a Full knowledge base, fact — not yet filed, call the Skill
tool with `wiqrug:file-knowledge`, one commit each; it owns every kind's format, its ID rules,
and what to offer when the project's level lacks the kind.

**With a slug** (`/wiqrug:update-knowledge <slug>`), also read every item in the slug's folder
under `documents.queue`: each unticked line of its `## To file` section, and any note its
`## Comments` leaves for this skill. File each through `wiqrug:file-knowledge`, then tick the line
with where it now lives — and, where the level lacked the kind, which kind it became. A finding
already filed is ticked with where it lives, not filed twice.

**An open `D:` line is a question for the owner**: a decision is written in their words. Put
every open one to them in one round, numbered, each with your recommendation; file what they
decide, in their words, and leave the rest unticked.

## 2 — what did the range make false?

```bash
git --no-pager diff --name-status --diff-filter=DR <base>..HEAD     # files deleted or renamed
git --no-pager log --first-parent --oneline <base>..HEAD            # one line per piece of work
```

For each file the first lists, and each function, flag, route, screen, script or setting the
second's work renamed or removed, search the documents the settings name, the `.claude` folder
and `CLAUDE.md` for the old name with the Grep tool, and fix or retire each hit: a citation of a
deleted thing reads as checkable.

## 3 — Now and Next

**Standard** — rewrite `documents.now` in the format of
`${CLAUDE_PLUGIN_ROOT}/templates/knowledge/standard/now.md`: Now at most three lines, Next at most
eight, no hash, no date. What stops being true is deleted — git holds it — never condensed into a
summary line.

**Full** — for each unit the range's work touched (step 2's second list, not commit by commit), in
`documents.units`, in the format of `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/unit.md`:
rewrite `## Now` — the marker and what is left, **at most three lines** — and `## Next` — the
exact next action, what waits on the owner, what is unverified, **at most eight lines**, no hash,
no date in either. Add **one** History entry at the top of `## History`:
`### YYYY-MM-DD — <gist> (<first>..<last>)`, the commit range. What no longer fits moves there
verbatim. Then rewrite `documents.now` in the format of
`${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/now.md`, naming the unit in play.

A unit the work needs and the units folder lacks is proposed to the user, not created unasked.
Markers: ✅ ran for real **and** checks green · ⚠️ say which half is missing · 🚧 in progress ·
❌ broken. A ✅ that is not is worse than no marker.

**With a slug, a finished queue is archived**: when
`python3 ${CLAUDE_PLUGIN_ROOT}/lib/work_next.py <slug> --all` shows every item `done`, `git mv`
its folder under `documents.archive`, put `> SUPERSEDED <date> — history only` above each file's
first line and change nothing else, record the queue where step 3 wrote what it advanced, and fix
every citation of the old path as step 2 does. A queue with an `owed` item stays: its boxes wait
on the owner.

## 4 — memory

Memory takes **only lessons about working with the owner**. A procedure goes into its skill, a
decision into a `D-` file, a project fact into the repository. Where something is deployed stays
out of memory: ask the machine each time.

## 5 — check, commit, move the cursor

Read each knowledge file this work changed beside its template, and Grep every ID it took: each
is defined exactly once. A handoff that does not match its templates is not finished. Commit in
slices — a finding about the world separately from the change that found it. Once everything is
committed, move the cursor to this commit; it lives in this working tree's git refs, so it is
never committed and every working tree keeps its own:

```bash
git update-ref refs/worktree/wiqrug-update-knowledge HEAD
```

## Unattended — `--unattended`

The unattended loop's closing session, with nobody watching. It does step 1's To file lines and
step 5's check and commit **only** — no Now and Next, no archive, no memory, no cursor: a memory
written with nobody watching is one nobody reviews.

- Write in **whichever file** a line needs, an item's notes included — no item owns a path — and
  when step 5's check names a fault, fix it there as its own commit, or say in one line what you
  could not fix.
- ⚠️ **A `D:` line is never filed**: nothing goes into `documents.decisions` — not as a decision,
  not as a paragraph added to one. Leave the line unticked and append
  ` — not filed: a decision is the owner's, asked in the run's report`. The loop undoes any change
  there and reopens a `D:` line this session ticks.
- The one change allowed in a decision file: a dead path a check names, fixed inside its
  backticks and nothing else.

## 6 — report

Plain words first: what happened and what is needed. Then **what changed** · **what was filed**
· **what is unverified, and why** · **what waits on the owner**, their commands in full, one a line.
