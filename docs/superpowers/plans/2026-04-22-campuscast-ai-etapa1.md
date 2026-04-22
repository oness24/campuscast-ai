# CampusCast AI — Etapa 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a working Etapa 1 prototype of CampusCast AI — an n8n workflow that fetches Open-Meteo weather + Google Sheets events, asks `llama3.1:8b` (Ollama) for a Portuguese bulletin, sends it to a local Kokoro FastAPI server for TTS, and appends the result to Google Sheets.

**Architecture:** Single-machine Linux prototype. Three localhost services (n8n on 5678, Ollama on 11434 — existing, Kokoro on 8800 — new). n8n owns orchestration + Sheets I/O. A small FastAPI wrapper hosts Kokoro. Python smoke tests (via `requests`) validate each external call before wiring into n8n.

**Tech Stack:** n8n (`npx n8n`), Ollama 0.17.0 (already installed), `llama3.1:8b` (already pulled), Python 3.12 + FastAPI + Kokoro TTS, Google Sheets API (OAuth2). Reference spec: `docs/superpowers/specs/2026-04-22-campuscast-ai-etapa1-design.md`.

**Pre-flight state (already true):**
- `/usr/bin/git`, `/usr/bin/python3`, `/usr/bin/node` (v22), `/usr/bin/npx`, `/usr/bin/docker`, `pnpm` all installed.
- Ollama running at `localhost:11434`, model `llama3.1:8b` present.
- NVIDIA GPU, 31 GB RAM, 16 cores — capacity is not a concern.
- Working directory `/home/oness24/Desktop/AI/pucpr/campuscast-ai` contains `docs/`, `examples/`, `README.md`, and a 665 MB `n8n/` source clone (to be removed in Task 8).
- No `.git` directory exists yet.

---

## File Structure

Files this plan creates or modifies, in dependency order:

| File | Purpose | Created in |
|---|---|---|
| `.gitignore` | Ignore `audio/`, `.venv/`, `__pycache__/`, secrets | Task 1 |
| `tools/requirements.txt` | Python pins for smoke tests + Kokoro server | Task 1 |
| `tools/smoke.py` | Python HTTP probes for Open-Meteo, Ollama, Kokoro (ID 2.1 compliance) | Tasks 3, 4, 7 |
| `tools/smoke_weather.sh` | bash wrapper → `python tools/smoke.py --only weather` | Task 3 |
| `tools/smoke_ollama.sh` | bash wrapper → `--only ollama` | Task 4 |
| `tools/smoke_kokoro.sh` | bash wrapper → `--only kokoro` | Task 7 |
| `tools/kokoro_server.py` | FastAPI server: `POST /tts`, `GET /health` | Task 6 |
| `workflow/campuscast.workflow.json` | n8n workflow exported after manual build | Task 12 |
| `audio/.gitkeep` | Keep audio dir in git (WAVs themselves ignored) | Task 1 |
| `docs/07-setup-evidence.md` | ID 2.1 evidence log | Task 15 |

Removed: the cloned `n8n/` source tree (Task 8).

---

## Task 1: Project scaffolding + git init

**Files:**
- Create: `.gitignore`
- Create: `tools/requirements.txt`
- Create: `tools/` (directory)
- Create: `workflow/` (directory)
- Create: `audio/.gitkeep`

- [ ] **Step 1: Initialize git repository**

Run:
```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
git init
git config user.email "onesmus.simiyu@pucpr.edu.br"
git config user.name "Onesmus Simiyu"
```

Expected: `Initialized empty Git repository in .../campuscast-ai/.git/`.

- [ ] **Step 2: Create `.gitignore`**

Write to `/home/oness24/Desktop/AI/pucpr/campuscast-ai/.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/

# Generated audio (keep the folder via .gitkeep, ignore the WAVs)
audio/*.wav
audio/*.mp3

# n8n local state
.n8n/

# Editor
.vscode/
.idea/

# Secrets
.env
*.env.local
credentials/*.json
!credentials/.gitkeep

# The huge cloned n8n source tree (safety net in case it isn't removed yet)
n8n/
```

- [ ] **Step 3: Create directory skeleton**

Run:
```bash
mkdir -p tools workflow audio
touch audio/.gitkeep
```

- [ ] **Step 4: Create `tools/requirements.txt`**

Write to `/home/oness24/Desktop/AI/pucpr/campuscast-ai/tools/requirements.txt`:

```txt
requests==2.32.3
fastapi==0.115.0
uvicorn[standard]==0.30.6
soundfile==0.12.1
kokoro==0.9.2
```

(Version pins are conservative current stable. If `pip install` fails for `kokoro==0.9.2`, drop the pin in Task 5.)

- [ ] **Step 5: First commit**

Run:
```bash
git add .gitignore tools/requirements.txt audio/.gitkeep
git commit -m "chore: initialize project scaffolding"
```

Expected: a commit with three new files.

---

## Task 2: Python virtual environment

**Files:** none created; only local `.venv/` directory (git-ignored).

- [ ] **Step 1: Create venv**

Run:
```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
python3 -m venv .venv
source .venv/bin/activate
python -V
```

Expected: `Python 3.12.x`. Prompt now shows `(.venv)`.

- [ ] **Step 2: Upgrade pip**

Run:
```bash
pip install --upgrade pip
```

Expected: pip upgrades to latest.

- [ ] **Step 3: Install `requests` only (smaller, unblocks Tasks 3-4)**

We only need `requests` before Task 5. Kokoro/FastAPI come later.

Run:
```bash
pip install requests==2.32.3
python -c "import requests; print(requests.__version__)"
```

