---
name: update-knowledge
description: The closing check. Close a piece of work — file anything not yet filed, fix what this session made false, rewrite the Now and Next, check the knowledge against its templates. Use when work is finished, before /clear, or when the owner says "write this up" or "we are done for today". With a slug, it files a queue's "To file" lines; with --unattended too, only that.
argument-hint: "[<slug> [--unattended]]"
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

# Update knowledge

The settings above name the documents and `knowledge.level`. The range is every commit since this
skill last finished in this working tree, plus the working tree itself:

```bash
git --no-pager log --oneline refs/worktree/wiqrug-update-knowledge..HEAD
git --no-pager status --short
```

When the first command answers *unknown revision*, this is the tree's first run: take the commits
since the branch left the main branch, `git --no-pager log --oneline <main>..HEAD`. The test:
**could somebody with no memory of this session pick it up tomorrow and repeat none of it?**

## 1 — anything not filed yet

Knowledge is filed when learned; this step catches the rest. For each trap, question, answer,
term, decision or defect — and in a Full knowledge base, fact — not yet filed, call the Skill
tool with `wiqrug:file-knowledge`, one commit each; it owns every kind's format, its ID rules,
and what to offer when the project's level lacks the kind.

**With a slug** (`/wiqrug:update-knowledge <slug>`), also read every item in the slug's folder
under `documents.queue`: each unticked line of its `## To file` section (one typed line per
finding — `G:`, `F:`, `Q:`, `answer:`, `term:`, `D:`, `defect:`), and any note its `## Comments`
leaves for this skill. File each through `wiqrug:file-knowledge`, then tick the line with where
it now lives — and, where the level lacked the kind, which kind it became. A finding already
filed is ticked with where it lives, not filed twice. **`--unattended`** (the unattended loop's
closing session, nobody watching): this step and step 5's check and commit **only** — no Now and
Next, no memory, no cursor. A memory written with nobody watching is one nobody reviews. Write in
**whichever file** a line needs, an item's notes included — no item owns a path — and when
step 5's check names a fault, fix it there as its own commit, or say in one line what you could
not fix.

## 2 — what did this session make false?

For every function, file, flag, route, screen, script or setting this session **renamed or
removed**, search the documents the settings name, the `.claude` folder and `CLAUDE.md` for the
old name with the Grep tool, and fix or retire each hit: a citation of a deleted thing reads as
checkable.

## 3 — Now and Next

**Standard** — rewrite `documents.now` in the format of
`${CLAUDE_PLUGIN_ROOT}/templates/knowledge/standard/now.md`: Now at most three lines, Next at most
eight, no hash, no date. What stops being true is deleted — git holds it — never condensed into a
summary line.

**Full** — for each unit this session touched, in `documents.units`, in the format of
`${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/unit.md`: rewrite `## Now` — the marker and what is
left, **at most three lines** — and `## Next` — the exact next action, what waits on the owner,
what is unverified, **at most eight lines**, no hash, no date in either. Add **one** History entry
for the session at the top of `## History`: `### YYYY-MM-DD — <gist> (<first>..<last>)`, the
commit range. What no longer fits moves there verbatim. Then rewrite `documents.now` in the format
of `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/now.md`, naming the unit in play.

A unit the work needs and the units folder lacks is proposed to the user, not created unasked.
Markers: ✅ ran for real **and** checks green · ⚠️ say which half is missing · 🚧 in progress ·
❌ broken. A ✅ that is not is worse than no marker.

## 4 — memory

Memory takes **only lessons about working with the owner**. A procedure goes into its skill, a
decision into a `D-` file, a project fact into the repository. Where something is deployed stays
out of memory: ask the machine each time.

## 5 — check, commit, move the cursor

Read each knowledge file this session changed beside its template, and Grep every ID it took:
each is defined exactly once. A handoff that does not match its templates is not finished. Commit
in slices — a finding about the world separately from the change that found it. Once everything is
committed, move the cursor to this commit; it lives in this working tree's git refs, so it is never
committed and every working tree keeps its own:

```bash
git update-ref refs/worktree/wiqrug-update-knowledge HEAD
```

## 6 — report

Plain words first: what happened and what is needed. Then **what changed** · **what was filed**
· **what is unverified, and why** · **what waits on the owner**, their commands in full, one a line.
