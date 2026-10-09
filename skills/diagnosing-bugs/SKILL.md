---
name: diagnosing-bugs
description: Diagnose a hard bug or a slowdown with a tight loop that goes red first — reproduce and minimise, three to five falsifiable hypotheses, instrument, fix with a regression test, clean up, file the trap. Use when something "should work" and does not, throws, fails, gives a wrong answer or is slow.
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

# Diagnosing bugs

A discipline for the bug that did not fall to the first look. Skip a phase only with a stated
reason. **Before phase 1, read the project's traps** — `documents.gotchas` in the settings above,
unless it is `none` — for the area you are in: a trap already filed is a bug already diagnosed,
and its *instead* is the fix.

## What may be shown

This skill shows commands, outputs and captured artifacts, so these come first:

- **Never read a secret.** Run the tool that resolves the credential inside its own process;
  never print, `grep` or `source` a credential file to build a loop. An error body can quote the
  credential it rejected — quote only the lines with the signal.
- **No personal data in anything shown or committed.** A real input stays where it lives,
  outside the repository. A loop over it prints **counts and reason codes, never a record**; a
  regression fixture is anonymised — the fields and their format kept, the person replaced.
- **Nothing in `agents.never-touch`** is changed to build a loop, and a loop that would write to
  a live system is not a loop.

If what may be shown is not enough to diagnose it, say so and ask the owner.

## Phase 1 — a loop that goes red

**This is the skill.** With a tight pass/fail signal that goes red on *this* bug, the cause will
be found; without one, reading more code will not find it. Spend the effort here.

### The loops a project offers, roughly in this order

| loop | how | reaches |
|---|---|---|
| **one test** | one test of `tests.framework`, run alone — the project's tests show how | a decision in the code — the tightest loop there is (`/wiqrug:tdd`) |
| **a scratch script** | a script outside the repository that calls the code with the failing input and prints the symptom | a decision with no test yet, or a real input's shape without copying it in |
| **a request** | the project run locally, and one request sent to it | a route, a stored change, a cookie, a migration against data |
| **the browser check** | `browser.check`, when it is not `none`, on the one page with the bug's assertions | what a person sees |
| **the "done" command** | `done.command`, or the one part of it that fails | the whole build, when the failure is only seen there |
| **a measurement** | time the one operation, a profiler, the database's own query plan | speed — a slowdown is measured, not reasoned about |

Scratch scripts and copies of the running project live outside the repository, in the system's
temporary folder: a loop leaves nothing behind in the tree.

A bug a person has to see — a screen only they can judge — is not driven by hand: the check
proves what it can, and the owner gets concrete steps for the rest.

### Tighten it

Once there is *a* loop: faster (one test, not the module; one page, not the suite), sharper
(assert the symptom, not "did not crash"), more deterministic (pin the date, fix the seed, a fresh
start every run). A thirty-second flaky loop is barely a loop; a two-second one is the tool.

**Non-deterministic bugs:** the aim is a higher reproduction rate, not a clean repro — loop the
trigger, add load, narrow the timing window, until it is red often enough to work against.

**When no loop can be built,** stop and say so, with what was tried. Ask the owner for access to
what reproduces it, a captured artifact (anonymised, and left outside the repository if it holds
people), or leave to add temporary instrumentation. **No loop, no hypothesis.**

### Done when

One named command, already run at least once with its output shown, that is:

- [ ] **red-capable** — it drives the real code path and asserts the symptom that was reported;
- [ ] **deterministic** — the same verdict every run, or a pinned high rate for a flaky bug;
- [ ] **fast** — seconds, not minutes;
- [ ] **agent-runnable** — it needs nobody at a keyboard.

Reading code to build a theory before this command exists is the failure this skill prevents.

## Phase 2 — reproduce and minimise

Run the loop and watch it go red. Confirm it is **the reported failure**, not a neighbour —
wrong bug, wrong fix — that it reproduces across runs, and capture the exact symptom: the error,
the wrong answer beside the right one and where the right one comes from, the time in ms.

Then cut: inputs, records, configuration, steps, **one at a time**, re-running after each. Stop
when every remaining element is load-bearing — removing any one turns it green. The minimised
repro is the regression test in phase 5.

## Phase 3 — hypothesise

**Three to five ranked hypotheses before testing any.** One anchors on the first plausible idea.
Each is falsifiable:

> If <X> is the cause, then <changing Y> makes the bug disappear, and <changing Z> makes it worse.

A hypothesis with no prediction is a vibe: sharpen it or drop it. Show the ranked list to the
owner before testing — they often re-rank it at once. Unattended, write it in the item's
`## Comments` and carry on with your ranking.

## Phase 4 — instrument

Each probe answers one prediction from phase 3; **change one variable at a time**. Prefer a REPL
or a debugger to a log, and a log at the boundary that separates two hypotheses to a log
everywhere. **Tag every debug line** — `[DEBUG-a4f2]` — so cleanup is one search. A debug line
never prints a person, a credential or a token.

**Slowness is measured, not reasoned about:** take a baseline number first, vary one thing, and
see whether the time tracks the thing you blame. A measurement also rules suspects out, which
reading cannot.

## Phase 5 — fix, with a regression test

Write the regression test **before the fix**, at a **correct seam**: one where the test
exercises the real bug as it happens at the call site, with its expected value from an
independent source (`/wiqrug:tdd`). Then: watch it fail, fix, watch it pass, re-run the phase 1
loop against the original, un-minimised case.

**When no correct seam exists, say so** — in the item's `## Comments`, the commit message and
the trap filed in phase 6. A test at a shallower seam would pass while the bug lived on; the
architecture that keeps the bug from being locked down is itself the finding.

## Phase 6 — clean up and file it

- [ ] the phase 1 loop no longer goes red;
- [ ] the regression test passes, or the missing seam is written down;
- [ ] a search for `DEBUG-<tag>` finds nothing;
- [ ] scratch scripts, captured files and copies of the running project are gone, and none was
      ever inside the repository;
- [ ] **the commit message states the cause** — the hypothesis that held — so the next debugger
      learns it from the history;
- [ ] **the trap is filed through `wiqrug:file-knowledge`**, with the regression test as what
      enforces it, as its own commit. Unattended, it is a `G:` line in the item's `## To file`
      instead, naming the test.
