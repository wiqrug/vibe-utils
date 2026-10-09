---
name: implement
description: Build one work item and prove it, or drain a whole queue unattended. Ticks an acceptance box only because a command exited 0.
argument-hint: "<the item's path in the project's queue>"
disable-model-invocation: true
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

# Implement

One item — the unit that can be proved and reverted on its own. Every fact about the project
comes from the settings above: the queue is `documents.queue`, the "done" command is
`done.command`. Run `git status --short` first: work already in the tree is somebody's.

## 1 — read the item, and only then the code

`Advances:` names what the item moves: in a Full knowledge base, a unit in `documents.units` —
read its Now, since the repository may have moved since the item was written; in a Standard one,
`documents.now`. `Cites:` names the records it rests on — `G-` in `documents.gotchas`, `D-` in
`documents.decisions`, and in a Full knowledge base `F-` and `Q-` in `documents.ledger`. Read them
before the code, since the obvious implementation of an item resting on a trap is the one that
already failed.

**An item whose `Waits on:` names an open question or a decision only the owner can make is not
started**: say which it waits on and pick another item — work built on an unmade decision is
thrown away.

An `Attended: <why>` header is the item saying the owner builds it: the unattended loop never
offers it, and `/wiqrug:implement` typed by the owner builds it like any other.

**An item names no files**: find them from the code, and change what the item's behaviour
needs, wherever it lives. Its reviewer judges anything unasked-for against the spec, not against
a path list. An older queue's item carries a `Touches:` line; read it as a hint, never as a
fence. Nothing in `agents.never-touch` is written, whatever the item says.

## 2 — fails first: run the item's own boxes before any code

Before a line is written, note the commit you start from (`git rev-parse HEAD` — step 6 reviews
the diff since it), run every box's command there from the repository's root and **see each one
fail**. Not a box **for a person**, and not an older queue's "done" box —
`` `<done.command>` exits 0 ``. A browser-check box needs the project running, so run it only
when the item's first slice brings it up anyway.

**A box that already passes never stops the item**, but it cannot tell finished from
unstarted, so find out why it passes — the commit or the earlier item that delivered it — and
write one line under `## Comments`, in exactly one of these two forms:

```text
Fails first: box <n> passed at <short sha> before any work — delivered by <the commit or item>: <the evidence>. Ticked.
Box <n> worded wrong: <why it passes with none of this item's work, and what it should say instead>
```

The first when earlier work really delivered what the box asks: tick the box, and the item's
reviewer checks the claim. The second when the box is simply worded wrong: leave it unticked —
it is owed, holds nothing up, and goes to the report as a question for the owner. Either way,
build the rest of the item. `/wiqrug:to-tickets` wrote each box with the clause that says what
would show it false; this step is where that clause is run.

A box the loop added — *the code gate passes at this item's last commit* — means an earlier run
left this item failing the code gate. It names its command and its log: make it pass like any
other box.

## 3 — build the smallest thing that satisfies one box

Work box by box, not file by file. Before opening an area of the code, read the project's traps
for it (`documents.gotchas`). The two that cost most anywhere are **blank is not zero** — a value
that could not be computed is never a plausible default — and **two idioms for one job**: a
second copy of something that exists means one is wrong and nobody knows which.

**A box that needs code: call the Skill tool with `wiqrug:tdd`** before its first test. It owns
the red → green slices inside the box, with the project's test framework, at the seams the
understanding agreed, with expected values from an independent source.

**A box still red after two honest attempts, or red for a reason you cannot name, is a bug:
call the Skill tool with `wiqrug:diagnosing-bugs`** before a third attempt. It builds the loop
that goes red on this failure first, then tests hypotheses against it.

## 4 — tick a box only because a command exited 0

`wiqrug:verify` runs the "done" command — `done.command` — reports it, and names what it did
not run. An item carries no box for it: the command is the code gate, and the loop runs it
itself.

⚠️ **A box is ticked because its named command ran in this session and exited 0** — not
because the code looks right or another check passed. The "done" command exiting with
`done.owed-exit` is not a tick: it passed everything it could check, and the rest is owed.

**Unattended, only code can stop the item**: after the session the loop runs the code gate —
the "done" command — at the item's last commit, and again after the item's review is fixed.
Leave an older queue's "done" box to the loop, which settles it on the branch tip.

What a person has to judge by looking — a screen, a wording — goes in the item's
`## Check in the browser`, which the run's report gathers under *For you to check*. An older
queue puts it in a box **for a person** instead: that box stays unticked, and the queue reader
reads those words — an item whose only open boxes are a person's is `owed`, not unfinished, and
the items after it may start.

