"""FastAPI wrapper around Kokoro TTS.

Endpoints:
    GET  /health          → {"status": "ok"}
    POST /tts             → {"audio_file": "...", "duration_seconds": N}
    POST /convert         → {"mp3_file": "...", "size_bytes": N}
    GET  /weekly-report   → {"xlsx_file": "...", "filename": "...", "rows": N}
    POST /whatsapp        → {"sid": "...", "status": "queued"}
    GET  /audio/{file}    → binary MP3/WAV
    GET  /reports/{file}  → binary XLSX

Environment variables for WhatsApp (Twilio):
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_FROM    (default: whatsapp:+14155238886)
    TWILIO_TO      (default: whatsapp:+5541988667710)

Run from the project root:
    .venv/bin/uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800
"""

from __future__ import annotations

import datetime as dt
import io
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import lameenc
import numpy as np
import openpyxl
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from kokoro import KPipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_SA_KEY = PROJECT_ROOT / "credentials" / "campuscast-n8n.json"
_SHEET_ID = os.environ.get(
    "CAMPUSCAST_SHEET_ID",
    "1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk",
)
_SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


_MARKDOWN_STRIP_PATTERNS = [
    (re.compile(r"\*\*(.+?)\*\*", re.S), r"\1"),
    (re.compile(r"__(.+?)__", re.S), r"\1"),
    (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S), r"\1"),
    (re.compile(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", re.S), r"\1"),
    (re.compile(r"`+(.+?)`+", re.S), r"\1"),
    (re.compile(r"^\s{0,3}#{1,6}\s+", re.M), ""),
    (re.compile(r"^\s{0,3}>\s*", re.M), ""),
    (re.compile(r"^\s{0,3}[-*+]\s+", re.M), ""),
    (re.compile(r"^\s{0,3}\d+\.\s+", re.M), ""),
    (re.compile(r"[*_`~#>]"), ""),
    (re.compile(r"\n{3,}"), "\n\n"),
]


def strip_markup(text: str) -> str:
    """Remove markdown-like characters so the TTS engine does not pronounce them."""
    cleaned = text
    for pattern, replacement in _MARKDOWN_STRIP_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned.strip()


AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

LANG_PT_BR = "p"
DEFAULT_VOICE = "pf_dora"
SAMPLE_RATE = 24000
MAX_TEXT_CHARS = 5000

app = FastAPI(title="CampusCast Kokoro TTS", version="0.1.0")
pipeline = KPipeline(lang_code=LANG_PT_BR)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS)
    voice: Optional[str] = DEFAULT_VOICE


class TTSResponse(BaseModel):
    audio_file: str
    duration_seconds: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tts", response_model=TTSResponse)
def tts(req: TTSRequest) -> TTSResponse:
    voice = req.voice or DEFAULT_VOICE
    cleaned = strip_markup(req.text)
    if not cleaned:
        raise HTTPException(status_code=400, detail="kokoro_tts: text empty after markup strip")
    try:
        generator = pipeline(cleaned, voice=voice)
        chunks = [audio for _, _, audio in generator]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"kokoro_tts: {type(e).__name__}: {e}")

    if not chunks:
        raise HTTPException(status_code=500, detail="kokoro_tts: no audio produced")

    audio = np.concatenate(chunks)
    timestamp = dt.datetime.now().isoformat(timespec="seconds").replace(":", "-")
    out_path = AUDIO_DIR / f"{timestamp}.wav"
    sf.write(out_path, audio, SAMPLE_RATE)

    return TTSResponse(
        audio_file=str(out_path),
        duration_seconds=round(len(audio) / SAMPLE_RATE, 2),
    )


# ---------------------------------------------------------------------------
# WAV → MP3 conversion
# ---------------------------------------------------------------------------

