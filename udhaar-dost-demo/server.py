"""Udhaar Dost — tiny local server that proxies the Sarvam APIs.

Serves the demo UI and exposes two endpoints so the browser never holds the key:
  POST /api/structure  -> LLM (sarvam-105b-conversations): voice note -> structured slots
  POST /api/tts        -> Bulbul TTS: any UI text -> base64 audio (spoken, not typed!)

Run:  python server.py     then open  http://localhost:8000
"""
import base64
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Windows consoles default to cp1252 and the Sarvam SDK touches stdio — force UTF-8
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sarvamai import SarvamAI

STATIC = Path(__file__).parent
ENV = Path(__file__).parent.parent / ".env"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}

_tts_cache: dict[str, str] = {}  # text -> data URI
_client: SarvamAI | None = None


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def get_client() -> SarvamAI:
    global _client
    if _client is None:
        _client = SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])
    return _client


STRUCTURE_PROMPT = (
    "You are the structuring brain of 'Udhaar Dost', a credit ledger for Indian kirana shops. "
    "A shopkeeper speaks a Hinglish voice note about lending goods on credit (udhaar). "
    "Extract the slots and respond with ONLY minified JSON, no other text:\n"
    '{"name": "<customer name as spoken, or null>", "amount": <number in rupees, or null>, '
    '"items": "<items mentioned, or null>", "date_hint": "aaj" | "kal" | "parso" | "pichhle" | "none"}\n\n'
    "Rules: 'udhaar pe/diya/liya/khata' means credit sale. Amount is usually the LAST explicit number, "
    "'200 udhaar pe' after a 500 total means udhaar = 200. Names often precede 'ne/ko/se/ki/ka'. "
    "Voice note: "
)


def structure_voice_note(note: str) -> dict:
    resp = get_client().chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": STRUCTURE_PROMPT + note}],
    )
    content = resp.choices[0].message.content.strip()
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        raise ValueError("LLM returned no JSON: " + content[:200])
    return json.loads(m.group(0))


def tts(text: str, speaker: str) -> str:
    text = re.sub(r"[🪔📞🌙✅📝🎉🙏😊🟡⚠️]|[\U0001F300-\U0001FAFF]", "", text)
    key = (speaker, text)
    if key not in _tts_cache:
        audio = get_client().text_to_speech.convert(
            text=text[:500],
            language_code="hi-IN",
            speaker=speaker,          # ritu = AI assistant, neha = customer voice
            model="bulbul:v3",
            speech_sample_rate=22050,
        )
        _tts_cache[key] = "data:audio/wav;base64," + audio.audios[0]
    return _tts_cache[key]


def stt(wav: bytes) -> dict:
    """Saaras STT — code-mixed Hinglish speech -> transcript."""
    resp = get_client().speech_to_text.transcribe(
        file=("note.wav", wav, "audio/wav"),
        model="saaras:v3",
        mode="codemix",          # keeps Hinglish intact ("500 ka saman liya")
        language_code="unknown",  # auto-detect the Indic language
    )
    data = resp.transcript
    return {"transcript": data if isinstance(data, str) else getattr(data, "transcript", str(data))}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter logs
        pass

    def _json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, url_path: str) -> bool:
        """Serve a file from the demo folder — whitelisted types, no path traversal."""
        rel = url_path.lstrip("/")
        suffix = Path(rel).suffix.lower()
        if suffix not in MIME:
            return False
        try:
            target = (STATIC / rel).resolve()
            target.relative_to(STATIC.resolve())   # escapes the folder -> refuse
        except (OSError, ValueError):
            return False
        if not target.is_file():
            return False
        try:
            body = target.read_bytes()
        except OSError:
            return False
        self.send_response(200)
        self.send_header("Content-Type", MIME[suffix])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)
        return True

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            page = (STATIC / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", MIME[".html"])
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        elif path == "/healthz":          # Render health check
            self._json({"ok": True})
        elif self._static(path):
            pass
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/stt":
                raw = str(data.get("wav", "")).split("base64,")[-1]
                if not raw:
                    return self._json({"error": "empty audio"}, 400)
                self._json(stt(base64.b64decode(raw)))
            elif self.path == "/api/structure":
                if not data.get("note"):
                    return self._json({"error": "empty note"}, 400)
                self._json(structure_voice_note(data["note"][:300]))
            elif self.path == "/api/tts":
                if not data.get("text"):
                    return self._json({"error": "empty text"}, 400)
                self._json({"audio": tts(data["text"], str(data.get("speaker", "ritu")))})
            else:
                self._json({"error": "not found"}, 404)
        except Exception as exc:  # noqa: BLE001 — fail soft so the demo never dies
            self._json({"error": str(exc)}, 502)


if __name__ == "__main__":
    load_env(ENV)
    if not os.environ.get("SARVAM_API_KEY"):
        raise SystemExit("SARVAM_API_KEY missing in ../.env")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Udhaar Dost live on http://localhost:{port}  (Sarvam: Saaras STT + 105B-Convos + Bulbul TTS)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
