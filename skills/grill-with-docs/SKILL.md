---
name: grill-with-docs
description: A relentless interview to sharpen a request, filing glossary terms and decisions as they resolve.
argument-hint: "<what you want built>"
disable-model-invocation: true
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

# Grill with docs

The first step of the loop, for a feature — anything larger than a single change:
`/wiqrug:grill-with-docs` → `/wiqrug:to-spec` → `/wiqrug:to-tickets` → `/wiqrug:implement`.

**Nothing is built in this skill, and nothing is written but the knowledge that resolves on
the way** — glossary terms and decisions, each as its own commit. It ends in a playback the
owner confirms; `/wiqrug:to-spec` then writes the document from this conversation.

## 1 — look up what the project already knows

The settings above name every document; one set to `none` is one the project does not keep, and
is skipped. Before the first question, because a feature that already exists under another name
changes every question after it, read rather than assume — in a background `Explore` subagent
when the reading is long, asking the round-1 questions that do not depend on it meanwhile:

- **`documents.now`**, and in a Full knowledge base **`documents.units`** — is this already
  open somewhere under another name?
- **`documents.specs`** and the folders under **`documents.queue`** — is it specified, or
  queued, already?
- **`documents.decisions`** — which `D-` decisions govern the area? The work respects them, or
  the interview proposes superseding one.
- **`documents.questions`**, and in a Full knowledge base **`documents.ledger`** — every claim
  about the project's subject in the request cites what is recorded, or becomes a new open
  question. A request that rests on a question nobody has answered waits on it, decided by the
  owner and by nobody else.
- **`documents.gotchas`** — is the thing being asked for a known trap, or a defect left for a
  reason?

## 2 — interview, with the questions that belong to a feature

The technique is `/wiqrug:interview`, and `/wiqrug:domain-modeling` sharpens and files the
knowledge on the way; both are printed in full at the end of this skill. These are the questions,
and the first round is whichever of them do not depend on another:

- **Who reads the result?** A document or a screen handed to the project's users is written in
  `language.deliverables`; the project's own code and knowledge stay in the language they are in.
  Ask only when this result's readers differ from that setting.
- **What does the person do today instead?** The answer names the manual step, the tool or the
  screen being replaced, and that is what the work is measured against.
- **What must be true for this to be right?** Each answer is a candidate acceptance box, so
  press until it names something a command could check.
- **What may this not change?** The invariant that must survive — and anything under
  `agents.never-touch`. This becomes the item that fails loudly rather than the assumption
  nobody wrote down.
- **What is the smallest version that is useful on its own?** Anything past it is a later
  item, not a bigger first one.
- **What does this advance?** In a Full knowledge base, a unit in `documents.units`: a feature
  that advances no unit either opens one or is not work. In a Standard one, the line of the Now
  note's Next it moves, or a new one.
- **Who uses it, and for what?** Each answer is a candidate user story — *as a <role, or the
  owner>, I want …, so that …* — for `/wiqrug:to-spec` to write down.

Where it is tested is not asked here: `/wiqrug:to-spec` proposes the seams and agrees them with
the owner.

## 3 — play it back, and wait for the owner

The interview's **Playback**, with its decision list. The owner reading it is the check the
whole chain rests on: nothing past this point happens until they confirm it.

## Report

What was agreed · what is out of scope · what it waits on, each named · what was filed on the
way (terms, `D-` files) · and the next step, which is the owner's: they type
`/wiqrug:to-spec <slug>` in this same session, where `<slug>` is lowercase-hyphen — the
conversation is its input.

The technique and the filing are pasted below. If nothing follows a rule, read
`${CLAUDE_PLUGIN_ROOT}/skills/interview/SKILL.md` and
`${CLAUDE_PLUGIN_ROOT}/skills/domain-modeling/SKILL.md` and use them. The project check at the
head of the pasted `domain-modeling` has already run, above.

---

!`wiqrug-check --skill --run ${CLAUDE_PLUGIN_ROOT}/skills/grill-me/paste.py ${CLAUDE_PLUGIN_ROOT}/skills/interview/SKILL.md`

---

!`wiqrug-check --skill --run ${CLAUDE_PLUGIN_ROOT}/skills/grill-me/paste.py ${CLAUDE_PLUGIN_ROOT}/skills/domain-modeling/SKILL.md`