def _wav_to_mp3(wav_path: Path) -> Path:
    data, samplerate = sf.read(str(wav_path), dtype="float32")
    if data.ndim > 1:
        data = data[:, 0]
    pcm = (data * 32767).astype(np.int16)
    enc = lameenc.Encoder()
    enc.set_bit_rate(128)
    enc.set_in_sample_rate(samplerate)
    enc.set_channels(1)
    enc.set_quality(2)
    mp3_bytes = enc.encode(pcm.tobytes()) + enc.flush()
    mp3_path = wav_path.with_suffix(".mp3")
    mp3_path.write_bytes(mp3_bytes)
    return mp3_path


class ConvertRequest(BaseModel):
    wav_path: str


@app.post("/convert")
def convert_wav_to_mp3(req: ConvertRequest) -> dict:
    wav = PROJECT_ROOT / req.wav_path
    if not wav.exists():
        raise HTTPException(status_code=400, detail=f"WAV not found: {req.wav_path}")
    try:
        mp3 = _wav_to_mp3(wav)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {e}")
    return {
        "mp3_file": str(mp3.relative_to(PROJECT_ROOT)),
        "size_bytes": mp3.stat().st_size,
    }


# ---------------------------------------------------------------------------
# Weekly XLSX report
# ---------------------------------------------------------------------------

@app.get("/weekly-report")
def weekly_report() -> dict:
    if not _SA_KEY.exists():
        raise HTTPException(status_code=503, detail="Service account key not found")
    creds = Credentials.from_service_account_file(str(_SA_KEY), scopes=_SHEETS_SCOPES)
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=_SHEET_ID, range="results!A:M")
        .execute()
    )
    values = result.get("values", [])
    if len(values) < 2:
        raise HTTPException(status_code=404, detail="No results data in sheet yet")

    headers = values[0]
    last_seven = values[1:][-7:]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Semana"
    ws.append(headers)
    for row in last_seven:
        padded = row + [""] * max(0, len(headers) - len(row))
        ws.append(padded[: len(headers)])

    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    week_label = datetime.now(timezone.utc).strftime("%Y-W%V")
    filename = f"campuscast-semana-{week_label}.xlsx"
    xlsx_path = reports_dir / filename
    wb.save(str(xlsx_path))

    return {
        "xlsx_file": str(xlsx_path.relative_to(PROJECT_ROOT)),
        "filename": filename,
        "rows": len(last_seven),
    }


# ---------------------------------------------------------------------------
# Static file serving (bypasses n8n N8N_RESTRICT_FILE_ACCESS_TO)
# ---------------------------------------------------------------------------

@app.get("/audio/{filename}")
def serve_audio(filename: str):
    file_path = PROJECT_ROOT / "audio" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    media = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    return FileResponse(str(file_path), media_type=media)


@app.get("/reports/{filename}")
def serve_report(filename: str):
    file_path = PROJECT_ROOT / "reports" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    return FileResponse(
        str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# WhatsApp via Twilio (credentials kept server-side in env vars)
# ---------------------------------------------------------------------------

import httpx

_TWILIO_SID   = os.environ.get("TWILIO_ACCOUNT_SID", "")
_TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
_TWILIO_FROM  = os.environ.get("TWILIO_FROM", "whatsapp:+14155238886")
_TWILIO_TO    = os.environ.get("TWILIO_TO",   "whatsapp:+5541988667710")


class WhatsAppRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=1600)
    to: Optional[str] = None


@app.post("/whatsapp")
def send_whatsapp(req: WhatsAppRequest) -> dict:
    sid   = _TWILIO_SID
    token = _TWILIO_TOKEN
    if not sid or not token:
        raise HTTPException(status_code=503, detail="Twilio credentials not configured (set TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN)")
    to = req.to or _TWILIO_TO
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        r = httpx.post(
            url,
            auth=(sid, token),
            data={"From": _TWILIO_FROM, "To": to, "Body": req.body},
            timeout=15,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Twilio error {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Twilio request failed: {e}")
    data = r.json()
    return {"sid": data.get("sid"), "status": data.get("status")}
