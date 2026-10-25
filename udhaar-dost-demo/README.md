# উधार दोस्त — Udhaar Dost (demo)

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

## Production notes (what the demo stands in for)

- WhatsApp Business voice notes/telephony (Exotel/Twilio) replaces the browser mic for real customers;
  `upi://pay` deep links stay the same.
- LLM call from `/api/structure` includes a guardrail prompt (never threaten, no third-party disclosure);
  frequency/time-window caps live server-side next to the call scheduler.
