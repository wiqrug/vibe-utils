---
name: to-tickets
description: Cut a confirmed understanding into tracer-bullet work items in the project's queue, for /wiqrug:implement or the unattended loop.
argument-hint: "<slug>"
disable-model-invocation: true
---

!`wiqrug-check --skill`

If the first line above begins neither `wiqrug: set up —` nor `wiqrug: setup in progress`, show
that line to the user and stop. Setup builds itself from a queue, so this skill goes on while it
is in progress, with only `documents.queue` set.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

# To tickets

The third step of the loop: `/wiqrug:grill-with-docs` → `/wiqrug:to-spec` →
`/wiqrug:to-tickets` → `/wiqrug:implement`. One input — `<documents.queue>/<slug>/understanding.md`,
which `/wiqrug:to-spec` wrote, or a report of gaps — and one output: a numbered set of items in
the same folder. **The shape of an item and the meaning of each header are
[items.md](items.md)** — open it now; this skill is how the set is arrived at.

**This skill writes items; `/wiqrug:implement` builds them.** An item small enough to just do is
still written down first: the queue makes the work resumable by a session that was not here.

## 1 — cut along what can be proved, not along the code's layout

An item is one **vertical slice that can be verified on its own**: could a session with no
memory of this conversation finish it and know that it had?

| cut it here | not here |
|---|---|
| one behaviour a command can check | one layer — "the backend part", "the frontend part" |
| one screen doing one new thing | one file, however large |
| one migration plus the code that reads it | a migration on its own, which proves nothing |

⚠️ **A layer is not a slice.** Two items that only work once both are done are one item, and
the first of them will be reported as finished.

⚠️ **Size it to finish under about 150k tokens of context.** Past that a session reasons
worse, and one that compacted rebuilds its understanding from its own notes; "one fresh
context window" overshoots it more often than not. A file read whole, a screen checked and a
full test run each cost context, so an item with more than one is suspect. Cut a bigger one
along the table's lines:

- **two behaviours** — two items, the second `Blocked by:` the first;
- **a reshaping the behaviour needs** — its own item, first, proved by the tests that already
  exist;
- **one change repeated across the codebase** — expand (add the new way beside the old), migrate
  (move callers over, a batch per item), contract (remove the old way);
- **a screen and what feeds it** — apart only if each can be checked alone; otherwise one item,
  with less of the screen in it.

## 2 — show the owner the breakdown, and wait

Before any file is written, put the proposed set in front of the owner:

```text
01  <title>
    delivers:   <what the owner can see or run when it is done — behaviour, not a layer>
    blocked by: <numbers, or "nothing — can start now">
    waits on:   <an open question or the owner's decision, or nothing>
    attended:   <foundation — the reason, or nothing>
```

Propose `attended: foundation` on every **foundation** item — one that adds or changes the
schema or the shared decision code the rest of the queue builds on, or that most of the queue
depends on through `blocked by` — with its reason. It is built attended because a wrong
call there is the one every later item rests on.

Then ask, in one round, each with your recommendation:

```markdown
❓ **Q1** - **Size**: is any item too big for one session, or too small to be worth one?

➡️ <your recommendation>

---

❓ **Q2** - **Order**: is every `blocked by` real — does each item depend only on what truly gates it?

➡️ <your recommendation>

---

❓ **Q3** - **Merge or split**: should any two be merged, or any one split?

➡️ <your recommendation>

---

❓ **Q4** - **Attended**: is each `attended: foundation` one the queue truly rests on, and is any
item missing one?

➡️ <your recommendation>
```

Iterate until the owner approves the breakdown.

**Write no item until the owner says yes**: every later item builds on a wrong split. A
`delivers:` line naming a layer ("the endpoint", "the model") is fixed before the list is shown.

## 3 — fill in every header, and mean it

`Advances:` is required on every item. **An item describes behaviour and names no file path** —
not in `## What to build`, not as something a box writes: the session that builds it finds the
files from the code, and the Spec reviewer judges *unasked-for* against the spec. **Each item's
`## What to build` names the user stories it serves**, by their number in `understanding.md`; a
story no item serves is either out of scope — say so — or a missing item. Then:

- **`Advances:`** — in a Full knowledge base, the unit slug in `documents.units`; in a Standard
  one, the work's own slug.
- **`Blocked by:`** — ordered so that `01` can start now. Something outside this folder is a
  `Waits on:`, not a `Blocked by:`.
