# Deepening

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

How to deepen a cluster of shallow modules safely, given its dependencies. Assumes the vocabulary in
[SKILL.md](SKILL.md): **module**, **interface**, **seam**, **adapter**.

## Dependency categories

When assessing a candidate for deepening, classify its dependencies. The category determines how the
deepened module is tested across its seam. What a test may not need — the `tests.limits` the project
check names, often no database and no network — decides categories 2 to 4 here.

### 1. In-process

Pure computation, in-memory state, no I/O: a calculation's decisions, a format's field mapping.
Always deepenable: merge the modules and test through the new interface directly. No
adapter needed.

### 2. Local-substitutable

Dependencies with a local stand-in: the file system (a temporary directory), the database session (a
small class holding the rows the code reads, as `/wiqrug:tdd` shows). Deepenable when the stand-in
is small. The seam is internal; no port at the module's external interface.

### 3. Remote but owned (Ports & Adapters)

This project's own processes across a socket, such as a worker or a local daemon. Define a
**port** (interface) at the seam. The deep module owns the logic; the transport is injected as an
**adapter**. Tests use an in-memory adapter. Production uses the socket adapter.

Recommendation shape: *"Define a port at the seam, implement the socket adapter for production and
an in-memory adapter for testing, so the logic sits in one deep module even though it runs in two
processes."*

### 4. True external (Mock)

Services this project does not control: a payment provider, a partner's API. The deepened module
takes the external dependency as an injected port; tests provide a stand-in adapter for its
transport.

## Testing strategy: replace, don't layer

- Old unit tests on shallow modules become waste once tests at the deepened module's interface
  exist; delete them.
- Write new tests at the deepened module's interface. The **interface is the test surface**.
- Tests assert on observable outcomes through the interface, not internal state.
- Tests should survive internal refactors, since they describe behaviour, not implementation. If a
  test has to change when the implementation changes, it's testing past the interface.
