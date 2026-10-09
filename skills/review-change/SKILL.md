---
name: review-change
description: Review a change since a fixed point along two axes — Standards (the project's own CLAUDE.md and rules) and Spec (the understanding and the items) — in two parallel reviewer subagents, reported side by side. Use when a branch, an item's commits or work in progress is finished and needs an independent reading before it is merged or reported.
argument-hint: "[<base>] [<spec path>]"
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

# Review a change

Two axes, reviewed apart, because a change can pass one and fail the other: code that keeps every
rule and builds the wrong thing, or code that builds exactly the item and breaks the project's
rules. One reviewer reading both lets one axis hide the other.

- **Standards** — does the diff keep this project's rules?
- **Spec** — does the diff build what the understanding and the items asked for?

Each axis is one subagent of the plugin's `reviewer` agent
([its brief](${CLAUDE_PLUGIN_ROOT}/agents/reviewer.md)), listed among the agents as
`wiqrug:reviewer`. They run in parallel so neither reads the other's context. A reviewer only
reads. What it reports is a claim, not a verdict. The caller checks each finding before acting
on it.

## 1 — pin the fixed point

The base is the one the caller names: the commit before an item's first commit, or the branch the
work will merge into. With none named, use the merge base with the branch this one was cut from;
when that cannot be told, ask — attended — or, unattended, say which base was taken and why.

Run it from the repository's root. The three files go in a new temporary folder outside the
repository, so a review leaves nothing in the tree:

```bash
cd "$(git rev-parse --show-toplevel)"
base=$(git rev-parse --verify "<base>^{commit}")           # a bad ref fails here
git diff --quiet "$base"...HEAD && echo "empty diff"       # an empty diff stops the review
out=$(mktemp -d)
git diff "$base"...HEAD > "$out/diff.patch"
git log --oneline "$base"..HEAD > "$out/commits.txt"
git diff --name-only "$base"...HEAD > "$out/files.txt"
```

A bad ref or an empty diff stops the review here and is reported as such. A review of nothing
must not look like a clean review. The reviewers have no Bash, so they read these three files,
never a `git` command — give them the absolute paths.

## 2 — find the spec

The queue is `documents.queue` in the settings above. In this order, first match wins:

1. A path the caller passed. **When it lies in a queue folder** (`<documents.queue>/<slug>/`),
   give the Spec reviewer the whole queue set as well: that folder's `understanding.md`, the
   items the diff touches, and the passed file. A caller passes an item or the understanding;
   each needs the other half.
2. The queue: `<documents.queue>/<slug>/understanding.md` and the items whose files the diff
   touches. If the diff touches no item, the item the caller names. The slug comes from an item
   path in `files.txt` or from the branch `afk/<slug>`.
3. With no `understanding.md`, the item alone; with no queue at all (`none`), a specification in
   `documents.specs` the caller names.
4. With none of these, the Spec reviewer is not started, and the report's `## Spec` says
   **"no spec available"**. An axis that could not run must not look like one that passed.

## 3 — find the standards

The project's own, never a list carried from elsewhere:

- **The project's instructions**: `CLAUDE.md` at the repository's root and any `CLAUDE.md` in a
  folder the diff touches, the files they import with `@`, and AGENTS.md where the project
  keeps one.
- **The rule files that match the changed paths.** A `.claude/rules/*.md` with `paths:` in its
  frontmatter matches when a file in `files.txt` falls under one of its globs. A rule file without
  `paths:` is always on.
- **The project's traps** — `documents.gotchas`, unless it is `none` — whose area the diff
  touches: a change that walks back into a filed trap is a finding.
- **The reviewer's own lenses.** It already carries them — blank is not zero, a default says so,
  a second idiom, no personal data, a refused edit is not saved, a count equals the rows behind
  it, a check that cannot run does not look passed, a domain claim cites its source. Name them in
  the brief; do not restate them.
- **Tests that repeat the code's own calculation.** An expected value computed the way the code
  computes it proves only that the code agrees with itself. It must come from an independent
  source (`/wiqrug:tdd`).
- **The smell baseline** below: judgement calls only. A rule of the project overrides it, and a
  smell a rule endorses is not reported.

### The smell baseline

Fowler's smells (_Refactoring_, ch. 3), each a labelled heuristic ("possible Feature Envy"),
never a hard violation. Skip what tooling already enforces.

- **Mysterious Name**: a name that does not say what the thing does or holds. → rename it; if no
  honest name comes, the design is murky.
- **Duplicated Code**: the same logic shape in more than one hunk or file. → extract it, call it
  from both.
- **Feature Envy**: a function reaching into another object's data more than its own. → move it
  onto the data it envies.
- **Data Clumps**: the same few fields or parameters travelling together. → bundle them into one
  type.
- **Primitive Obsession**: a string or number standing in for a domain concept. → give the concept
  its own small type.
- **Repeated Switches**: the same `if`-cascade on the same type in several places. → one map both
  sites share.
- **Shotgun Surgery**: one logical change scattered across many files. → gather what changes
  together.
- **Divergent Change**: one file edited for several unrelated reasons. → split it so each part
  changes for one reason.
- **Speculative Generality**: parameters or hooks for needs the spec does not have. → delete them.
- **Message Chains**: long `a.b().c().d()` navigation. → hide the walk behind one call.
- **Middle Man**: a function that mostly delegates onward. → call the real target directly.
- **Refused Bequest**: an implementer that ignores most of what it inherits. → use composition.

## 4 — start both reviewers, in parallel

Two `Agent` calls with the `wiqrug:reviewer` subagent type, in one message. Each brief carries
the three absolute paths from step 1.

**Standards brief:** the project's instruction files and the matching rule files, by path; the
traps by path; the lens names from step 3; the smell baseline pasted in full, because the reviewer
has no other copy; and:

> Report, per file and hunk, (a) every place the diff breaks the project's instructions, a rule
> file, a filed trap or one of your lenses — cite the file and the rule, or the lens; (b) any
> test whose expected value repeats the code's own calculation; (c) any baseline smell, named,
> with the hunk quoted. A rule breach can be hard; a smell is always a judgement call, and a rule
> of the project overrides it. Under 400 words, then *What I did not read*.

**Spec brief:** the spec paths from step 2, and:

> Report (a) what the spec asked for that is missing or partial; (b) what the diff does that was
> not asked for; (c) what looks built but built wrong; (d) anything the spec itself leaves
> undecided that the diff had to guess — a gap in the spec, not a defect of the code; say which
> spec line is silent. Quote the spec line for each finding. Under 400 words, then *What I did
> not read*.

## 5 — report the two side by side

```
## Standards
<the Standards reviewer's report, verbatim or lightly cleaned>

## Spec
<the Spec reviewer's report — or: no spec available, and which sources were looked for>

Standards: <n> findings; worst: <one line, or none>
Spec: <n> findings; worst: <one line, or none> — or: Spec: not run, no spec available
```

Never merge the two lists, and never re-rank across them. The separation exists so that one
axis cannot bury the other. Each finding is still a claim: check it before anyone fixes it.

Remove the temporary folder once the report is written.
