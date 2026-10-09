---
name: domain-modeling
description: Sharpen the project's words and decisions, and file them as they resolve. Use when a term is fuzzy, overloaded or differs from the glossary, when the owner makes a decision worth a D- file, or when an answer about the project's subject needs checking before it is written down.
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

# Domain modeling

The half of `/wiqrug:grill-with-docs` that writes, beside `/wiqrug:interview`'s technique.
`grill-with-docs` pastes it in; any other session reaches it when a word or a decision surfaces
mid-work, and applies *Every answer checked* and *File as it resolves* to that one thing.
`/wiqrug:grill-me` files nothing, so inside it everything here goes to the playback's decision list
instead.

The settings above name the documents: `documents.glossary`, `documents.decisions`,
`documents.questions` and, in a Full knowledge base, `documents.ledger`. A document set to `none`
is one the project does not keep — `/wiqrug:file-knowledge` says what it offers instead.

What this skill files, `/wiqrug:file-knowledge` writes, in these templates' formats: a term,
`${CLAUDE_PLUGIN_ROOT}/templates/knowledge/common/glossary.md`; a decision,
`${CLAUDE_PLUGIN_ROOT}/templates/knowledge/common/decision.md`; a question — Standard,
`${CLAUDE_PLUGIN_ROOT}/templates/knowledge/standard/questions.md`; Full,
`${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/question.md` with its line in
`${CLAUDE_PLUGIN_ROOT}/templates/knowledge/full/questions.md`.

## Inside each question

**Challenge against the glossary.** When the owner's word differs from the glossary's, say so
inside the question: which word the glossary uses, and what it means there.

**Sharpen a fuzzy word.** When the owner's word is vague or overloaded, propose the precise one
inside the question: *"'account' — do you mean the person who signs in, or the company that pays?"*

**Invent the edge case.** When a relationship between two things is being settled, make up the
scenario that tests its boundary — an order changed after it shipped, a subscription that spans
two price periods, a record moved between owners halfway through — and ask what happens in it.

## Every answer checked

An answer is a claim. Check it before it is written down:

| about | against |
|---|---|
| the project's subject | Full: the ledger, then the item; Standard: the decisions, the glossary and the open questions |
| what the software does | the code, read |
| what is running, where | the environments the settings name, asked of the machine — never remembered |
| a term | the glossary |

⚠️ **An answer the evidence contradicts is neither a fact nor a correction.** It becomes a
question with both sides quoted — in a Full knowledge base a `Q-` item with status
`contradicted`, in a Standard one an open question marked contradicted — and the work goes
around it. `/wiqrug:file-knowledge` owns both formats.

## File as it resolves

Terms and decisions are written during the interview, not after it:

- **A term resolves** — the owner settles what a word means, or which of two words is right:
  call the Skill tool with `wiqrug:file-knowledge`, which writes it to the glossary in its format.
- **A decision is made** that is all three — hard to reverse, surprising without its context,
  and a real trade-off: call `wiqrug:file-knowledge`, which writes a `D-` file with the owner's
  words verbatim. Anything less goes into the playback's decision list only.
- **A decision only the owner can make** and nobody has made becomes an open question naming the
  owner as the one who answers it, and what depends on it waits.

Each filing is its own commit, made when it resolves — not batched with the next one, and not
held for the playback. The understanding document is different: `/wiqrug:to-spec` writes it, and
only after the owner has confirmed the playback. Unattended, a term or decision goes to the item's
`## To file` instead.

## Scenarios

Before the playback, replay every rule the answers produced through one concrete example — real
dates, quantities and parties — with numbers chosen so that the two readings of the rule give
different results. Put both results side by side and ask which one is right: the owner confirms
the number, not the sentence.
