# What setup asks

The questions behind the settings file and the project's structure, in the order their answers
depend on each other. `/wiqrug:setup` asks them in the `interview` technique: a round asks every
question here whose prerequisites are settled, each with a recommendation drawn from the audit.
**A question the audit already answers is not asked** — the recommendation is played back
instead, and the user can still change it there.

Every setting named here is explained, with an example, in the plugin's settings example, which
setup's own instructions name; read it before round 1.

## The design tree

| # | Decision | Waits on | Becomes |
|---|---|---|---|
| 1 | What the project is | — | the opening of `CLAUDE.md` |
| 2 | Standard or Full knowledge | 1 | `knowledge.level` |
| 3 | Where each kind of document lives | 2 | `documents.*` |
| 4 | The "done" command | — | `done.command` |
| 5 | Its owed exit code | 4 | `done.owed-exit` |
| 6 | The test framework and its limits | 4 | `tests.framework`, `tests.limits` |
| 7 | Preparing a fresh copy | 4 | `unattended.prepare` |
| 8 | Environments | 1 | `environments.list` |
| 9 | Browser checks | 1 | `browser.check` |
| 10 | The deliverable language | 1 | `language.deliverables` |
| 11 | What an agent never touches | 8 | `agents.never-touch` |
| 12 | Each overlapping project skill | 3 | kept, retired to `documents.archive`, or folded |
| 13 | Each change to an existing `CLAUDE.md` | every other | numbered proposals |

So round 1 is usually 1, 4 and — from what the audit found — whatever of 8 to 10 it leaves open.

## 1 — What the project is

What it does, for whom, and what it is built with — in two or three sentences the user would
put at the top of `CLAUDE.md`. Recommend from the README and the build files; an existing
`CLAUDE.md` that already says it settles this.

## 2 — Standard or Full knowledge

- **Standard** — a glossary, decisions (`D-`), gotchas (`G-`), open questions, and a short
  Now/Next note. Right for a tool, a library, most applications.
- **Full** — adds an evidence ledger of facts (`F-`) and questions (`Q-`), and units: one file
  per part of the system with its Now, Next and History. Right where the business rules are the
  hard part and every claim about them needs its source.

Recommend Standard unless the user describes rules that come from people outside the team.

## 3 — Where each kind of document lives

One question per kind — `queue`, `specs`, `decisions`, `gotchas`, `glossary`, `questions`, `now`,
`research`, `archive`, and at Full `ledger` and `units` — each answered **an existing folder or
file, a new one, or none**. Recommend an existing folder wherever the audit found one that
already holds that kind (an adr folder holds decisions); otherwise a new one under one documents
folder. `queue` and `archive` are never `none`: the loop needs the queue, and retiring a skill
needs the archive.

**Nothing is moved without asking.** An existing document that would fit a new folder better is
its own question — move it, or point the setting at where it is — never a side effect.

## 4 — The "done" command

The one command that says the work is in a state to hand over: build, linters, tests. Recommend
the audit's proposal and show which files it came from; where the build files disagree with
what CI runs, recommend what CI runs. A project with no tests yet still needs a command — say what
it would be, or `none` with the consequence: nothing an agent builds is proved by a command.

## 5 — Its owed exit code

Whether the "done" command has an exit code meaning "every check I could run here passed; one
needs a running environment". Most projects have none — recommend `none` unless the command is a
script that already distinguishes them.

## 6 — The test framework and its limits

The framework `/wiqrug:tdd` writes tests with — recommend the audit's — and its **limits**: what
a test may not need, one per line. Ask what the test run can rely on where an unattended copy
builds: a network, a database, a service, a secret. A limit is a line every test is held to, so
recommend only what the existing tests already respect.

## 7 — Preparing a fresh copy

The commands that make a fresh clone ready to build and test — installing dependencies,
generating files — in order, or `none`. Recommend from the lock files and the build files
(`npm ci`, `uv sync`, a virtual environment and its install).

## 8 — Environments

Where the project runs, one per line: its name and what it is. `none` for a project that only
runs where it is built.

## 9 — Browser checks

Whether the project has screens, and if so the command that proves one in a real browser, or
`none`. A project with screens and no such command is told what that costs: a screen is then
proved only by a person looking.

## 10 — The deliverable language

The language a document handed to the project's users is written in. The knowledge base itself —
code, comments, these documents — stays in one language; ask which only if the audit shows two.

## 11 — What an agent never touches

Paths, systems and actions no session may change, whatever its ticket says: a production
database, a secrets file, a vendored folder, a deploy. Recommend from the ignore file, the
environments and any rule the audit found in another tool's files.

## 12 — Each overlapping project skill

For every project skill or command the audit lists as overlapping one of wiqrug's, one question:

- **keep** — both stay; the project's is called by its own name, wiqrug's as `/wiqrug:<name>`;
- **retire** — the project's moves into `documents.archive`, untouched, so it can be restored;
- **fold** — its project-specific parts (a command, a folder, a rule) become settings or a
  `CLAUDE.md` line, then it is retired.

Read the skill before recommending: one that only restates the method is retired; one that
carries the project's own commands is folded.

## 13 — Each change to an existing `CLAUDE.md`

Asked last, because every other answer feeds it. Each change is its own numbered proposal —
**C1**, **C2**, … — quoting the current line where there is one, the new text, and why: an addition
(a rule from another tool's file worth keeping, a pointer to the settings file), a rewording, a
move. **Nothing in it is removed without its own number**, and the user answers each one.

A project with no `CLAUDE.md` gets one proposal instead: a new one, short and invariants first,
in the `writing-for-agents` style — its outline played back, not its full text.

Other tools' instruction files are read for rules worth keeping and never edited: a rule from one
reaches `CLAUDE.md` only as a numbered proposal.
