---
name: research
description: Investigate a question against high-trust primary sources and report the findings, each with its source. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

Spin up a **background agent** to do the research, so you keep working while it reads.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Report the findings in the conversation, citing each claim's source. That is the whole output, unless the brief says to write a file (step 3).
3. Write a file only when the user asked for one, or a decision or spec will cite the findings — decide this before starting the agent, and put it in its brief. Then: one Markdown file in the folder the project check names as `documents.research`, as the next free `NN-<topic>.md`, and say where. When that setting is `none`, ask the user where before writing. A fact about the project's subject is filed through `/wiqrug:file-knowledge`, not into a research file.
