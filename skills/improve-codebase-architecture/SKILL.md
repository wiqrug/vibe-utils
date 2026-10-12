---
name: improve-codebase-architecture
description: Scan the code for deepening opportunities, present them as a visual HTML report, then grill through the one the user picks. Use before planning work in an area that keeps changing, or when an area has become hard to change or test.
disable-model-invocation: true
---

!`wiqrug-check --skill`

If the first line above does not begin `wiqrug: set up —`, show that line to the user and stop.

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities**: refactors that turn shallow
modules into deep ones. The aim is testability and AI-navigability. **Nothing is built in this
skill**; what it writes is the report, and the knowledge that resolves in the grilling.

This command is _informed_ by the project's domain model and built on a shared design vocabulary:

- Call the Skill tool with `wiqrug:codebase-design` for the architecture vocabulary (**module**,
  **interface**, **depth**, **seam**, **adapter**, **leverage**, **locality**) and its principles
  (the deletion test, "the interface is the test surface", "one adapter = hypothetical seam, two =
  real"). Use these terms exactly in every suggestion, and don't drift into "component," "service,"
  "API," or "boundary."
- The settings above name the documents; one set to `none` is one the project does not keep, and
  is skipped. The glossary, `documents.glossary`, gives names to good seams; the `D-` files in
  `documents.decisions` record decisions this command should not re-litigate.

## 1 — explore

**Scope before you scan: YAGNI.** Deepening a module pays off by making future changes to it easier,
so put extra weight on the parts of the code that have recently changed. Decide *where* to look
before you look:

- If the user named a direction (a module, a subsystem, a pain point), take it, and skip the
  inference below.
- Otherwise, walk back a good stretch of the commit history (`git --no-pager log --oneline
  --name-only`) to find the hot spots, the files and areas that keep coming up, and let those paths
  pull your attention first. If the changes are scattered with no clear hot spot, widen the net.

Read the glossary and the `D-` files in the area you're touching first.

Then spawn an `Explore` sub-agent to walk the code. Don't follow rigid heuristics; explore
organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow**, with an interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how
  they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the code are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate
complexity, or just move it? A "yes, concentrates" is the signal you want.

## 2 — present candidates as an HTML report

Write a self-contained HTML file outside the repository, in the system's temporary folder, named
`architecture-review-<timestamp>.html` so each run gets a fresh file. Give the user its absolute
path to open in a browser.

The report uses **Tailwind via CDN** for layout and styling, and **Mermaid via CDN** for diagrams
where a graph/flow/sequence reliably communicates the structure. Mix Mermaid with hand-crafted
CSS/SVG visuals: use Mermaid when relationships are graph-shaped (call graphs, dependencies,
sequences), and hand-built divs/SVG when you want something more editorial (mass diagrams,
cross-sections, collapse animations). Each candidate gets a **before/after visualisation**. Be
visual.

For each candidate, render a card with:

- **Files**: which files/modules are involved
- **Problem**: why the current architecture is causing friction
- **Solution**: plain English description of what would change
- **Benefits**: explained in terms of locality and leverage, and how tests would improve
- **Before / After diagram**: side-by-side, custom-drawn, illustrating the shallowness and the
  deepening
- **Recommendation strength**: one of `Strong`, `Worth exploring`, `Speculative`, rendered as a
  badge

End the report with a **Top recommendation** section: which candidate you'd tackle first and why.

**Use the glossary's words for the domain, and the `wiqrug:codebase-design` vocabulary for the
architecture.** If the glossary defines "order," talk about "the order intake module," not "the
FooBarHandler," and not "the order service."

**`D-` conflicts**: if a candidate contradicts a `D-` decision, only surface it when the friction is
real enough to warrant revisiting the decision. Mark it clearly in the card (e.g. a warning callout:
_"contradicts D-017, but worth reopening because…"_). Don't list every theoretical refactor a
decision forbids.

See [HTML-REPORT.md](HTML-REPORT.md) for the full HTML scaffold, diagram patterns, and styling
guidance.

Propose no interfaces yet. After the file is written, ask the user: "Which of these would you like
to explore?"

## 3 — grilling loop

Once the user picks a candidate, interview them with the technique pasted at the end of this
skill, walking the design tree: constraints, dependencies, the shape of the deepened module, what
sits behind the seam, what tests survive.

Side effects happen inline as decisions crystallize; call the Skill tool with
`wiqrug:domain-modeling` to keep the domain model current as you go:

- **Naming a deepened module after a concept not in the glossary?** File the term then, as
  `wiqrug:domain-modeling` says.
- **Sharpening a fuzzy term during the conversation?** File it right there.
- **User rejects the candidate with a load-bearing reason?** Offer a `D-` file, framed as: _"Want
  me to record this as a decision so future architecture reviews don't re-suggest it?"_ Only offer
  when the reason would actually be needed by a future explorer to avoid re-suggesting the same
  thing; skip ephemeral reasons ("not worth it right now") and self-evident ones.
- **Want to explore alternative interfaces for the deepened module?** Use `wiqrug:codebase-design`'s
  design-it-twice parallel sub-agent pattern
  ([DESIGN-IT-TWICE.md](../codebase-design/DESIGN-IT-TWICE.md)).

## Report

The report's path · the candidates, each with its strength · the one explored and what was decided ·
what was filed on the way (terms, `D-` files) · and the next step, which is the user's: to build
the deepening, they type `/wiqrug:grill-with-docs <the deepening>`, which starts the loop from what
this conversation settled.

The technique is pasted below from the `interview` skill. If nothing follows the rule, read
`${CLAUDE_PLUGIN_ROOT}/skills/interview/SKILL.md` and use it.

---

!`wiqrug-check --skill --run ${CLAUDE_PLUGIN_ROOT}/skills/grill-me/paste.py ${CLAUDE_PLUGIN_ROOT}/skills/interview/SKILL.md`
