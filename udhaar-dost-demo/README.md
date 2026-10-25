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

The page is drawn from the bahi-khata's night paper: dark ledger ground (`--page:#171411` sections,
`#221e19` cover cloth) with gold-stamped type, and one running motif lifted from the book itself —
the **red margin rule**, which draws itself full-width under the header, runs down each section as
a gutter rule, misprints as chip bullets and marks the active tab. Type: **Archivo** (single Latin
webfont, fluid `clamp()` sizes); Hindi renders through system Devanagari fallbacks — no Devanagari
webfont is downloaded. One bold element only — the turmeric mic.

Accessibility & **language toggle**: five colour schemes (मूल / उजाला / राहत / रात / काला-पीला,
persisted in `ud-theme`), font steps (85%–145%, `ud-fs`), and a हिंदी ⇄ English toggle (`ud-lang`)
applied pre-paint (no language flash on refresh). Static copy swaps via `data-i18n` + `EN_DICT`;
dynamic strings go through a bilingual `T()` helper; `<html lang>` follows the choice.

Imagery: four Creative-Commons photographs of the bazaar world the ledger lives in — Main Bazaar
Paharganj (Argenberg, CC BY 4.0), Khari Baoli (Haugen, CC BY 2.0), Kolkata New Market spices
(Savage, CC BY 2.0), and the account-book of Thomas Mister (Wellcome Collection, CC BY 4.0) —
each credited inline in a bilingual caption; full details in `assets/credits.json`.

## Run tests

```
node tests/js/frontend.mjs                       # 33 checks — runs the demo's real JS in Node
                                                 #   (incl. section G: language-toggle gates)
python -m unittest discover tests -v             # 27 checks — politeness/policy specs + live Sarvam API
python server.py                                 # needed for the live-API tests (SARVAM_API_KEY in ../.env)
```

## Production notes (what the demo stands in for)

- WhatsApp Business voice notes/telephony (Exotel/Twilio) replaces the browser mic for real customers;
  `upi://pay` deep links stay the same.
- LLM call from `/api/structure` includes a guardrail prompt (never threaten, no third-party disclosure);
  frequency/time-window caps live server-side next to the call scheduler.
