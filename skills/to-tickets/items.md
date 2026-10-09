# Work items — the unit of work between a specification and a commit

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

The shape `/wiqrug:to-tickets` writes and `/wiqrug:implement`, the unattended loop and the queue
reader (`${CLAUDE_PLUGIN_ROOT}/lib/work_next.py`) read. A project keeps no copy of this page.

A **work item** is one slice of work, sized to fit a single fresh context window, that answers
*what do I do next, and can I do it yet?*. It is finished and then archived. What it moves — a
unit in a Full knowledge base, the Now note's Next in a Standard one — is the durable subject
that answers *where does this stand?*, and outlives every item. The two are related by citation,
not by containment: an item names what it advances, and that records the item once it lands.

## Shape

One folder per piece of work, `<documents.queue>/<slug>/`, holding `understanding.md` from
`/wiqrug:to-spec` and then `<NN>-<title>.md` per item, numbered from `01` in dependency order,
the title lowercase-hyphen.

```markdown
# 04: The order form refuses a blank price

Advances:   ordering
Blocked by: 02
Waits on:   pricing-owner
Attended:   foundation — the order rules every later item prices with
Cites:      D-007, G-012

## What to build

Two or three sentences of intent — behaviour, never a file — and the user stories it serves by
number. No file paths, no line numbers and no code: they go stale inside a week, a reader cannot
tell that they have, and the session that builds it finds the files from the code.

## Acceptance

- [ ] `<the command that runs this item's new tests, selected by name>` exits 0

## Check in the browser

<only on an item that changes a screen: what the owner should see, then the steps>

## To file

<only when a session learned something it could not file: one typed line each>

## Comments

<appended as work happens, newest last>
```

## The five headers, and what each one is for

| header | required | what it does |
|---|---|---|
| `Advances:` | yes | what this item moves: a unit slug (Full) or the work's slug (Standard). An item that advances nothing is a task nobody asked for |
| `Blocked by:` | — | item numbers in this folder. A missing dependency is the cheapest bug to prevent and the most expensive to find |
| `Waits on:` | — | an open question, or a decision only the owner can make, named. **The unattended loop never builds these** |
| `Attended:` | — | why the owner builds it with `/wiqrug:implement` — `foundation`, the schema or shared decision code the queue rests on, approved with the breakdown. **The unattended loop never offers it**, and what depends on it waits. With no reason it is malformed |
| `Cites:` | — | the `G-`, `D-` (and in Full, `F-`, `Q-`) records the intent rests on. A permanent ID is what lets a later reader check the reasoning rather than re-derive it |

A header's value of `-`, `—` or `none` means it has none. A malformed item — no title, no
`Advances:`, no acceptance box, an `Attended:` with no reason, or a `Blocked by:` naming no
item — stops the queue reader with exit 2, never "not ready": a loop that skipped it politely
would drain the queue and report success.

**An item carries no `Touches:`, no box for the "done" command and no box for a person.** The
loop runs the done command itself after every item, as the code gate; what a person judges goes
in `## Check in the browser`, which the report gathers. An **older queue** — written before items
dropped them — keeps working: its `Touches:` is read past, and its person's boxes, its `- [~]`
boxes and its done box (once anything else on the item is ticked) are **owed**: the item counts
as settled for `Blocked by:`, and the loop's report lists each such box under *For you to check*.

**`## To file` holds what an unattended session learned and left for the run's closing
session.** One unticked line per finding, typed by its kind and written in the words it would be
filed with: `G:` a trap, `F:` a fact, `Q:` a question, `answer:` an answer to an open question,
`term:` a glossary term, `D:` a decision, `defect:` a defect left unfixed. The loop runs
`/wiqrug:update-knowledge <slug>` once after the last item, which files each line through
`/wiqrug:file-knowledge` and ticks it with where it now lives. **A To file line is not an
acceptance box**: it never holds the item open.

**Three `## Comments` lines are read by the loop**, each by its exact prefix:

- `Fails first: box <n> passed at <sha> before any work — delivered by <what>: <evidence>.` —
  `/wiqrug:implement` found a box that passed before any code because earlier work delivered it,
  and ticked it on that evidence. The item's reviewer checks the claim. **A box that passed
  first never parks an item.**
- `Box <n> worded wrong: <why>` — the box passed before any work and is worded wrong. It stays
  open, is owed, and goes to the report as a spec question.
- `Spec question: <question>` — a review finding that is a gap in the spec, written by the item's
  fix instead of code. The report lists it under *Spec questions*.

The loop may add one box itself: *the code gate passes at this item's last commit* — the done
command failed there and one repair did not fix it. It holds the item open until a session makes
it pass.

⚠️ **An acceptance box names a command, never an intention.** A box may be ticked because a
command ran in this session and exited 0 — that is the whole difference between this and a
checklist. `/wiqrug:implement` refuses to tick one any other way.

⚠️ **`Waits on:` is the header that earns its keep overnight.** An item resting on an undecided
question, handed to a loop nobody is watching, produces hours of confident work built on a wrong
call — the most expensive failure this whole arrangement exists to prevent.

**An item that changes a screen** proves it with the project's browser check where it has one
(`browser.check`), and hands the owner its `## Check in the browser` steps: [screens.md](screens.md).

## Lifecycle

`/wiqrug:grill-with-docs` settles it · `/wiqrug:to-spec` writes `understanding.md` ·
`/wiqrug:to-tickets` writes the items · `/wiqrug:implement` or the unattended loop drains them
one at a time · when every item is done the folder moves, verbatim, under `documents.archive`
with a banner saying it is superseded, and what it advanced records it.
