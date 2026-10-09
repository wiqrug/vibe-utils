---
name: to-spec
description: Turn a confirmed /wiqrug:grill-with-docs playback into the work's understanding.md in the project's queue — no interview, only synthesis.
argument-hint: "<slug>"
disable-model-invocation: true
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

# To spec

The second step of the loop: `/wiqrug:grill-with-docs` → `/wiqrug:to-spec` →
`/wiqrug:to-tickets` → `/wiqrug:implement`. Its input is this conversation — the interview and
the playback the owner confirmed. **Do not interview.** Synthesize what was already said; the one
question this skill asks is the seams (step 1). With no confirmed playback in the conversation,
stop and say `/wiqrug:grill-with-docs` comes first.

The output is one document that a later session, with no memory of this conversation, can be
handed alone.

## 1 — agree where it is tested

Call the Skill tool with `wiqrug:codebase-design` first, and use its words — module, interface,
seam, adapter, depth — here and in `## Implementation decisions`. Sketch the seams — the places a
test observes behaviour at, such as a pricing decision or an external client's transport.
**Prefer an existing seam to a new one, the highest seam possible, and as few as possible — the
ideal is one.** A new seam is proposed at the highest point it can go. `/wiqrug:tdd` writes tests
only at the seams agreed here, with `tests.framework` and within `tests.limits`.

Put them to the owner as one numbered question — `❓ **Q1** - **Where it is tested**: …` then
`➡️ <your recommendation>` — and wait. This is the only question; everything else comes from the
conversation.

## 2 — write one document

`<documents.queue>/<slug>/understanding.md`, where `<slug>` is lowercase-hyphen and the queue
folder is the one the settings above name:

```markdown
# <slug> — what is being built and why

## The problem            what the person does today, and what it costs
## The shape              what is being built, in prose. No paths, no code
## User stories           a long numbered list: "As a <role, or the owner>, I want <feature>,
                          so that <benefit>" — every aspect of the work
## Acceptance             what must be true, each stated as something checkable
## Invariants             what may not change, and what breaks if it does
## Implementation decisions  the modules built or changed and the interface each shows the
                          rest, schema changes, API contracts, the owner's technical calls
## Where it is tested     the seams agreed in step 1 — tdd tests nowhere else — and the
                          prior art: the existing tests nearest to them, named by what they test
## Out of scope           named, so a later session does not helpfully add it
## Undecided              each with the open question or the owner's decision it waits on
## Decisions              the playback's decision list, as confirmed
## Advances               a unit in documents.units (Full), or the Now note's Next line (Standard)
```

Use the glossary's words (`documents.glossary`) throughout, and respect the `D-` decisions in the
area (`documents.decisions`). A term or decision the grilling settled is already filed — cite it;
do not file it again. Where the project keeps specifications (`documents.specs` is not `none`)
and this work changes one, say so under `## Implementation decisions`: the specification is
updated by the item that changes what it describes.

⚠️ **No file paths, no line numbers, no code in this document.** They go stale inside a week
and a reader cannot tell that they have, so they mislead with the full authority of something
specific. Nor do they belong in a work item: the session that builds the item finds them from
the code.

## Report

Where the document is · how many user stories · the seams agreed · what it explicitly excludes
· what it waits on, each named · and the next step, which is the owner's: they type
`/wiqrug:to-tickets <slug>` in this same session.