Expected: `2.32.3`.

- [ ] **Step 4: No commit** — venv is git-ignored. Move to Task 3.

---

## Task 3: Open-Meteo smoke probe

**Files:**
- Create: `tools/smoke.py`
- Create: `tools/smoke_weather.sh`

- [ ] **Step 1: Write `tools/smoke.py` skeleton with weather probe**

Write to `/home/oness24/Desktop/AI/pucpr/campuscast-ai/tools/smoke.py`:

```python
"""CampusCast AI smoke tests.

Runs Python HTTP probes against the three external services the workflow
depends on. Satisfies ID 2.1 ("chamadas HTTP em Python").

Usage:
    python tools/smoke.py               # run all three probes
    python tools/smoke.py --only weather
    python tools/smoke.py --only ollama
    python tools/smoke.py --only kokoro
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Callable

import requests

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=-25.4284&longitude=-49.2733"
    "&current=temperature_2m,relative_humidity_2m,precipitation,rain,"
    "weather_code,wind_speed_10m"
    "&timezone=America/Sao_Paulo"
)
OLLAMA_URL = "http://localhost:11434/api/generate"
KOKORO_URL = "http://localhost:8800/tts"

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


@dataclass
class ProbeResult:
    name: str
    ok: bool
    detail: str


def probe_weather() -> ProbeResult:
    try:
        r = requests.get(OPEN_METEO_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        temp = data["current"]["temperature_2m"]
        if not isinstance(temp, (int, float)):
            return ProbeResult("weather", False, f"temperature_2m not numeric: {temp!r}")
        return ProbeResult("weather", True, f"Curitiba temperature_2m={temp} C")
    except Exception as e:
        return ProbeResult("weather", False, f"{type(e).__name__}: {e}")


def probe_ollama() -> ProbeResult:
    return ProbeResult("ollama", False, "not implemented yet (Task 4)")


def probe_kokoro() -> ProbeResult:
    return ProbeResult("kokoro", False, "not implemented yet (Task 7)")


PROBES: dict[str, Callable[[], ProbeResult]] = {
    "weather": probe_weather,
    "ollama": probe_ollama,
    "kokoro": probe_kokoro,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="CampusCast AI smoke tests")
    parser.add_argument(
        "--only",
        choices=sorted(PROBES),
        help="Run only the named probe. Default runs all probes.",
    )
    args = parser.parse_args()

    names = [args.only] if args.only else list(PROBES)
    results: list[ProbeResult] = []
    for name in names:
        result = PROBES[name]()
        results.append(result)
        color = GREEN if result.ok else RED
        marker = "PASS" if result.ok else "FAIL"
        print(f"{color}[{marker}]{RESET} {result.name}: {result.detail}")

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the weather probe**

Run:
```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
source .venv/bin/activate
python tools/smoke.py --only weather
```

Expected: `[PASS] weather: Curitiba temperature_2m=<some number> C`. Exit code 0.

If FAIL: check internet connectivity; Open-Meteo is public and does not require auth.

- [ ] **Step 3: Create bash wrapper**

Write to `/home/oness24/Desktop/AI/pucpr/campuscast-ai/tools/smoke_weather.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tools/smoke.py --only weather "$@"
```

Make it executable:
```bash
chmod +x tools/smoke_weather.sh
```

- [ ] **Step 4: Verify wrapper works**

Run:
```bash
./tools/smoke_weather.sh
```

Expected: same PASS output as Step 2.

- [ ] **Step 5: Commit**

```bash
git add tools/smoke.py tools/smoke_weather.sh
git commit -m "feat(smoke): add Python HTTP probe for Open-Meteo weather"
```

---

## Task 4: Ollama smoke probe

**Files:**
- Modify: `tools/smoke.py` (replace `probe_ollama` stub)
- Create: `tools/smoke_ollama.sh`

- [ ] **Step 1: Confirm Ollama is running and `llama3.1:8b` is loaded**

Run:
```bash
curl -s http://localhost:11434/api/tags | python -m json.tool
```

Expected: JSON listing `llama3.1:8b` among the models. If not, `ollama pull llama3.1:8b`.

- [ ] **Step 2: Replace `probe_ollama` with real implementation**

Open `tools/smoke.py` and replace the entire `probe_ollama` stub with:

```python
def probe_ollama() -> ProbeResult:
    body = {
        "model": "llama3.1:8b",
        "prompt": "Responda em uma frase curta: qual é a capital do Brasil?",
        "stream": False,
    }
    try:
        r = requests.post(OLLAMA_URL, json=body, timeout=60)
        r.raise_for_status()
        data = r.json()
        response = data.get("response", "")
        if not isinstance(response, str) or not response.strip():
            return ProbeResult("ollama", False, f"empty/invalid response: {response!r}")
        preview = response.strip().replace("\n", " ")[:120]
        return ProbeResult("ollama", True, f"{len(response)} chars — {preview!r}")
    except Exception as e:
        return ProbeResult("ollama", False, f"{type(e).__name__}: {e}")
