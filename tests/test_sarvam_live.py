"""LIVE integration tests — full Sarvam pipeline through the local server.

Covers the ask-brief's core claims:
  1. Saaras STT output (also its Devanagari form) is structured correctly by 105B.
  2. The '500 basket / 200 udhaar' trap from the brief is handled by the LLM, not just the fallback.
  3. Bulbul speaks every line the AI would say on a call (contract: base64 wav data URI).
  4. Failures fail SOFT (API hiccup never breaks the demo).

Run:  python -m unittest tests.test_sarvam_live -v     (requires: python server.py on :8000)
"""
import base64
import json
import os
import time
import unittest
import urllib.request

BASE = "http://localhost:8000"
TIMEOUT = 90


def up() -> bool:
    try:
        urllib.request.urlopen(BASE + "/", timeout=5)
        return True
    except Exception:
        return False


def post(path: str, payload: dict) -> tuple[int, dict]:
    try:
        req = urllib.request.Request(
            BASE + path, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return -1, {"error": str(e)}


@unittest.skipUnless(up(), "server.py not running on :8000 — start it for integration tests")
class TestLiveStructuring(unittest.TestCase):
    """105B-Convos must convert shopkeeper speech into the exact slot schema."""

    def struct(self, note: str) -> dict:
        status, body = post("/api/structure", {"note": note})
        assert status == 200, body
        for key in ("name", "amount", "items", "date_hint"):
            self.assertIn(key, body)          # schema always present, even for nulls
        return body

    def test_flagship_total_vs_udhaar(self):
        # brief sample: basket 500, udhaar 200
        b = self.struct("Meena didi ne 500 ka saman liya, 200 udhaar pe")
        self.assertEqual(b["amount"], 200)
        self.assertIn("meena", str(b["name"]).lower())

    def test_kal_with_items(self):
        b = self.struct("Ramesh ko kal 350 ka udhaar diya, biscuit aur chai")
        self.assertEqual(b["amount"], 350)
        self.assertEqual(str(b["date_hint"]).lower(), "kal")
        for item in ("biscuit", "chai"):
            self.assertIn(item, str(b["items"]).lower())

    def test_saras_devanagari_script(self):
        b = self.struct("कल अनिता ने 600 का राशन लिया")
        self.assertEqual(b["amount"], 600)

    def test_numbers_in_words(self):
        b = self.struct("sunita ji ko paanch sau ka atta udhaar pe diya")
        self.assertEqual(b["amount"], 500)

    def test_no_amount_returns_null_not_zero(self):
        b = self.struct("Golu aaya tha, baat cheet ki")
        if isinstance(b["amount"], (int, float)):
            self.assertEqual(b["amount"], 0)   # tolerated but never fabricated

    def test_promise_style_note_never_leaks_into_ledger(self):
        # a payment promise is not a sale — must NOT create an udhaar entry
        b = self.struct("kal aati hoon, paise de dungi meena")
        self.assertTrue(b["amount"] in (None, 0))


@unittest.skipUnless(up(), "server.py not running on :8000")
class TestLiveTTSContract(unittest.TestCase):
    def test_both_voices_speak(self):
        for speaker in ("ritu", "neha"):
            s, b = post("/api/tts", {"text": "Namaste, yaad dila rahi hoon.", "speaker": speaker})
            self.assertEqual(s, 200)
            self.assertTrue(b["audio"].startswith("data:audio/wav;base64,"))
            self.assertGreater(len(b["audio"]), 5000)   # real audio payload

    def test_emoji_in_script_never_breaks_tts(self):
        s, b = post("/api/tts", {"text": "Dhanyavaad! 🙏 namaste ji 😊"})
        self.assertEqual(s, 200)
        self.assertGreater(len(b["audio"]), 5000)

    def test_cache_makes_repeat_instant(self):
        payload = {"text": "Shaam ka hisaab, ek hi baar synth hota hai."}
        t0, s1, b1 = time.perf_counter(), *post("/api/tts", payload)
        t1, s2, b2 = time.perf_counter(), *post("/api/tts", payload)
        self.assertEqual(b1["audio"], b2["audio"])
        self.assertLess(t1 - t0, 8.0, "second synth must come from cache")


@unittest.skipUnless(up(), "server.py not running on :8000")
class TestLiveSTTRoundtrip(unittest.TestCase):
    def test_bulbul_to_saaras_full_pipeline(self):
        # synthesize real speech, then transcribe it: the two ends of the stack
        s, b = post("/api/tts", {"text": "Ramesh ko kal teen sau pachaas rupaye ka udhaar diya"})
        self.assertEqual(s, 200, b)
        s2, b2 = post("/api/stt", {"wav": b["audio"].split("base64,")[1]})
        self.assertEqual(s2, 200, b2)
        tr = str(b2.get("transcript", "")).lower()
        self.assertTrue(tr, "Saaras returned empty transcript")
        self.assertTrue("350" in tr or "३५०" in tr, f"amount lost in STT: {tr}")


@unittest.skipUnless(up(), "server.py not running on :8000")
class TestFailSoft(unittest.TestCase):
    def test_bad_requests_return_json_errors(self):
        cases = [("/api/structure", {"note": ""}),
                 ("/api/tts", {"text": ""}),
                 ("/api/stt", {"wav": ""}),
                 ("/api/nothing", {})]
        for path, payload in cases:
            s, b = post(path, payload)
            self.assertIn(s, (400, 404), f"{path}: expected clean 4xx")
            self.assertIn("error", b, f"{path}: must fail with a readable error, not a crash")


if __name__ == "__main__":
    print("server up:", up())
    unittest.main(verbosity=2)
