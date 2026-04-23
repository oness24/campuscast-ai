# ID 2.1 — Setup Evidence + Live Demo Runbook

This document captures the evidence for requirement **ID 2.1** (HTTP calls in Python, n8n workflow, Ollama + Kokoro running locally) and the final pipeline verification.

Date of capture: **2026-04-22**
n8n version: **2.13.4 (Self-Hosted)**
Machine: Linux (Pop!_OS), 31 GB RAM, 16 CPU cores, NVIDIA GPU
Python: 3.12.3 in `.venv/`

---

## 1. Open-Meteo public API (HTTP in Python)

Sample Python probe result — `python tools/smoke.py --only weather`:

```text
[PASS] weather: Curitiba temperature_2m=15.7 C
```

Sample API response (first 400 chars):

```json
{"latitude":-25.375,"longitude":-49.25,"generationtime_ms":0.113,"utc_offset_seconds":-10800,"timezone":"America/Sao_Paulo","timezone_abbreviation":"GMT-3","elevation":920.0,"current_units":{"time":"iso8601","interval":"seconds","temperature_2m":"°C","relative_humidity_2m":"%","precipitation":"mm","rain":"mm","weather_code":"wmo code","wind_speed_10m":"km/h"},"current":{ ... }}
```

HTTP call location: `tools/smoke.py` → `probe_weather()`, using the `requests` library (satisfies the rubric's "chamadas HTTP em Python" requirement).

---

## 2. Ollama (local LLM)

Version: `ollama version is 0.17.0`
Systemd service: active
Installed model: `llama3.1:8b` (4.9 GB, Q4_K_M quantization)

Direct CLI test:

```text
$ ollama run llama3.1:8b "Em uma frase, fale sobre o clima de Curitiba."
O clima da cidade é subtropical úmido e é influenciado pela proximidade com
a Serra do Mar, trazendo chuvas intensas na primavera. Durante o ano, ocorrem
também temperaturas frias, especialmente em julho e agosto, tornando o
inverno um dos períodos mais frios da cidade.
```

HTTP probe via `python tools/smoke.py --only ollama`:

```text
[PASS] ollama: 9 chars — 'Brasília.'
```

---

## 3. Kokoro (local TTS)

Engine: Kokoro 0.9.2 (Python package), PyTorch 2.11.0 with CUDA.
Voice: `pf_dora` (Brazilian Portuguese), `lang_code="p"`.

Pt-BR voice quality smoke test — synthesized 6.47s of audio from a pt-BR sample sentence. Result: intelligible pt-BR, no fallback to Piper needed.

HTTP probe via `python tools/smoke.py --only kokoro`:

```text
[PASS] kokoro: audio/2026-04-22T21-45-47.wav (138044 bytes, 2.88s)
```

Server: FastAPI wrapper at `tools/kokoro_server.py`, running at `http://127.0.0.1:8800`. Endpoints:

- `GET /health` → `{"status":"ok"}`
- `POST /tts` with `{"text":"..."}` → `{"audio_file":"audio/<iso>.wav","duration_seconds":<n>}`

---

## 4. n8n (automation)

Editor: `http://localhost:5678`
Workflow: **CampusCast AI MVP** (ID `OPL0o46PElOTFv7M`, project `Contego NOC`)
Workflow JSON: `workflow/campuscast-mvp.workflow.json` (committed)

Pipeline (8 nodes, linear):

```text
Manual Trigger
    → Weather (HTTP GET Open-Meteo)
    → Events Read (Google Sheets service-account read)
    → Build Prompt (Code, JS — WMO mapping + prompt build)
    → Ollama Generate (HTTP POST :11434/api/generate)
    → Kokoro TTS (HTTP POST :8800/tts)
    → Build Success Row (Set — 12 result fields)
    → Results Append (Google Sheets append to results tab)
```

The workflow was deployed to n8n via the REST API (see `tools/deploy_to_n8n.py`) and via an authenticated `PATCH /rest/workflows/{id}` session.

---

## 5. Google Sheets

Spreadsheet: `CampusCast AI`
ID: `1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk`
URL: https://docs.google.com/spreadsheets/d/1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk/edit

Tabs:

- **`events`** (6 columns: `date, time, event_name, location, audience, priority`) — seeded with 2 sample events for today via the Google Sheets API.
- **`results`** (12 columns: `timestamp, city, temperature, humidity, rain, precipitation, wind_speed, events_used, llm_response, audio_file, status, error_message`).

Auth: Google **Service Account** (`campuscast-n8n@campuscast-n8n.iam.gserviceaccount.com`), shared with the spreadsheet as Editor. Credentials stored locally at `credentials/campuscast-n8n.json` (git-ignored).

n8n credential name: `Google Sheets — CampusCast` (type `googleApi`, id `xsjRaVzdAvkp6C3F`), created via REST.

---

## 6. End-to-End Run — Verified Output

A single Execute Workflow run produced:

**Generated bulletin (excerpt from `llm_response`):**

> "Olá, estudantes! Hoje à noite, Curitiba tem um céu limpo com temperaturas amenas de 15.9 graus Celsius e alta umidade..."

**Generated audio file:** `audio/2026-04-22T21-42-36.wav` (1.98 MB, ~41 s).

**Row appended to `results` tab:**

| timestamp | city | temperature | humidity | rain | wind_speed | status |
|---|---|---|---|---|---|---|
| 2026-04-22T21:42:36.424-03:00 | Curitiba | 15.9 | 93 | 0 | 4.3 | ok |

All 8 nodes in the workflow went green in a single execution.

---

## 7. Git History (as of this evidence)

```text
ae6d70f feat(workflow): add Google Sheets read/append for full pipeline (8 nodes)
0aab9b6 fix(workflow): use 127.0.0.1 instead of localhost (Ollama/Kokoro IPv4-only)
3ff44d4 feat(workflow): extend MVP with Kokoro TTS node (5 nodes total)
24045bf feat(smoke): add Python HTTP probe for Kokoro TTS server
48589e6 feat(kokoro): add FastAPI server wrapping Kokoro TTS on :8800
2e09850 feat(tools): add Python deployer for n8n workflows (mirrors zabbix pattern)
014dab9 feat(workflow): add 4-node MVP workflow for import (Trigger → Weather → Prompt → Ollama)
20b11f3 feat(smoke): add Python HTTP probe for local Ollama llama3.1:8b
3e78664 feat(smoke): add Python HTTP probe for Open-Meteo weather
e72ad0b chore: import existing project docs and examples
bbd90ad chore: initialize project scaffolding
```

11 commits on `master`.

---

## 8. Live Demo Runbook (2–4 minutes)

Use this as the script for a live demonstration. Everything below should work with a single machine, local services already running.

### Pre-flight checklist (do once before the demo starts)

Open **three terminals** side by side:

- **Terminal A** — smoke tests terminal (empty, ready to run commands)
- **Terminal B** — Kokoro server log (`uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800` must be running; leave the log visible)
- **Terminal C** — audio playback (empty)

Open **two browser tabs**:

- **Tab 1** — n8n editor at http://localhost:5678/workflow/OPL0o46PElOTFv7M
- **Tab 2** — Google Sheet at https://docs.google.com/spreadsheets/d/1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk/edit (on the `results` tab so the audience can see new rows appear)

### Demo steps (talk track in italics)

1. **Prove the three upstream services are reachable** (~20 s)
   - In Terminal A run:
     ```bash
     cd ~/Desktop/AI/pucpr/campuscast-ai
     source .venv/bin/activate
     python tools/smoke.py
     ```
   - *"These three Python HTTP probes confirm Open-Meteo, Ollama, and Kokoro are all responding. All green."*

2. **Show the n8n workflow on screen** (~15 s)
   - Switch to Tab 1. Zoom so all 8 nodes are visible.
   - *"The pipeline is: manual trigger, weather API, Google Sheets read for campus events, a code node that builds the LLM prompt, Ollama generating a Portuguese bulletin, Kokoro turning it into audio, and Google Sheets appending the result."*

3. **Show today's events in the sheet** (~10 s)
   - Switch to Tab 2, `events` tab briefly.
   - *"Two events are registered for today — the workflow will include them in the bulletin."*

4. **Run the pipeline live** (~45 s)
   - Back to Tab 1. Click **Execute workflow**.
   - Narrate as each node turns green: *"Weather fetched. Events read. Prompt built. Ollama is thinking... Bulletin generated. Kokoro synthesizing audio... Row appended."*
   - When all 8 are green: *"Eight nodes, all green."*

5. **Show the new row in the Sheet** (~20 s)
   - Switch to Tab 2 → `results` tab. A new row should appear (hit the refresh icon if needed).
   - *"This row has the timestamp, weather values, the events list the LLM saw, the full Portuguese bulletin, the path to the generated audio, and status=ok."*
   - Click on the `llm_response` cell so the audience can read the bulletin.

6. **Play the audio** (~20–40 s)
   - In Terminal C:
     ```bash
     ls -t ~/Desktop/AI/pucpr/campuscast-ai/audio/*.wav | head -1 | xargs -I {} aplay {}
     ```
   - *"This is the exact audio file referenced in the row we just saw."*
   - Pause so the audience hears the full pt-BR bulletin.

7. **Wrap** (~10 s)
   - *"Input → process → output: public API data and a spreadsheet, combined by n8n, interpreted by a local LLM, rendered to audio by local TTS, and recorded in Google Sheets — all running on this single machine with zero external paid services beyond the free Open-Meteo API."*

### If something goes wrong mid-demo

| Failure | Quick recovery |
|---|---|
| Kokoro node red — "ECONNREFUSED" | Terminal B probably died. Restart: `cd ~/Desktop/AI/pucpr/campuscast-ai && source .venv/bin/activate && uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800` |
| Ollama node red — timeout | GPU might be busy. Wait, or retry. `llama3.1:8b` can take 10–30 s first call after idle. |
| Google Sheets node red | Usually auth — reload the n8n page, credential stays valid. |
| Sheet row doesn't appear | Make sure you're on the `results` tab, not `events`; click the browser reload. |

---

## 9. What's stored where

| Artifact | Location |
|---|---|
| Design spec | `docs/superpowers/specs/2026-04-22-campuscast-ai-etapa1-design.md` |
| Implementation plan | `docs/superpowers/plans/2026-04-22-campuscast-ai-etapa1.md` |
| Existing docs (diagnosis, canvas, checklists, presentation) | `docs/01-...md` through `docs/06-...md` |
| n8n workflow JSON | `workflow/campuscast-mvp.workflow.json` |
| Smoke tests (Python) | `tools/smoke.py`, `tools/smoke_weather.sh`, `tools/smoke_ollama.sh`, `tools/smoke_kokoro.sh` |
| Kokoro TTS server | `tools/kokoro_server.py` |
| n8n deploy helper | `tools/deploy_to_n8n.py` |
| Generated audio | `audio/*.wav` (git-ignored) |
| Service account JSON | `credentials/campuscast-n8n.json` (git-ignored) |
| This evidence | `docs/07-setup-evidence.md` |