- **`Waits on:`** — an open question in `documents.questions` (a `Q-` in a Full knowledge base)
  or a decision only the owner can make, filed as an open question naming the owner through the
  Skill tool `wiqrug:file-knowledge` — left for the owner to resolve, so no run builds on it.
- **`Attended:`** — only on an item the owner has to build with `/wiqrug:implement` themself,
  never the unattended loop, and why, in one line: `Attended: foundation` where the owner
  approved it in step 2, or another reason, `Attended: changes the loop that drives this run`.
  The loop never offers it and what depends on it waits. Something a person checks by looking is
  not a reason for it — that goes in the item's `## Check in the browser` section.
- **`Cites:`** — the existing `G-` and `D-` (and in a Full knowledge base `F-` and `Q-`) the
  intent rests on; a claim with no record yet gets an open question through `wiqrug:file-knowledge`.

There is no `Touches:` line, and nothing under `agents.never-touch` is named as work to do.

## 4 — every acceptance box names a command, and what would show it false

```markdown
- [ ] `<the command that runs this item's new tests, selected by name>` exits 0
```

A test the item creates is named by what the framework selects it with — its name or its module —
never as a backticked file path: the file does not exist until the item is built, and an item
names no path.

Not *"offers work correctly"*. A box that cannot name a command is a sign the item is not yet
understood — or it is a person's check, which goes in the item's `## Check in the browser`
section, never in a box. **No item carries a box for the "done" command**: the loop runs it
itself after every item, as the code gate.

**A box that already passes proves nothing.** For every box, name what would show it false,
in a clause — a test file the item creates is missing, which counts if it asserts the new
behaviour. **"Today" is the commit the item starts from** — after every item it is `Blocked by:`.
A box that runs a test file an earlier item creates passes there with none of this item's work:
select the new cases by name, and make sure `tests.framework` exits non-zero when a selection
matches nothing. A browser-check box needs the project running, so name the assertion today's
screen would fail. This step only checks that every box can be read — a command, and its clause —
and runs none of them: `/wiqrug:implement` runs each box before any code (*fails first*), against
the commit it actually starts from. A box that already passes there is ticked with the evidence of
the earlier work that delivered it, or noted as worded wrong for the report ([items.md](items.md))
— never a reason to stop the item. A guard box — *"keep what exists"* — passes today by
construction, so it is never a box of its own: fold it into a box that fails today, as a clause
of that box's command.

**Every item ends with `## To file` and `## Comments`**, both empty — [items.md](items.md)'s
shape. `## To file` is where an unattended session writes what it learned and could not file;
it is never an acceptance box, so `/wiqrug:to-tickets` writes no line there.

**When an item changes a screen, open [screens.md](screens.md) now**: its one box for the screen,
where the project has a browser check, and the section the owner follows in the browser.

## 5 — have it read by somebody who was not here

Hand the folder to the `reviewer` agent wiqrug ships (the Agent tool, `wiqrug:reviewer`):

```text
read <documents.queue>/<slug>/ against understanding.md and report
  — any acceptance criterion in understanding.md that no item covers
  — any user story in understanding.md that no item serves
  — any item that cannot be finished alone, and which other item it needs
  — any file path an item names as something to write
  — any item whose boxes cannot be checked by a command
  — any box for a person, or any box for the done command
  — any box that restates the request rather than naming what it observes
  — any box that would already pass once the items it is Blocked by are built
```

It reads and reports — a review of your own decomposition finds what it already agreed with.
Fix what it finds; renumber if the order changed.

## 6 — state the queue

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/work_next.py <slug> --all
```

Every item with its state, computed from the files; it finds the queue through the project check,
whatever folder the session stands in. A count here must equal the items behind it.

## 7 — hand over what the owner runs

Commit the queue first — the unattended loop builds in a fresh copy cut from `HEAD`, and an
uncommitted queue reads "nothing ready", exactly like a drained one:

```bash
git add <documents.queue>/<slug>
git commit -m "Work items for <slug>"
```

Then print the unattended loop's command for this slug as `/wiqrug:implement` gives it, the
paths substituted, so it pastes into any terminal. The run attempts **5 items** by default —
`--max <n>` on the `afk.sh` line changes it — and ends in a branch and a report: what was built,
reviewed and proved; *for you to check*; the spec questions. What needs the owner never stops
the queue.

## Report

How many items · which can start now · which wait on a decision, naming it · which are
attended, and why · what
`understanding.md` asked for that no item covers, if anything survived step 5 · any box without
its clause · and the commands from step 7, plus `/wiqrug:implement <the first item>` to build one
with somebody watching.
