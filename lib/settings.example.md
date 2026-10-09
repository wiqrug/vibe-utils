# wiqrug settings

This file tells every wiqrug skill where this project keeps things and how it proves work done.
`/wiqrug:setup` writes it as wiqrug.md in the .claude folder at the repository's root, from what
you agreed in its interview; commit it with the project. Only the `ini wiqrug` blocks are read —
by `wiqrug-check`, the one reader — and everything around them is for people: say here *why* a
setting is what it is.

A setting's value is never left blank. Where the project has no such thing, write `none`: a blank
is refused, because nobody can tell a forgotten setting from a deliberate absence. A setting that
holds a list puts one entry per line, each indented under its key. Lines starting with `#` are
comments. Paths are relative to the repository's root, whatever folder a session stands in.

## The version and the state

`version` is the wiqrug version that wrote this file; a skill run with a newer wiqrug says to run
`/wiqrug:setup --upgrade`. `state` is `complete` once setup has finished. While setup is still
building the project's structure it is `setup-in-progress`, and then only `version` and
`documents.queue` need to exist: every skill but setup and `to-tickets` stops with "finish setup".

```ini wiqrug
[wiqrug]
version = 0.1.0
state = complete
```

## Where each kind of document lives

A folder or a file, relative to the repository's root, or `none` where the project keeps no such
document. Setup never moves an existing document to fit these.

- `queue` — the work queue: one folder per piece of work, holding its understanding and its items.
- `specs` — the specifications `/wiqrug:to-spec` writes.
- `decisions` — the decisions (`D-`), one file each.
- `gotchas` — the traps (`G-`): what bit someone, why, and what to do instead.
- `glossary` — the project's words, and the synonyms to avoid.
- `questions` — the open questions nobody has answered yet.
- `now` — the short note of what is true now and what comes next.
- `research` — where `/wiqrug:research` saves what it found.
- `archive` — where superseded documents, and project skills setup retired, are kept.
- `ledger` — Full knowledge only: the evidence ledger of facts (`F-`) and questions (`Q-`).
- `units` — Full knowledge only: one file per part of the system, with its Now and Next.

```ini wiqrug
[documents]
queue = docs/work
specs = docs/specs
decisions = docs/decisions
gotchas = docs/gotchas.md
glossary = docs/glossary.md
questions = docs/open-questions.md
now = docs/now.md
research = docs/research
archive = docs/archive
ledger = none
units = none
```

## How much knowledge the project keeps

`standard` keeps the glossary, decisions, gotchas, open questions and the Now note. `full` adds
the evidence ledger and units, and then `documents.ledger` and `documents.units` may not be `none`.
`/wiqrug:file-knowledge` and `/wiqrug:update-knowledge` write only what this level has.

```ini wiqrug
[knowledge]
level = standard
```

## "Is it done?"

The one command that says the project is in a state to hand over — its build, its linters, its
tests. Run from the repository's root; exit 0 means done.

`owed-exit` is the exit code by which that command says "every check I could run here passed,
and one only a running environment can make is left" — or `none`, when every exit but 0 is a
failure. The unattended loop builds in a fresh copy that no environment runs: on this code it
marks the item's "done" box `[~]`, owed to a person after the merge, instead of failing it.

```ini wiqrug
[done]
command = make check
owed-exit = none
```

## Tests

`framework` is what `/wiqrug:tdd` writes tests with. `limits` are what a test may not need — each
one a line `/wiqrug:tdd` holds every test to — or `none`.

```ini wiqrug
[tests]
framework = pytest
limits =
    no network
    no database
```

## Preparing a fresh copy for an unattended run

The unattended loop builds in a fresh copy of the repository. These commands, run in order from
that copy's root, make it ready — installing dependencies, generating files — or `none`.

```ini wiqrug
[unattended]
prepare =
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
```

## Environments

Where the project runs, one per line: its name, then what it is. `none` for a project that only
runs where it is built.

```ini wiqrug
[environments]
list =
    development — the shared test site, deployed from the dev branch
    production — what users see, deployed from main
```

## Checking a screen in a browser

The command that proves a screen works in a real browser, or `none` for a project without screens
or without such a check.

```ini wiqrug
[browser]
check = none
```

## The deliverable language

The language a document handed to the project's users is written in. The project's own knowledge
base — its code, comments and these documents — is always in the language of this file.

```ini wiqrug
[language]
deliverables = English
```

## What an agent may never touch

One per line: a path, a system or an action no session may change, whatever its ticket says — or
`none`.

```ini wiqrug
[agents]
never-touch =
    the production database
    .env
```
