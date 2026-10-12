---
name: tdd
description: Use when a box needs code and tests, when fixing a bug test-first, or when unsure what a test here should look like.
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

# Test-driven development

The red → green loop, and what makes it produce tests worth keeping. **`/wiqrug:implement` owns
the box; this skill owns the slices inside it**: each slice is one test that goes red, then only
the code that turns it green.

Name tests and fixtures with the glossary's words (`documents.glossary`, unless it is `none`), so
a test reads as a sentence about the thing.

## The project's rules for a test

The settings above hold them; a test that breaks one does not belong in this project.

- **`tests.framework`** is what every test is written with. Find where the project's existing
  tests live and how one test is run alone before writing the first, and follow their layout —
  never a second framework beside the first.
- **`tests.limits`**, one line each, is what a test may not need — a network, a database, a
  clock, a credential. A limit is why the suite can run anywhere, so what crosses it is stood
  in at its boundary: [mocking.md](mocking.md). With `none`, the project set no limit; a test
  that needs something slow or shared still says so in its name.
- **Test the decision, not its wrapper.** The decision is a function you call with values and
  read a value back from, and its extremes — blank, zero, one, the boundary date, the missing
  record — are where the bugs are. A rule buried in a request handler or a component cannot be
  tested without them; moving it out is part of the slice.
- **Behaviour through the public interface.** A test that breaks when the code is refactored
  and the behaviour has not changed is testing the implementation. Examples: [tests.md](tests.md).

## Seams: where tests go

A **seam** is the place a test observes behaviour at, without reaching inside. Before choosing
where a test goes, or when a slice makes you want to change a module's interface, call the Skill
tool with `wiqrug:codebase-design`: its words are the ones `/wiqrug:to-spec` agreed the seams in.

**Test only at the seams agreed in the understanding.** `/wiqrug:to-spec` writes them under
`## Where it is tested` in `<documents.queue>/<slug>/understanding.md`. Read that section before
the first test.

A slice no listed seam reaches is information: attended, ask the owner; unattended, test at
that code's own public interface — in its existing test file, where it has one — and append under
the item's `## Comments`:

```text
Spec question: box <n> needed a seam understanding.md does not list: <the seam, and why no listed one reaches it>
```

The report then asks the owner, and the reviewer reads it as a gap in the spec, not a defect.

With no such section, the seams are the ones the item's boxes name, and the report says so.

## Expected values come from an independent source

The expected value in an assertion comes from **an independent source**, never recomputed the way
the code computes it:

- **the specification** — a worked example in the understanding, an item, or a decision
  (`documents.decisions`);
- **a recorded fact** — in a Full knowledge base, the worked example an `F-` item in
  `documents.ledger` records;
- **the real thing** — what the system this code talks to actually returned, captured once and
  anonymised;
- **a reference** — a published table, a standard's test vector, the output of a tool the
  project already trusts for this answer.

The test's docstring or comment cites the source, so a reader can open it and check the number.
A known literal worked out by hand from the rule is acceptable when the rule is cited; a value
derived by calling the code, or by re-running its formula in the test, is not — it passes by
construction.

**Where no source gives the number, the test does not invent one.** Blank is not zero: the test
asserts that the code refuses, or flags the default it used, and the missing answer is an open
question for `wiqrug:file-knowledge`.

## Anti-patterns

- **Implementation-coupled** — mocks the project's own modules, calls a private helper, or
  verifies through a side channel (reading the stored record back instead of calling the
  interface). The tell: it breaks on a refactor that kept the behaviour.
- **Tautological** — the expected value restates the implementation: a sum recomputed with the
  same `sum()`, a constant asserted equal to itself, a snapshot captured from the code's own
  output. It can never disagree with the code.
- **Horizontal slicing** — every test first, then every line of code. Bulk tests describe imagined
  behaviour and go insensitive to real changes. Work in vertical slices: one test, one minimal
  implementation, repeat; each slice answers to what the last one taught.

## The loop

1. **Red.** Write one test at an agreed seam. Run that test alone and see it fail — **for the
   reason you expect**: an assertion on the value, not an import error or a typo.
2. **Green.** Write only enough code to pass it. No speculative branch for a later test.
3. **Next slice.** One seam, one test, one minimal implementation per cycle.

Refactoring is not part of the loop: it belongs to the review, `wiqrug:review-change`.
