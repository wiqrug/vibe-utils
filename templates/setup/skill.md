# <NN>: The project's <skill> skill — <retired | folded>

Advances:   wiqrug-setup
Blocked by: 01, <the ticket that lays down documents.archive, if one does>
Touches:    <the skill's folder>
            <documents.archive>
            <for a fold: .claude/wiqrug.md>

<!-- wiqrug template: one ticket per overlapping project skill the user chose to retire or
fold. A skill kept gets no ticket. -->

## What to build

<For retire:> Move `<the skill's folder>` into `<documents.archive>` with `git mv`, untouched, so it
can be restored by moving it back.

<For fold:> Write its project-specific parts, as the user agreed them, where the playback says —
a setting in wiqrug.md in the .claude folder, or a line that a `CLAUDE.md` ticket carries — then retire it as
above:

```text
<each part, and where it goes>
```

## Acceptance

- [ ] `test -e "<documents.archive>/<skill>" && test ! -e "<the skill's folder>"` exits 0
- [ ] `wiqrug-check` exits 0

## Comments
