# Implement — an item that changes a screen

Open this from `SKILL.md` §4 only when the item changes something drawn. A screen is proved by a
command, never by a screenshot read by eye: a picture proves nothing a command can repeat.

**Where `browser.check` is a command**, run it on the changed page with the item's assertions,
twice — a check that passes once and fails once is a flaky screen, not a pass. Write the
assertions as the item's boxes ask: counts, what a row says, what a role cannot do. Read what the
check prints instead of opening a screenshot; a screenshot is for a check that failed.

**Where `browser.check` is `none`**, nothing a command runs can see the screen: the item has no
box for it, and the owner's steps below are the whole check. An older queue's item may carry a
screen box **for a person**; it stays unticked.

Either way, rewrite the item's `## Check in the browser` as steps the owner can follow without
reading code — page, account, language, width, what to do, what should be seen — and end it with
what only a person can judge. Anything the check saw and could not decide goes there too.
