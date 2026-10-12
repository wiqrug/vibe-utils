---
name: interview
description: Use when a request arrives underspecified and a guess would cost more than a question.
---

# Interview

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

Interview the user relentlessly until you reach a shared understanding. It needs no setup, so it
works in any folder.

## Rounds

Keep the request as a **design tree**: every decision branches into the decisions that hang off
it. The **frontier** is every decision whose prerequisites are settled — what can be asked now
without guessing at an answer not yet heard. A round asks **the whole frontier**, numbered, each
with your recommendation; past six, the six that unblock the most. A question that depends on
another still open in this round belongs to a later round. Wait for the answers, recompute the
frontier, ask the next round.

```markdown
❓ **Q1** - **<what is being decided>**: <the question; the options, where there are few>

➡️ <your recommendation, and the reason in one line>

---

❓ **Q2** - …
```

Word each question so "yes" accepts your recommendation.

A round opens with its questions. A finding appears only inside the question it bears on, in
one line; the rest waits for the playback.

## Facts are yours to find

If the repository answers it, it is not a question. Where the lookup reads across files, start
an `Explore` subagent in the background and ask the rest of the frontier meanwhile — a few,
flat, each scoped with a capped report. Only the questions that depend on its answer wait.

## Playback

Stop asking when the frontier is empty: every branch of the tree visited, nothing silently
assumed. Stop early when a decision only the user can make blocks the whole request.

A decision nobody has made is listed **undecided**, with what it waits on. Then play it back in
your own words: what is being built, what for, what it does not cover, what is still unknown —
and every decision it rests on, with how each was settled:

```text
Decisions
- <decision>: user, round N | looked up: <source> | undecided: <what it waits on> | out of scope
```

A decision with no line was assumed: ask it, or list it undecided. Then wait. The user's reply
confirms the playback or starts the next round.

## Report

Called by another skill, that skill's report is the report. Alone: agreed · out of scope ·
undecided, each with what it waits on · the decision list.
