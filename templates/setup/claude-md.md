# <NN>: CLAUDE.md — <C-number and its one-line summary | a new CLAUDE.md>

Advances:   wiqrug-setup
Blocked by: 01
Touches:    CLAUDE.md

<!-- wiqrug template: one ticket per ACCEPTED numbered proposal, in its number order, or one
ticket for a new CLAUDE.md. A declined proposal gets no ticket. Always the last tickets: every
other answer feeds them. -->

## What to build

<For a proposal:> Apply proposal <Cn> exactly as accepted, and nothing else in the file:

```text
current: <the line it changes, verbatim — or: none, an addition>
new:     <the accepted text, verbatim — or: removed>
```

<For a new CLAUDE.md:> Write `CLAUDE.md` in the `writing-for-agents` style — short, invariants
first — from the outline the user confirmed, below. It names the settings file at
wiqrug.md in the .claude folder as where every wiqrug skill reads the project's layout, the "done" command
`<done.command>` and the work queue `<documents.queue>`: setup's final check asks a fresh session
what `CLAUDE.md` requires, and expects those two named.

```text
<the confirmed outline>
```

## Acceptance

- [ ] `grep -qF "<a line the accepted text adds>" CLAUDE.md` exits 0 — or, for a removal,
      `grep -qF "<the removed line>" CLAUDE.md` exits 1
- [ ] `git status --porcelain -- . ':!CLAUDE.md' ':!<the queue folder>'` prints nothing — new files too

## Comments
