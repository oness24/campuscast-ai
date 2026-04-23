"""FastAPI wrapper around Kokoro TTS.

Endpoints:
    GET  /health       → {"status": "ok"}
    POST /tts          → {"audio_file": "...", "duration_seconds": N}

The server writes WAVs to ./audio/<iso-timestamp>.wav relative to the
current working directory and returns the relative path.

Run from the project root:
    .venv/bin/uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from kokoro import KPipeline


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
