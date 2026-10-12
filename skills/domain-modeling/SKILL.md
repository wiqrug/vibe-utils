---
name: domain-modeling
description: Use when a term is fuzzy, overloaded or differs from the glossary, when the owner makes a decision worth a D- file, or when an answer about the project's subject needs checking before it is written down.
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

# Domain modeling

Sharpen the project's words and decisions while the owner designs, and file each the moment it
resolves.

The settings above name the documents: `documents.glossary`, `documents.decisions`,
`documents.questions` and, in a Full knowledge base, `documents.ledger`. A document set to `none`
is one the project does not keep — `/wiqrug:file-knowledge` says what it offers instead.

## Inside each question

**Challenge against the glossary.** When the owner's word differs from the glossary's, say so
inside the question: which word the glossary uses, and what it means there.

**Sharpen a fuzzy word.** When the owner's word is vague or overloaded, propose the precise one
inside the question: *"'account' — do you mean the person who signs in, or the company that pays?"*

**Invent the edge case.** When a relationship between two things is being settled, make up the
scenario that tests its boundary — an order changed after it shipped, a subscription that spans
two price periods, a record moved between owners halfway through — and ask what happens in it.

## Every answer checked

An answer is a claim: check it against the evidence before it is written down.

| about | against |
|---|---|
| the project's subject | Full: the ledger, then the item; Standard: the decisions, the glossary and the open questions |
| what the software does | the code, read |
| what is running, where | the environments the settings name, asked of the machine — never remembered |
| a term | the glossary |

An answer the evidence contradicts is filed as contradicted, and the work goes around it.

## File as it resolves

Terms and decisions are written during the interview, as each resolves — not held for the
playback:

- **A term resolves** — the owner settles what a word means, or which of two words is right:
  call the Skill tool with `wiqrug:file-knowledge`.
- **A decision is made**: call `wiqrug:file-knowledge`; one that does not earn a `D-` file goes
  into the playback's decision list.
- **A decision only the owner can make** and nobody has made becomes an open question naming the
  owner as the one who answers it, and what depends on it waits.

## Scenarios

Before the playback, replay every rule the answers produced through one concrete example — real
dates, quantities and parties — with numbers chosen so that the two readings of the rule give
different results. Put both results side by side and ask which one is right: the owner confirms
the number, not the sentence.
