# To tickets — an item that changes a screen

Open this from `SKILL.md` §4 only when an item changes something drawn. It adds to §4's boxes,
never replaces them. Never a screenshot box, and never a hand-built drive: a picture proves
nothing a command can repeat.

**Where `browser.check` is a command**, the item gets exactly this one box for the screen —
never a box for a person:

```markdown
- [ ] `<browser.check>` on <the page> with the item's assertions, run twice, exits 0 — asserting:
      <what a command can check: counts, what a row says, what a role cannot do>
```

**Where `browser.check` is `none`**, no box for the screen at all: nothing a command runs can see
it, so a person does, from the section below. Say so in `## What to build`, so nobody reads the
missing check as forgotten.

What only a person can judge goes in the `## Check in the browser` section, never in a box; the
run's report gathers every item's section under *For you to check*.

⚠️ **No box and no `## Comments` line quotes the section's heading.** `/wiqrug:implement` finds
the section by its heading's text to rewrite it; when the first match is a box, the rewrite eats
that box and the box after it.

After `## Acceptance`, say what the owner should see, in the owner's terms; the session that
builds the item rewrites it as concrete steps:

```markdown
## Check in the browser

- Orders › New order, as a clerk who takes orders: a blank price is refused, saying why
- Only you can judge: whether the refusal reads naturally to the people who use it
```
