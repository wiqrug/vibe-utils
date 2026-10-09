# Good and bad tests

Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock).

The examples are in Python for brevity; the shape is the same in the project's own framework.
The domain is an invented shop that prices orders.

## Good tests

**Through the real interface, with an independent expected value.**

```python
class AnOrderWithAVolumeDiscount(unittest.TestCase):
    """12 units at 4.50 with the 10% volume discount: 48.60, the worked example in D-007."""

    def test_the_discount_applies_once_to_the_whole_order(self) -> None:
        order = price(lines([line("SKU-1", quantity=12, unit="4.50")]), discounts=[volume_10])
        self.assertEqual(order.total, Decimal("48.60"))  # D-007's worked example
```

What makes it good:

- It calls the decision — pricing an order — and reads its answer; nothing inside is patched.
- The expected number is the decision record's, cited, not the code's arithmetic replayed.
- The name says **what** is true of an order, not **how** the code gets there.
- It survives any rewrite of the pricing that still prices the order the same.

**A default is asserted as a flag, not only as a number.**

```python
def test_an_item_with_no_price_uses_the_list_price_and_says_so(self) -> None:
    order = price(lines([line("SKU-9", quantity=1)]), list_prices={"SKU-9": "10.00"})
    self.assertEqual(order.total, Decimal("10.00"))
    self.assertIn("list_price_used", {note.code for note in order.defaults})
```

A result computed from a default is flagged, never passed off quietly — so the test proves the
flag.

## Bad tests

**Implementation-coupled.**

```python
# BAD: asserts on how, through a patched internal collaborator
def test_price_calls_apply_discounts(self) -> None:
    with mock.patch("shop.pricing._apply_discounts") as applied:
        price(lines(...), discounts=[...])
    applied.assert_called_once()
```

Red flags: a patch on the project's own module, a private helper called directly, an assertion on
call counts or order, a name that describes the mechanism, a test that breaks on a refactor that
kept the behaviour.

**Verified through a side channel.**

```python
# BAD: reads the stored row back instead of asking the interface
def test_saving_an_alias_stores_it(self) -> None:
    save_alias(store, "SKU-1-OLD", "SKU-1")
    self.assertEqual(store.rows[0].sku, "SKU-1")

# GOOD: what was saved is what the interface now answers
def test_a_saved_alias_is_what_the_order_is_priced_with(self) -> None:
    save_alias(store, "SKU-1-OLD", "SKU-1")
    self.assertEqual(sku_for(store, "SKU-1-OLD"), "SKU-1")
```

**Tautological.**

```python
# BAD: the expected value is recomputed the way the code computes it
def test_the_total_is_the_sum_of_its_lines(self) -> None:
    order = price(lines(...), discounts=[...])
    self.assertEqual(order.total, sum(line.net for line in order.lines))

# GOOD: the expected value is a known literal, and cites where it came from
def test_the_total_rounds_once_not_per_line(self) -> None:
    order = price(lines(...), discounts=[...])  # D-012: round the total, never each line
    # 3 × 3.335 = 10.005 → 10.01 once; per line it would be 3 × 3.34 = 10.02.
    self.assertEqual(order.total, Decimal("10.01"))
```

**A number where nobody gave one.**

```python
# BAD: the test invents the answer nobody has given
self.assertEqual(order.total, Decimal("0.00"))

# GOOD: the code refuses, and the open question is named
self.assertIn("no_price", {note.code for note in order.refusals})  # waits on the open question
```

Blank is not zero, in a test as in the code.