**When the item changes a screen, open [screens.md](screens.md) now**: the check that proves it,
where the project has one, and the owner's steps for what only a person can judge.

## 5 — commit the slice, and say what changed in the item

One undoable change per commit. **A finding about the world commits separately from the work
that found it**, or reverting the item silently reverts the knowledge.

Then, in the item file: tick what was proved, and append to `## Comments` what a later reader
would otherwise have to re-derive — what was tried and abandoned, what the code turned out to
already do. ⚠️ **Never backtick a path that will not exist later** — a scratch, anything under
/tmp or under logs/, which git ignores: write it as plain text. A later reader follows a
backticked path as a citation, and finds nothing.

If the work produced a trap, a fact, a term, a decision or a defect, call the Skill tool with
`wiqrug:file-knowledge` the moment it is learned, as its own commit. An item is not the place for
knowledge that outlives it — except **unattended**, where knowledge is filed once, by the run's
closing session: there the finding goes into the item's `## To file` as one unticked line typed
by its kind (`G:`, `term:`, `D:`, `defect:`, `answer:`, and in a Full knowledge base `F:` and
`Q:`), and that session files it after the last item. A To file line is not an acceptance box;
the closing session ticks it.

## 6 — review the item's diff, unless the session is unattended

After the last box's slice is committed, and before the item file's final commit and the
report, call the Skill tool with `wiqrug:review-change`, the base being the commit step 2 noted
and the spec the item file — the session that wrote the code finds only what it already agreed
with.

**Skip it when `AFK_SOURCE_TREE` is set** in the session's environment. The unattended loop sets
it on every session it starts, so a session that sees it is unattended — and the loop runs this
same review itself, as a session of its own, the moment this one ends, then resumes this session
with the findings.

Check each finding before acting on it, by the loop's evidence rule ([afk.md](afk.md)):

- **confirmed** — the code does what the finding says. Fix it as its own slice, then run the
  "done" command again.
- **refuted** — only with a command and its output, or the quoted lines that contradict it.
- **spec question** — the finding is a gap in the spec: the item or `understanding.md` never
  decided it. Write no code for it; append `Spec question: <the question, for the owner>` under
  `## Comments` and commit it. The run's report lists it under *Spec questions*.
- **unchecked** — anything else. A "refuted" without that evidence is unchecked.

The report lists every finding with its verdict: the fixed ones with their commit, the refuted
ones with their evidence, the spec questions and the unchecked ones as open.

## 7 — the next item, or stop

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/work_next.py <slug> --all
python3 ${CLAUDE_PLUGIN_ROOT}/lib/work_next.py <slug>
```

Where `python3` is not the name, `wiqrug-check --python` prints the one this machine has. The
queue reader decides readiness from the files: ready when every `Blocked by:` is done and
`Waits on:` is empty. An `Attended:` item is offered here and never to the loop
(`--unattended`). On a malformed item it exits `2`, so a loop cannot skip what it cannot judge.

**Between items, clear the context**: the next item was sized for a fresh window, and a window
carrying the last one's reasoning is where two items quietly merge.

## Unattended

Run from anywhere in the project, the loop drains a whole queue with nobody watching, one fresh
session per item, in a throwaway worktree, ending in a branch and a report. Hand the owner this
command for the slug, the plugin's folder substituted, with `--dry-run` first:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/implement/afk.sh <slug> --dry-run
bash ${CLAUDE_PLUGIN_ROOT}/skills/implement/afk.sh <slug>
```

`--environment <name>` is required when `environments.list` names more than one. The flags, the
usage-limit wait, the endings, the evidence, the report and the review: [afk.md](afk.md).

## Report

```
item        <path> — <its title>
fails first <n> of <m> boxes ran and failed at <sha> — or: box <n> passed: delivered by <…>, ticked | worded wrong
proved      <box> — <command, exit code>
NOT proved  <box> — <why: needs a browser, needs a decision, needs an environment>
review      <n> confirmed and fixed, <n> refuted, <n> spec questions, <n> unchecked — or: skipped, unattended
commits     <one line each>
next        <the command>
```

What was not proved is written as not proved. The record is the item file — its ticked boxes and
`## Comments` — and what `wiqrug:file-knowledge` filed; this report is the session's summary of
them. `python3 ${CLAUDE_PLUGIN_ROOT}/lib/afk_report.py <slug> --out <file>` renders the queue's
state into a file, when the owner wants one outside the session.