```

- [ ] **Step 3: Run the probe**

Run:
```bash
python tools/smoke.py --only ollama
```

Expected: `[PASS] ollama: <N> chars — 'A capital do Brasil é Brasília...'`. Exit 0. First call may take 5-30 seconds while the model loads into GPU memory.

- [ ] **Step 4: Create bash wrapper**

Write to `/home/oness24/Desktop/AI/pucpr/campuscast-ai/tools/smoke_ollama.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tools/smoke.py --only ollama "$@"
```

Make executable:
```bash
chmod +x tools/smoke_ollama.sh
```

- [ ] **Step 5: Verify both probes run together**

Run:
```bash
python tools/smoke.py
```

Expected: weather PASS, ollama PASS, kokoro FAIL ("not implemented yet"). Exit code 1 (because kokoro fails).

- [ ] **Step 6: Commit**

```bash
git add tools/smoke.py tools/smoke_ollama.sh
git commit -m "feat(smoke): add Python HTTP probe for local Ollama llama3.1:8b"
```

---

## Task 5: Install Kokoro + verify pt-BR voice quality

This task resolves open item §11.1 from the spec: does Kokoro's Brazilian Portuguese voice sound good enough? If not, we fall back to Piper TTS.

**Files:** none created in this task. Optionally updates `tools/requirements.txt` if a fallback is needed.

- [ ] **Step 1: Install full Python dependencies**

Run:
```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
source .venv/bin/activate
pip install -r tools/requirements.txt
```

Expected: `requests`, `fastapi`, `uvicorn`, `soundfile`, `kokoro` installed. `kokoro` installation may fetch additional PyTorch deps (~2 GB). Takes 3-10 minutes on first run.

If `kokoro==0.9.2` is unavailable on PyPI, relax the pin:
```bash
pip install kokoro
```
and update `tools/requirements.txt` to reflect the installed version (run `pip freeze | grep kokoro` to get the exact version).

- [ ] **Step 2: Write a standalone voice-quality probe**

Write a throwaway script at `/tmp/kokoro_voice_check.py`:

```python
"""One-off: synthesize a pt-BR sentence and write it to /tmp/kokoro_check.wav."""
import soundfile as sf
from kokoro import KPipeline

pipeline = KPipeline(lang_code="p")  # 'p' = Brazilian Portuguese
text = (
    "Bom dia. Este é um teste do CampusCast AI. "
    "A temperatura em Curitiba é agradável e não há previsão de chuva."
)
generator = pipeline(text, voice="pf_dora")
audio_chunks = [audio for _, _, audio in generator]
if not audio_chunks:
    raise SystemExit("kokoro produced no audio")

import numpy as np
audio = np.concatenate(audio_chunks)
sf.write("/tmp/kokoro_check.wav", audio, 24000)
print(f"wrote /tmp/kokoro_check.wav ({len(audio)} samples, {len(audio)/24000:.1f}s)")
```

Run:
```bash
python /tmp/kokoro_voice_check.py
```

Expected: a `.wav` file is written. Size should be > 50 KB for that many words.

- [ ] **Step 3: Listen to the output**

Play the file:
```bash
# any of these, depending on what's installed:
aplay /tmp/kokoro_check.wav    # ALSA
paplay /tmp/kokoro_check.wav   # PulseAudio
ffplay -autoexit /tmp/kokoro_check.wav  # FFmpeg
```

Judgment call:
- **If pt-BR is intelligible and sounds natural:** PASS. Proceed to Task 6.
- **If pt-BR is garbled, English-accented, or unintelligible:** FAIL — execute the Piper fallback below.

- [ ] **Step 4 (only if Kokoro pt-BR failed): Piper TTS fallback**

Install Piper:
```bash
pip install piper-tts
```

Download a Brazilian Portuguese voice:
```bash
mkdir -p ~/.local/share/piper-voices/pt_BR
cd ~/.local/share/piper-voices/pt_BR
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json
```

Test:
```bash
echo "Bom dia. Este é um teste com Piper." | piper \
  --model ~/.local/share/piper-voices/pt_BR/pt_BR-faber-medium.onnx \
  --output_file /tmp/piper_check.wav
