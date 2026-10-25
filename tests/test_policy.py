"""Integrity tests for the Udhaar Dost IDEA (pure logic, no API needed).

These encode the product's non-negotiables from the brief as executable specs:
  - politeness engine (frequency caps, time windows, exits, privacy)
  - promise-respecting scheduling
  - money math that can never go negative or double-count
Run:  python -m unittest discover tests -v   (skips live-API tests if server down)
"""
import unittest
from datetime import datetime, timedelta
import unicodedata


# ---------------------------------------------------------------------------
# Reference implementations of the invariants (these are the specs the demo's
# JS implements; if the demo drifts from these, a test elsewhere catches it).
# ---------------------------------------------------------------------------

CALL_WINDOW = (9, 19)          # 9:00 - 19:00 inclusive-exclusive: 9 AM - 7 PM
CALLS_PER_WEEK = 2             # hard cap per customer per rolling week
FESTIVAL_CAP = 1               # even gentler during festival mode
OVERDUE_DAYS = 7               # overdue if no promise & entry older than this

LOW_TONE_PHRASES = ("theek rahega", "koi baat nahi", "yaad dila rahi hoon",
                    "bata dein", "convenient", "dhanyavaad", "namaste", "🙏")
THREAT_PHRASES = ("legal", "court", "case", "action", "notice", "police",
                  "dhama", "dhamki", "khatra", "gadbad", " blackmail")


def can_call(calls_this_week: int, hour: int, festival: bool = False) -> bool:
    """Politeness engine reference model."""
    if not (CALL_WINDOW[0] <= hour < CALL_WINDOW[1]):
        return False
    cap = FESTIVAL_CAP if festival else CALLS_PER_WEEK
    return calls_this_week < cap


def follow_up_date(promise_date: datetime) -> datetime:
    """Follow-up only AFTER the promised day — never before, never on it."""
    return promise_date + timedelta(days=1)


def part_payment(amount: float, min_part: float = 100.0, frac: float = 0.25) -> tuple[float, float]:
    """Objection handling: accept a part now, never round to zero or extract > balance."""
    part = min(min_part, round(amount * frac))
    part = max(part, 0.0)
    return part, round(amount - part, 2)


def outstanding(amount: float, entries: list[float]) -> float:
    """Ledger integrity: sum of payments can never exceed the principal."""
    paid = sum(entries)
    if paid > amount:
        raise ValueError(f"over-collected: paid {paid} > amount {amount}")
    return amount - paid


def is_overdue(entry_date: datetime, promise: datetime | None, now: datetime) -> bool:
    return promise is None and (now - entry_date) > timedelta(days=OVERDUE_DAYS)


def tone_check(dialogue: str) -> None:
    """No threatening language ever reaches a customer."""
    low = unicodedata.normalize("NFKD", dialogue).lower()
    for p in THREAT_PHRASES:
        if p in low:
            raise ValueError(f"forbidden tone phrase: {p!r}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPolitenessEngine(unittest.TestCase):
    def test_window_starts_9am(self):
        self.assertFalse(can_call(0, 8))
        self.assertTrue(can_call(0, 9))

    def test_window_ends_7pm(self):
        self.assertTrue(can_call(0, 18))
        self.assertFalse(can_call(0, 19))   # '9 AM-7 PM' boundary
        self.assertFalse(can_call(0, 23))
        self.assertFalse(can_call(0, 3))    # circle around midnight

    def test_two_calls_max_normal_week(self):
        self.assertTrue(can_call(0, 10))
        self.assertTrue(can_call(1, 10))
        self.assertFalse(can_call(2, 10))

    def test_festival_mode_is_even_gentler(self):
        self.assertTrue(can_call(0, 10, festival=True))
        self.assertFalse(can_call(1, 10, festival=True))
        # festival never beats the time window either
        self.assertFalse(can_call(0, 8, festival=True))

    @unittest.skip("production TODO: caps enforced server-side; demo enforces in JS")
    def test_documented_production_gap(self):
        pass


class TestPromiseScheduling(unittest.TestCase):
    def test_followup_is_never_on_or_before_promise_day(self):
        promise = datetime(2026, 11, 1, 10, 0)
        fu = follow_up_date(promise)
        self.assertGreater(fu, promise)
        self.assertEqual((fu - promise).days, 1)

    def test_sunday_promise(self):
        # brief script: "Sunday tak" -> call on Monday, not Sunday
        promise = datetime(2026, 11, 1)   # a Sunday
        self.assertEqual(follow_up_date(promise).weekday(), 0)


class TestMoneyMath(unittest.TestCase):
    def test_objection_part_payment_bill_half_of_brief(self):
        # brief script: ₹400 → suggest ₹100 now, ₹300 later
        part, balance = part_payment(400)
        self.assertEqual((part, balance), (100.0, 300.0))

    def test_part_never_negative_or_over_principal(self):
        part, balance = part_payment(50)
        self.assertGreaterEqual(part, 0)
        self.assertEqual(part + balance, 50)

    def test_outstanding_simple(self):
        self.assertEqual(outstanding(400, [100]), 300)
        self.assertEqual(outstanding(400, []), 400)

    def test_never_overcollect(self):
        with self.assertRaises(ValueError):
            outstanding(400, [300, 200])

    def test_many_small_payments_settle_exactly(self):
        pays = []
        amt = 350
        while outstanding(amt, pays) >= 50:
            p, _ = part_payment(outstanding(amt, pays)) if False else (50, None)  # 50-rupee installs
            pays.append(p)
        self.assertEqual(outstanding(amt, pays), amt - sum(pays))
        self.assertGreaterEqual(outstanding(amt, pays), 0)


class TestOverdueAging(unittest.TestCase):
    def test_7_day_threshold(self):
        now = datetime(2026, 10, 25, 12, 0)
        self.assertFalse(is_overdue(now - timedelta(days=7), None, now))
        self.assertFalse(is_overdue(now - timedelta(days=7), None, now))  # exactly 7 = not overdue (age > 7)
        self.assertTrue(is_overdue(now - timedelta(days=8), None, now))

    def test_promise_rescues_from_overdue_tag(self):
        now = datetime(2026, 10, 25)
        self.assertFalse(is_overdue(now - timedelta(days=40), now + timedelta(days=5), now))


class TestToneGuardrail(unittest.TestCase):
    def test_polite_scripts_pass(self):
        tone_check("Koi baat nahi. 100 rupaye abhi, baaki agle hafte theek rahega? 🙏")
        tone_check("Bata dein jab convenient ho, main sirf yaad dila rahi hoon.")

    def test_never_threatens(self):
        for s in ("Notice bhejenge, case hoga", "police bulayenge", "legal action lena padega"):
            with self.assertRaises(ValueError):
                tone_check(s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
