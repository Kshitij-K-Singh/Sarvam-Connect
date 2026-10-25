# उधार दोस्त — Udhaar Dost (demo)

Voice-first credit manager for India's 60M kirana stores. This is the live demo:
**Saaras STT → sarvam-105b-conversations → Bulbul TTS**, all real Sarvam API calls.

## Run

```
python -X utf8 server.py
```

Then open **http://localhost:8000** (allow microphone access).

- Requires `SARVAM_API_KEY` in `../.env`.
- Quits: Ctrl+C in the terminal.

## Story (60-second pitch path through the app)

1. **🎤 Voice Entry** — tap the mic and speak Hinglish ("Ramesh ko kal 350 ka udhaar diya, biscuit aur chai").
   Browser records → 16 kHz WAV → Saaras (`saaras:v3`, `codemix` mode) → 105B-Convos returns slots as strict JSON
   → Bulbul (`bulbul:v3`, voice `ritu`) reads the confirmation back aloud → confirm with one tap.
   Sample chips are the demo-safe path if no mic/network.
2. **📒 Khata** — the structured ledger. Politeness guardrail caps visible: 2 AI calls/week per customer.
3. **📞 Reminder Call** — scripted AI call with branching replies (promise / objection→part-payment / instant UPI / hand-off to human).
   Promise dates are extracted and the follow-up is scheduled *only after* the promised date. Voice-of-customer lines replayed with `neha`.
4. **🌙 Evening Digest** — 60-second spoken summary (Bulbul), totals, overdue-since, follow-up queue, Diwali festival-mode toggle.

## Architecture

```
browser (index.html, zero deps)
   │  wav (base64)        └─ graceful offline fallbacks everywhere
   ▼
server.py (stdlib http.server, :8000)   ← key never leaves here
   ├── /api/stt        → sarvamai.speech_to_text.transcribe(saaras:v3, codemix, unknown)
   ├── /api/structure  → sarvamai.chat.completions(sarvam-105b-conversations)
   └── /api/tts        → sarvamai.text_to_speech.convert(bulbul:v3, ritu/neha, 22 kHz)
```

## Deploy on Render

`render.yaml` at the repo root defines the web service (runtime: python, rootDir: udhaar-dost-demo).

1. Render dashboard → **New → Blueprint** → pick this repo → it reads `render.yaml`.
2. Set `SARVAM_API_KEY` when prompted (stored in Render, never in code).
3. Deploy → health check: `/healthz`.

Notes: server binds `0.0.0.0:$PORT`; `python -X utf8` keeps Devanagari safe on Linux too; and
set `PYTHONUTF8=1`. `/api/stt` needs mic access — browsers require HTTPS for that, which Render provides.

## Design system

The UI is drawn from the bahi-khata itself: the header is the red-cloth book cover
(#7a1f1f) with gold-stamped title, content lives on the ledger paper sheet
(#f6efdf) with the red margin rule (#c24a3b) running down the left, numbers
right-align toward the rule like handwritten entries, and digest totals carry the
bahi double-rule convention. Type: Tiro Devanagari Hindi (display) + Noto Sans Devanagari
(UI). One bold element only — the turmeric mic.

## Run tests

```
node tests/js/frontend.mjs                       # 21 checks — runs the demo's real JS in Node
python -m unittest discover tests -v             # 27 checks — politeness/policy specs + live Sarvam API
python server.py                                 # needed for the live-API tests (SARVAM_API_KEY in ../.env)
```

## Production notes (what the demo stands in for)

- WhatsApp Business voice notes/telephony (Exotel/Twilio) replaces the browser mic for real customers;
  `upi://pay` deep links stay the same.
- LLM call from `/api/structure` includes a guardrail prompt (never threaten, no third-party disclosure);
  frequency/time-window caps live server-side next to the call scheduler.