aplay /tmp/piper_check.wav
```

If Piper sounds better, update `tools/requirements.txt` to add `piper-tts` and mark Task 6 as "use Piper instead of Kokoro" — the FastAPI server code swaps one generator call for another, but endpoint contract stays the same.

- [ ] **Step 5: Record the decision in scratch notes**

Append a line to `/tmp/campuscast_decisions.md` (we'll fold this into the evidence doc in Task 15):

```text
TTS engine chosen: <Kokoro | Piper>
Voice: <pf_dora | pt_BR-faber-medium>
Reason: <one sentence>
```

- [ ] **Step 6: Commit requirements update (if any)**

If `tools/requirements.txt` changed:
```bash
git add tools/requirements.txt
git commit -m "chore: pin TTS dependencies after voice-quality check"
```

Otherwise, no commit needed — move to Task 6.

---

## Task 6: Kokoro FastAPI server

**Files:**
- Create: `tools/kokoro_server.py`

> **Note:** Code below assumes Kokoro won Task 5. If Piper won, replace the `KPipeline` import + `_synthesize` body with `piper.PiperVoice.load(...)` and `voice.synthesize(...)`. Endpoint contract is unchanged.

- [ ] **Step 1: Write the server**

Write to `/home/oness24/Desktop/AI/pucpr/campuscast-ai/tools/kokoro_server.py`:

```python
"""FastAPI wrapper around Kokoro TTS.

Endpoints:
    GET  /health       → {"status": "ok"}
    POST /tts          → {"audio_file": "...", "duration_seconds": N}

The server writes WAVs to ./audio/<iso-timestamp>.wav relative to the
current working directory and returns the relative path.

Run:
    uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from kokoro import KPipeline

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
    try:
        generator = pipeline(req.text, voice=voice)
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
```

- [ ] **Step 2: Start the server in a dedicated terminal**

Open a new terminal (keep it running throughout the remaining tasks):

```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
source .venv/bin/activate
uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800
```

Expected: `Uvicorn running on http://127.0.0.1:8800 (Press CTRL+C to quit)` and a log line about Kokoro pipeline loading.

- [ ] **Step 3: Test `/health` in your main terminal**

Run:
```bash
curl -s http://localhost:8800/health
```

Expected: `{"status":"ok"}`.

- [ ] **Step 4: Test `/tts` end-to-end**

Run:
```bash
curl -s -X POST http://localhost:8800/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bom dia. Este é um teste do CampusCast AI."}' | python -m json.tool
```

Expected:
```json
{
    "audio_file": "audio/2026-04-22T14-30-02.wav",
    "duration_seconds": 3.5
}
```

Confirm the file exists and plays:
```bash
ls -la audio/
aplay audio/2026-04-22T14-*.wav
```

- [ ] **Step 5: Commit**

```bash
git add tools/kokoro_server.py
git commit -m "feat: add FastAPI Kokoro TTS server on :8800"
```

---

## Task 7: Kokoro smoke probe

**Files:**
- Modify: `tools/smoke.py` (replace `probe_kokoro` stub)
- Create: `tools/smoke_kokoro.sh`

- [ ] **Step 1: Ensure Kokoro server is running on :8800**

In a separate terminal:
```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
source .venv/bin/activate
uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800
```

- [ ] **Step 2: Replace `probe_kokoro` in `tools/smoke.py`**

Open `tools/smoke.py` and replace the entire `probe_kokoro` stub with:

```python
def probe_kokoro() -> ProbeResult:
    body = {"text": "Bom dia. Este é um teste do CampusCast AI."}
    try:
        r = requests.post(KOKORO_URL, json=body, timeout=120)
        r.raise_for_status()
        data = r.json()
        audio_file = data.get("audio_file")
        if not audio_file or not isinstance(audio_file, str):
            return ProbeResult("kokoro", False, f"no audio_file in response: {data!r}")
        # Resolve relative to the project root (smoke.py sits in tools/).
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(project_root, audio_file)
        if not os.path.exists(full_path):
            return ProbeResult("kokoro", False, f"audio file missing: {full_path}")
        size = os.path.getsize(full_path)
        if size < 1024:
            return ProbeResult("kokoro", False, f"audio file too small: {size} bytes")
        duration = data.get("duration_seconds", 0)
        return ProbeResult("kokoro", True, f"{audio_file} ({size} bytes, {duration}s)")
    except Exception as e:
        return ProbeResult("kokoro", False, f"{type(e).__name__}: {e}")
```

- [ ] **Step 3: Run the full smoke suite**

Run:
```bash
python tools/smoke.py
```

Expected: all three PASS, exit code 0.

```text
[PASS] weather: Curitiba temperature_2m=19.4 C
[PASS] ollama: 47 chars — 'A capital do Brasil é Brasília.'
[PASS] kokoro: audio/2026-04-22T...wav (180432 bytes, 3.5s)
```

- [ ] **Step 4: Create bash wrapper**

Write to `/home/oness24/Desktop/AI/pucpr/campuscast-ai/tools/smoke_kokoro.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tools/smoke.py --only kokoro "$@"
```

Make executable:
```bash
chmod +x tools/smoke_kokoro.sh
```

- [ ] **Step 5: Commit**

```bash
git add tools/smoke.py tools/smoke_kokoro.sh
git commit -m "feat(smoke): add Python HTTP probe for Kokoro TTS server"
```

---

## Task 8: Remove cloned n8n source tree

**Files:**
- Delete: `n8n/` (665 MB)

- [ ] **Step 1: Confirm folder is not needed**

We're running n8n via `npx n8n`. The cloned source is only useful if modifying n8n itself — not in scope.

- [ ] **Step 2: Remove it**

Run:
```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
rm -rf n8n/
```

- [ ] **Step 3: Verify**

Run:
```bash
ls -la
```

Expected: no `n8n/` directory. `audio/`, `docs/`, `examples/`, `tools/`, `workflow/`, `.venv/`, `.git/`, `README.md`, `.gitignore` remain.

- [ ] **Step 4: No commit needed** — the folder was never added to git (`.gitignore` has `n8n/`).

---

## Task 9: Start n8n

**Files:** none. State persists to `~/.n8n/`.

- [ ] **Step 1: Launch n8n in a dedicated terminal**

Open a third terminal (alongside Kokoro server terminal):

```bash
npx n8n
```

Expected: npx downloads n8n on first run (~1-2 GB, 3-5 minutes). Eventually prints:
```text
Editor is now accessible via:
http://localhost:5678
```

- [ ] **Step 2: Open the editor**

Navigate to `http://localhost:5678` in a browser.

Expected: the n8n first-run onboarding screen.

- [ ] **Step 3: Complete onboarding**

Enter an email + password for the owner account. **Write these down — n8n stores them locally and you'll need them to log back in.**

- [ ] **Step 4: Verify you can create a workflow**

From the n8n home, click "New Workflow." Expected: an empty canvas with the "Start" node.

Cancel / discard this trial workflow — we'll build the real one in Task 12.

- [ ] **Step 5: No commit.** Move to Task 10.

---

## Task 10: Google Cloud OAuth setup

This is the gnarliest UI task in the project. It enables n8n to read/write your Google Sheets.

**Files:** none in-repo. Stores credentials in n8n's local DB.

- [ ] **Step 1: Create a Google Cloud project**

Browse to `https://console.cloud.google.com/projectcreate` (sign in with your PUCPR or personal Google account).

- Project name: `CampusCast AI`
- Location: leave as "No organization" (unless PUCPR has a workspace you want to use)
- Click Create.

- [ ] **Step 2: Enable the Google Sheets API**

In the left nav, go to APIs & Services → Library.
Search for "Google Sheets API" → click it → click **Enable**.

Also enable **Google Drive API** (required by n8n's Sheets node to list spreadsheets).

- [ ] **Step 3: Configure the OAuth consent screen**

APIs & Services → OAuth consent screen.

- User Type: **External**. Click Create.
- App name: `CampusCast AI`
- User support email: your email
- Developer contact: your email
- Click Save and Continue through Scopes (skip, leave default) and Test users.
- **In Test users, add your own Google account email.** Required for OAuth to work before the app is "verified" (which we don't need).
- Save and return to dashboard.

- [ ] **Step 4: Create OAuth 2.0 Client credentials**

APIs & Services → Credentials → Create Credentials → OAuth client ID.

- Application type: **Web application**
- Name: `CampusCast AI n8n`
- Authorized redirect URIs — add:
  ```
  http://localhost:5678/rest/oauth2-credential/callback
  ```
- Click Create.
- A dialog shows Client ID and Client Secret. **Copy both to a scratchpad.** (Also click Download JSON and save it somewhere safe, e.g. outside the repo.)

- [ ] **Step 5: Create a Google Sheets OAuth2 credential in n8n**

Back in the n8n editor (`http://localhost:5678`):

- Left nav → Credentials → **New** → search "Google Sheets OAuth2 API".
- Paste Client ID and Client Secret from Step 4.
- Click **Sign in with Google**. Complete the OAuth flow with your test-user Google account.
- Name the credential `Google Sheets — CampusCast`.
- Save.

- [ ] **Step 6: Verify credential works**

n8n credentials list should show the new credential with a green checkmark.

- [ ] **Step 7: Document the OAuth steps in scratch notes**

Append to `/tmp/campuscast_decisions.md`:

```text
Google Cloud project: CampusCast AI
OAuth Client Name (n8n): CampusCast AI n8n
Redirect URI: http://localhost:5678/rest/oauth2-credential/callback
n8n credential name: Google Sheets — CampusCast
```

---

## Task 11: Create the Google Sheet

**Files:** none in-repo.

- [ ] **Step 1: Create spreadsheet**

Browse to `https://sheets.new`. Rename the spreadsheet `CampusCast AI`.

- [ ] **Step 2: Rename Sheet1 to `events` and add headers**

- Right-click Sheet1 → Rename → `events`.
- In row 1, paste (tab-separated):
  ```
  date	time	event_name	location	audience	priority
  ```

- [ ] **Step 3: Populate events with sample data**

Copy rows 2-4 from `examples/sample-campus-events.csv`. Paste into row 2 of `events`:

```text
2026-04-23	19:00	AI Study Group	Lab 3	Computer Science students	medium
2026-04-23	21:00	Project Deadline Reminder	Online	All students	high
2026-04-24	18:30	Automation Project Checkpoint	Online	AI Factory students	high
```

**Important:** change the earliest date to *today* (2026-04-22) for your first test run, so the "filter to today" logic produces at least one event:

Insert a new row 2:
```text
2026-04-22	14:00	Workshop: Prototype Demo	Building A	All students	high
```

- [ ] **Step 4: Create `results` tab**

Bottom of spreadsheet → `+` → rename new sheet to `results`.
In row 1 paste:

```
timestamp	city	temperature	humidity	rain	precipitation	wind_speed	events_used	llm_response	audio_file	status	error_message
```

- [ ] **Step 5: Copy the spreadsheet ID**

From the URL: `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`. Copy the ID.

Append to `/tmp/campuscast_decisions.md`:
```text
Google Sheet ID: <SPREADSHEET_ID>
URL: https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
```

---

## Task 12: Build the n8n workflow

Build node-by-node in the n8n UI, then export to JSON.

**Files:**
- Create: `workflow/campuscast.workflow.json` (via n8n export at the end)

- [ ] **Step 1: Create workflow**

In n8n editor, click **New Workflow**. Name it `CampusCast AI` (top left).

- [ ] **Step 2: Node 1 — Manual Trigger**

Already present (the "When clicking 'Execute Workflow'" node).

- [ ] **Step 3: Node 2 — HTTP Request: Open-Meteo**

Click `+` after the trigger → **HTTP Request**.
- Method: `GET`
- URL:
  ```
  https://api.open-meteo.com/v1/forecast?latitude=-25.4284&longitude=-49.2733&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m&timezone=America/Sao_Paulo
  ```
- Leave everything else default.
- **Settings tab → On Error → "Continue (using error output)".**
- Rename the node: `Weather`.

Click **Execute node** once. Expected: JSON output with `current.temperature_2m`.

- [ ] **Step 4: Node 3 — Google Sheets: Read events**

Click `+` → **Google Sheets**.
- Credential: `Google Sheets — CampusCast`.
- Resource: `Sheet Within Document`.
- Operation: `Get Row(s) in Sheet`.
- Document: pick the `CampusCast AI` spreadsheet.
- Sheet: `events`.
- Options → Range: leave default (reads all).
- **Settings tab → On Error → "Continue (using error output)".**
- Rename the node: `Events Read`.

Click **Execute node**. Expected: array of items, one per event row.

- [ ] **Step 5: Node 4 — Code: Build payload + prompt**

Click `+` → **Code**. Language: JavaScript.

Paste:

```javascript
// Inputs: items coming from "Events Read" (one per event row).
// The "Weather" node output is reachable via $("Weather").first().json.

const events = items;
const weather = $("Weather").first().json.current;

// Portuguese phrase for the Open-Meteo / WMO weather code.
const WMO = {
  0: "céu limpo",
  1: "parcialmente nublado", 2: "parcialmente nublado",
  3: "céu encoberto",
  45: "neblina", 48: "neblina",
  51: "garoa", 53: "garoa", 55: "garoa",
  61: "chuva fraca", 63: "chuva moderada", 65: "chuva forte",
  66: "chuva congelante", 67: "chuva congelante",
  71: "neve", 73: "neve", 75: "neve",
  80: "pancadas de chuva", 81: "pancadas de chuva", 82: "pancadas de chuva",
  95: "trovoada", 96: "trovoada", 99: "trovoada"
};
const weather_phrase = WMO[weather.weather_code] || "condição indefinida";

// Today in America/Sao_Paulo.
const todaySP = new Date().toLocaleDateString("en-CA", { timeZone: "America/Sao_Paulo" });

// Filter events to today. Each row has { date, time, event_name, location, audience, priority }.
const todayEvents = events
  .map(i => i.json)
  .filter(ev => String(ev.date) === todaySP);

const events_list = todayEvents.length === 0
  ? "Nenhum evento registrado hoje."
  : todayEvents
      .map(e => `- ${e.date} ${e.time} ${e.event_name} (${e.location})`)
      .join("\n");

const payload = {
  city: "Curitiba",
  weather_time: weather.time,
  temperature: weather.temperature_2m,
  humidity: weather.relative_humidity_2m,
  rain: weather.rain,
  precipitation: weather.precipitation,
  wind_speed: weather.wind_speed_10m,
  weather_phrase,
  events_list
};

const prompt = `Você é o CampusCast AI, um assistente que cria boletins curtos diários para estudantes.

Dados do clima:
- Cidade: ${payload.city}
- Condição atual: ${payload.weather_phrase} (código ${weather.weather_code})
- Temperatura: ${payload.temperature} °C
- Umidade: ${payload.humidity}%
- Chuva: ${payload.rain} mm
- Precipitação: ${payload.precipitation} mm
- Vento: ${payload.wind_speed} km/h
- Horário: ${payload.weather_time}

Eventos do campus hoje:
${payload.events_list}

Crie um boletim com:
1. Uma saudação curta.
2. Um resumo do clima em uma ou duas frases.
3. Conselhos práticos para estudantes que vão ao campus.
4. Um lembrete sobre eventos relevantes, se houver.
5. Um alerta de risco apenas se necessário (chuva forte, trovoada, etc.).

Regras:
- Máximo de 120 palavras.
- Use português claro e natural do Brasil.
- Não invente eventos.
- Se não há eventos, diga que não há eventos registrados hoje.
- Deixe o texto adequado para leitura em áudio (sem listas, sem emojis, sem marcações).`;

return [{ json: { payload, prompt } }];
```

Rename the node: `Build Prompt`.

Click **Execute node**. Expected: one output item with `payload` and `prompt` keys.

- [ ] **Step 6: Node 5 — HTTP Request: Ollama**

Click `+` → **HTTP Request**.
- Method: `POST`
- URL: `http://localhost:11434/api/generate`
- Send Body: yes, `JSON`.
- Body:
  ```json
  {
    "model": "llama3.1:8b",
    "prompt": "={{$json.prompt}}",
    "stream": false
  }
  ```
- **Settings tab → On Error → "Continue (using error output)"**.
- Timeout: 120000 ms.
- Rename the node: `Ollama Generate`.

Click **Execute node**. Expected: JSON with `response` field containing Portuguese text.

- [ ] **Step 7: Node 6 — Code: Validate word count**

Click `+` → **Code** (JavaScript).

Paste:

```javascript
const response = $json.response || "";
const words = response.trim().split(/\s+/).filter(Boolean);
const n = words.length;

if (n < 50 || n > 200) {
  throw new Error(`ollama_bad_output: words=${n}`);
}

// Pass the bulletin forward, along with the payload that led to it.
const payload = $("Build Prompt").first().json.payload;
return [{ json: { payload, bulletin: response.trim() } }];
```

- **Settings tab → On Error → "Continue (using error output)"**.
- Rename the node: `Validate Bulletin`.

Click **Execute node**. Expected: one item with `payload` and `bulletin`.

- [ ] **Step 8: Node 7 — HTTP Request: Kokoro**

Click `+` → **HTTP Request**.
- Method: `POST`
- URL: `http://localhost:8800/tts`
- Send Body: yes, `JSON`.
- Body:
  ```json
  {
    "text": "={{$json.bulletin}}"
  }
  ```
- **Settings tab → On Error → "Continue (using error output)"**.
- Timeout: 120000 ms.
- Rename the node: `Kokoro TTS`.

Click **Execute node**. Expected: `{audio_file, duration_seconds}`.

- [ ] **Step 9: Node 8 — Set: Build success row**

Click `+` → **Set** (Edit Fields).

Mode: `Manual Mapping`. Add string fields:

- `timestamp`: `={{ $now.toISO() }}`
- `city`: `={{ $("Build Prompt").first().json.payload.city }}`
- `temperature`: `={{ $("Build Prompt").first().json.payload.temperature }}`
- `humidity`: `={{ $("Build Prompt").first().json.payload.humidity }}`
- `rain`: `={{ $("Build Prompt").first().json.payload.rain }}`
- `precipitation`: `={{ $("Build Prompt").first().json.payload.precipitation }}`
- `wind_speed`: `={{ $("Build Prompt").first().json.payload.wind_speed }}`
- `events_used`: `={{ $("Build Prompt").first().json.payload.events_list }}`
- `llm_response`: `={{ $("Validate Bulletin").first().json.bulletin }}`
- `audio_file`: `={{ $json.audio_file }}`
- `status`: `ok`
- `error_message`: `` (empty string)

Rename the node: `Success Row`.

- [ ] **Step 10: Node 9 — Google Sheets: Append results**

Click `+` → **Google Sheets**.
- Credential: `Google Sheets — CampusCast`.
- Resource: `Sheet Within Document`.
- Operation: `Append Row in Sheet`.
- Document: `CampusCast AI`.
- Sheet: `results`.
- Mapping Column Mode: `Map Automatically` (uses field names from Success Row).
- Rename the node: `Results Append`.

- [ ] **Step 11: Error branch — Set: Build error row**

Click `+` on the **red error output** of `Weather`, `Events Read`, `Ollama Generate`, `Validate Bulletin`, or `Kokoro TTS` → **Set** (Edit Fields).

Manual Mapping, add:

- `timestamp`: `={{ $now.toISO() }}`
- `city`: `Curitiba`
- `temperature`: `={{ $("Weather").first()?.json?.current?.temperature_2m || "" }}`
- `humidity`: `={{ $("Weather").first()?.json?.current?.relative_humidity_2m || "" }}`
- `rain`: `={{ $("Weather").first()?.json?.current?.rain || "" }}`
- `precipitation`: `={{ $("Weather").first()?.json?.current?.precipitation || "" }}`
- `wind_speed`: `={{ $("Weather").first()?.json?.current?.wind_speed_10m || "" }}`
- `events_used`: `={{ $("Build Prompt").first()?.json?.payload?.events_list || "" }}`
- `llm_response`: `={{ $("Validate Bulletin").first()?.json?.bulletin || $("Ollama Generate").first()?.json?.response || "" }}`
- `audio_file`: ``
- `status`: `error`
- `error_message`: `={{ $json.error?.message || JSON.stringify($json) }}`

Rename the node: `Error Row`.

Connect the red error outputs of all five eligible nodes to this single `Error Row` node.

- [ ] **Step 12: Error branch — Google Sheets: Append error row**

Click `+` after `Error Row` → **Google Sheets**.
Same config as `Results Append` (Step 10). Rename: `Error Row Append`.

- [ ] **Step 13: Save the workflow**

Top-right → **Save**.

- [ ] **Step 14: Export workflow JSON**

Top-right menu → **Download** (exports as JSON).
Move the downloaded file to `/home/oness24/Desktop/AI/pucpr/campuscast-ai/workflow/campuscast.workflow.json`.

- [ ] **Step 15: Commit**

```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
git add workflow/campuscast.workflow.json
git commit -m "feat(workflow): add n8n CampusCast AI Etapa 1 workflow"
```

---

## Task 13: Execute workflow — happy path

- [ ] **Step 1: Confirm all services are running**

Terminal 1 (Kokoro):
```bash
curl -s http://localhost:8800/health
```
Expected: `{"status":"ok"}`.

Terminal 2 (n8n): should show the editor.
Terminal 3 (Ollama is systemd):
```bash
curl -s http://localhost:11434/api/tags | grep llama3.1
```

- [ ] **Step 2: Run full smoke suite one more time**

```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
source .venv/bin/activate
python tools/smoke.py
```
Expected: all three PASS.

- [ ] **Step 3: Execute workflow**

In n8n editor → open `CampusCast AI` workflow → click **Execute Workflow** (top right, green play button).

Expected: all 9 success-path nodes turn green within ~60 seconds. No red nodes.

- [ ] **Step 4: Screenshot the executed workflow**

Save screenshot to `docs/evidence/01-workflow-success.png` (create folder if needed).

```bash
mkdir -p docs/evidence
```

- [ ] **Step 5: Verify audio file was created**

```bash
ls -la audio/
```

Expected: a new WAV file with today's timestamp, >50 KB.

Play it:
```bash
aplay audio/<the-new-file>.wav
```

Expected: intelligible Portuguese bulletin about Curitiba weather + events.

- [ ] **Step 6: Verify Google Sheets `results` row**

Open the spreadsheet → `results` tab. Expected: a new row with 12 columns populated, `status=ok`, `error_message=""`.

Screenshot to `docs/evidence/02-sheets-success-row.png`.

- [ ] **Step 7: Commit evidence screenshots**

```bash
git add docs/evidence/01-workflow-success.png docs/evidence/02-sheets-success-row.png
git commit -m "docs: add Etapa 1 success-path evidence screenshots"
```

---

## Task 14: Execute workflow — failure path

Proves the error branch writes an error row.

- [ ] **Step 1: Stop the Kokoro server**

In the Kokoro terminal → press `Ctrl+C`. Verify:
```bash
curl -s http://localhost:8800/health
```
Expected: connection refused.

- [ ] **Step 2: Execute workflow in n8n**

Click **Execute Workflow**. Expected: the `Kokoro TTS` node turns red, flow continues down error branch, `Error Row` and `Error Row Append` turn green.

- [ ] **Step 3: Screenshot the failure execution**

Save to `docs/evidence/03-workflow-failure.png`.

- [ ] **Step 4: Verify Google Sheets error row**

`results` tab should now have a second new row with `status=error`, `error_message` containing something like `kokoro_down: ...`, `audio_file=""`, and the other fields populated where possible.

Screenshot to `docs/evidence/04-sheets-error-row.png`.

- [ ] **Step 5: Restart Kokoro server**

In the Kokoro terminal:
```bash
uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800
```

- [ ] **Step 6: Commit evidence**

```bash
git add docs/evidence/03-workflow-failure.png docs/evidence/04-sheets-error-row.png
git commit -m "docs: add Etapa 1 failure-path evidence screenshots"
```

---

## Task 15: Write evidence doc (`docs/07-setup-evidence.md`)

**Files:**
- Create: `docs/07-setup-evidence.md`

- [ ] **Step 1: Capture `smoke.py` output**

Run:
```bash
python tools/smoke.py > /tmp/smoke-output.txt 2>&1
cat /tmp/smoke-output.txt
```

Copy the output — you'll paste it into the evidence doc in Step 3.

- [ ] **Step 2: Capture Ollama direct-call evidence**

Run:
```bash
ollama run llama3.1:8b "Em uma frase, fale sobre o clima de Curitiba." > /tmp/ollama-direct.txt
cat /tmp/ollama-direct.txt
```

- [ ] **Step 3: Write the evidence doc**

Write to `/home/oness24/Desktop/AI/pucpr/campuscast-ai/docs/07-setup-evidence.md`:

```markdown
# ID 2.1 — Setup Evidence

This document collects the evidence required by requirement ID 2.1:
HTTP calls in Python, n8n workflows, Ollama + Kokoro running locally.

## 1. Open-Meteo public API (HTTP in Python)

Sample response captured via `python tools/smoke.py --only weather`:

```text
<paste output from /tmp/smoke-output.txt — the weather line plus a sample curl response>
```

Direct curl sample:

```bash
$ curl -s "https://api.open-meteo.com/v1/forecast?latitude=-25.4284&longitude=-49.2733&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m&timezone=America/Sao_Paulo"
<paste JSON response>
```

## 2. Ollama (local LLM)

Version:

```text
$ ollama --version
ollama version is 0.17.0
```

Installed models:

```text
$ ollama list
NAME                 ID              SIZE      MODIFIED
llama3.1:8b          46e0c10c039e    4.9 GB    <when>
```

Direct model test:

```text
$ ollama run llama3.1:8b "Em uma frase, fale sobre o clima de Curitiba."
<paste response from /tmp/ollama-direct.txt>
```

HTTP API test via `python tools/smoke.py --only ollama`:

```text
<paste the ollama PASS line>
```

## 3. Kokoro (local TTS)

TTS engine chosen: `<Kokoro | Piper>` (see decision log).
Voice: `<pf_dora | pt_BR-faber-medium>`.

Server `/health` check:

```bash
$ curl -s http://localhost:8800/health
{"status":"ok"}
```

End-to-end `/tts` test via `python tools/smoke.py --only kokoro`:

```text
<paste the kokoro PASS line>
```

Generated audio file: `audio/<timestamp>.wav` (attached to delivery folder).

## 4. n8n (automation)

Version: installed via `npx n8n` — ![screenshot](evidence/01-workflow-success.png)
Editor: `http://localhost:5678`.

Workflow JSON: `workflow/campuscast.workflow.json`.

Full execution evidence:

- Success run: `docs/evidence/01-workflow-success.png`, `docs/evidence/02-sheets-success-row.png`
- Failure run (Kokoro stopped): `docs/evidence/03-workflow-failure.png`, `docs/evidence/04-sheets-error-row.png`

## 5. Google Sheets

Spreadsheet name: `CampusCast AI`.
Tabs: `events`, `results` (schemas match `examples/sample-campus-events.csv` and `examples/google-sheets-columns.csv`).

Credential name in n8n: `Google Sheets — CampusCast`.

## 6. Decisions captured during setup

(Copied from `/tmp/campuscast_decisions.md`.)

```text
<paste your scratch notes>
```
```

- [ ] **Step 4: Fill in the placeholders**

Replace each `<paste ...>` placeholder with the actual captured output. Leave nothing in angle brackets.

- [ ] **Step 5: Verify the doc is complete**

Open the doc and confirm:
- §1 has real JSON
- §2 has the Ollama PASS line
- §3 has the Kokoro PASS line and the chosen engine
- §4 links to all four screenshots that exist on disk
- §6 has non-empty scratch notes

- [ ] **Step 6: Commit**

```bash
git add docs/07-setup-evidence.md
git commit -m "docs: add ID 2.1 setup evidence"
```

---

## Post-implementation checklist

Once all 15 tasks are complete, confirm:

- [ ] `python tools/smoke.py` → all green, exit 0
- [ ] `npx n8n` runs cleanly on :5678
- [ ] `uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800` runs cleanly
- [ ] `workflow/campuscast.workflow.json` committed and re-importable
- [ ] Google Sheet has at least one `status=ok` row and one `status=error` row
- [ ] `docs/07-setup-evidence.md` has no placeholder content
- [ ] All commits pushed (if/when a remote is configured — `git remote add origin ...`)
- [ ] `git log --oneline` shows a clean linear history, each commit focused

**Deliverables mapped back to requirements:**

| Deliverable | Location |
|---|---|
| Diagnosis | `docs/01-diagnosis.md` |
| Project Canvas | `docs/02-project-canvas.md` |
| Setup evidence (ID 2.1) | `docs/07-setup-evidence.md` + `docs/evidence/` |
| Implementation plan | This file; original plan in `docs/04-implementation-plan.md` |
| n8n workflow JSON | `workflow/campuscast.workflow.json` |
| LLM-generated bulletin | Sheets `results` tab, `llm_response` column |
| TTS audio file | `audio/<timestamp>.wav` referenced from `audio_file` column |
| Testing checklist | `docs/05-testing-checklist.md` |
| Presentation script | `docs/06-presentation-script.md` |
