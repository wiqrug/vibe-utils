# When to stand something in

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

A test keeps to the project's `tests.limits`, so what crosses those boundaries is replaced — and
**only** what crosses them.

## Replace at a system boundary

- **An external service, over the network.** The project's client for it takes its transport as
  an argument. A test passes a stand-in that records what it was asked to send and answers from a
  list. A request the code refused is one the stand-in never saw.
- **A database.** A small class with the methods the code under test calls, holding the records
  it needs — or the project's own test database, when `tests.limits` allows one.
- **The clock.** Pass the date in, or replace the one call that reads it. A test that depends on
  today's date passes today and fails in a month.
- **The file system**, sometimes. A test that needs a file outside the project skips when the
  file is absent and says so — a skip that reads as a pass is a check that did not run.

## Keep real

- The project's own modules and services.
- Internal collaborators — the helper the decision calls.
- Anything this repository controls.

Replacing one of these tests the wiring, not the decision, and passes while the decision is wrong.

## Personal data

A fixture built from real records is a data export: anonymise it before it enters the
repository — keep the fields and their format, replace the person. A stable hashed fake per value
keeps joins working.

## Designing for a stand-in

**1. Pass the boundary in.**

```python
# Easy to stand in: the transport is an argument
def fetch_rates(day: date, *, transport: Transport) -> Rates: ...

# Hard to stand in: the function builds its own connection from the environment
def fetch_rates(day: date) -> Rates:
    session = requests.Session()
    ...
```

**2. One function per external operation, not one generic fetcher.** A stand-in for a specific
operation returns one shape, needs no branching on the URL, and shows at a glance which operations
a test exercises. Extend the one client with the operation; never write a second client.
