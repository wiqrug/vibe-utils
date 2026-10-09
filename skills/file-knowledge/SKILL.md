---
name: file-knowledge
description: File what was just learned, the moment it is learned — a trap (G-), a term, a decision (D-), an open question or its answer, a defect left unfixed, and in a Full knowledge base a fact or question (F-, Q-). Use when a fix took more than twenty minutes, something behaved unlike its documentation, someone answered a question, the owner decided something, or a word needed explaining.
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

# File knowledge

The one owner of **how** each kind of knowledge is written down. Every other skill that learns
something calls this one at the moment it learns it, rather than leaving it for the end of the
session: a finding held until the closing check is a finding the session forgets.

## What this project keeps

The lines above are the settings. `knowledge.level` says which kinds exist; each kind's
`documents.*` setting says where it lives, from the repository's root. The template is the format:
read it before writing, and write what it says.

| Kind | Setting | Template | Level |
|---|---|---|---|
| Term | `documents.glossary` | `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/common/glossary.md` | both |
| Decision (`D-`) | `documents.decisions`, one file each | `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/common/decision.md` | both |
| Trap (`G-`) | `documents.gotchas` | `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/common/gotchas.md` | both |
| Open question | `documents.questions` | `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/standard/questions.md` | standard |
| Answer to it | the same entry | the same template | standard |
| Defect left unfixed | `documents.now`, under Next | `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/standard/now.md` | standard |
| Fact (`F-`) | `documents.ledger`, one file each | `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/fact.md` | full |
| Question (`Q-`) | `documents.ledger`, one file each, and its line in `documents.questions` | `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/question.md`, `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/questions.md` | full |
| Answer to it | the same `Q-` file's History | `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/question.md` | full |
| Defect left unfixed | the unit's Next, in `documents.units` | `${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/unit.md` | full |

## A kind this project does not keep

A kind is missing when its level is not the project's, or when its setting is `none`. Then say so
in one line and offer the nearest kind the project has — never create the missing folder or file,
and never edit the settings to make room:

| Asked for | Nearest |
|---|---|
| a fact (`F-`), in a Standard project | a trap (`G-`) when it bites someone who assumes otherwise; else an open question, its evidence cited |
| a question (`Q-`), in a Standard project | an open question |
| an answer to a `Q-`, in a Standard project | the answer under its open question |
| a unit's Next, in a Standard project | the Now note's Next |
| any kind whose setting is `none` | a kind the project does keep that can carry the finding — a trap, a decision, an open question — named aloud; where none can, the commit message, and the user is told |

*"This project keeps a Standard knowledge base, so it has no ledger for F-194; I can file it as a
gotcha in docs/gotchas.md instead."* Unattended, nobody can be asked: file the nearest kind and
write, in the tick, which kind it became and why.

A setting that names a document which does not exist yet is a kind the project keeps: create that
one file from its template. A setting whose path is the other shape — a folder where the template
is one file, or the reverse — is asked about, never reshaped.

## Rules

- **Each filing is its own commit.** A finding about the world commits separately from the
  work that found it, or reverting the work silently reverts the knowledge.
- **Search before writing.** Use the Grep tool on the kind's document for the symptom, the term
  or the question. A trap that already has an entry gets an **Occurrence.** line on that entry —
  what was being done when it bit, and why its enforcement did not catch it — never a second
  entry. A term already defined is corrected in place; an answered question is never re-asked.
- **IDs are permanent.** The next free number is the highest in use plus one — Grep the whole
  document or folder for the prefix, `D-`, `G-`, `F-` or `Q-`, not only the newest entry. Never
  reuse, never renumber. After writing, Grep for the new ID's heading or file: it is defined
  exactly once.
- **Every new `G-` has its `**Enforced by**` line**: the test, guard or refusing script that
  stops it coming back, or `none:` and the reason. Building the check is preferred to writing
  `none:`.
- **A decision gets a `D-` file only when it is all three:** hard to reverse, surprising without
  its context, and the result of a real trade-off. Otherwise the commit message holds it. An
  owner's decision is written with the owner's words, verbatim.
- **Terms use the glossary's format** and its words: a synonym goes on the `_Avoid_:` line,
  never into prose.
- **An answer is appended, dated, never edited over its evidence.** When the evidence refuses an
  answer, it is recorded as contradicted — in a Full ledger the status `contradicted`, never
  closed — quoting both sides. Ledger statuses stay in the template's closed set.
- **Never guess a meaning.** A claim without evidence is a question, not a fact.
- **Never summarise what you move.** Text that moves — an answered question to Answered, what no
  longer fits a Now into History — moves verbatim.

## In an unattended item

The run files its knowledge once, in its closing session, so the item session does not write
the knowledge files. Write the finding into the item file instead, as one unticked line under its
`## To file`, typed by its kind and in the words it would be filed with:

```markdown
## To file

- [ ] G: <area>: <symptom> — cause <…>, instead <…>, enforced by <…>
- [ ] term: <Term> — <one or two sentences>
```

The types are `G:`, `F:`, `Q:`, `answer:`, `term:`, `D:` and `defect:` — the same in every
project, whatever its level. After the last item the loop runs `/wiqrug:update-knowledge <slug>`,
which files each line through this skill, one commit each, and ticks it with where it now lives.

## After filing

Read the changed file once more beside its template: the headings, the fields and the ID's
format are the template's. A filing that does not match its template is not filed.
