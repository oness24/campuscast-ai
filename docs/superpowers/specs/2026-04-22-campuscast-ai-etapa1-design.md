# CampusCast AI — Etapa 1 Design Spec

**Date:** 2026-04-22
**Scope:** Etapa 1 prototype only (manual trigger, single end-to-end run with evidence). Etapa 2 items (scheduled runs, multichannel delivery, alerts) are explicitly out of scope.

## 1. Summary

CampusCast AI generates a short daily Portuguese audio bulletin for PUCPR students by orchestrating four components through a single n8n workflow:

```text
Open-Meteo API  +  Google Sheets (events)
       │                 │
       └────────┬────────┘
                ▼
           n8n workflow
                │
        ┌───────┼────────┐
        ▼       ▼        ▼
    Ollama   Kokoro   Google Sheets
    (LLM)   (TTS)     (results)
```

The n8n workflow is itself the primary deliverable artifact (imported from committed JSON) because the project's grading rubric emphasizes visible pipeline orchestration (input → process → output).

## 2. Requirements coverage

| Requirement | Artifact |
|---|---|
| ID 1.1 — Diagnóstico | `docs/01-diagnosis.md` (already written) |
| ID 1.2 — Canvas | `docs/02-project-canvas.md` (already written) |
| ID 2.1 — Ambiente (HTTP calls em Python, n8n, Ollama/Kokoro local) | Ollama installed; `npx n8n` runtime; Kokoro FastAPI wrapper; `tools/smoke.py` (Python + `requests`) for HTTP compliance; `docs/07-setup-evidence.md` for evidence capture |
| ID 2.2 — Protótipo funcional | `workflow/campuscast.workflow.json` (Open-Meteo → Ollama → Kokoro → Google Sheets) |
| Aprendizagem-chave (input→process→output, API integration) | Linear 9-node (+ 2 shared error-branch nodes) n8n workflow; `docs/06-presentation-script.md` already written |

## 3. Architecture

Three long-lived localhost services + one on-demand workflow on a single Linux machine (Ubuntu/Pop!_OS, 31 GB RAM, 16 cores, NVIDIA GPU):

```text
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  n8n (npx n8n)      │     │  Ollama daemon      │     │  Kokoro FastAPI     │
│  localhost:5678     │───▶ │  localhost:11434    │     │  localhost:8800     │
│  (orchestrator)     │     │  (llama3.1:8b)      │     │  (TTS wrapper)      │
└─────────┬───────────┘     └─────────────────────┘     └──────────▲──────────┘
          │                                                         │
          ├─▶ api.open-meteo.com   (public HTTPS, no auth)           │
          ├─▶ Google Sheets        (OAuth2, events + results tabs)   │
          └─▶ localhost:8800/tts   ───────────────────────────────────┘
                                      (writes WAV to ./audio/YYYY-MM-DD.wav)
```

### Runtime decisions

- **n8n**: `npx n8n` (not Docker, not the cloned source tree). Data persists to `~/.n8n/`. The `n8n/` source clone in the repo is unused and should be removed or ignored.
- **Ollama**: already installed (v0.17.0), systemd-active. Model `llama3.1:8b` (4.9 GB) pulled.
- **Kokoro**: run as a small FastAPI server we author at `tools/kokoro_server.py`.
- **Event/result storage**: Google Sheets, both tabs of one spreadsheet, via n8n's native Google Sheets node with an OAuth2 credential the user creates once.

## 4. File layout

```text
campuscast-ai/
├── README.md                            (existing)
├── docs/
│   ├── 01-diagnosis.md                  (existing)
│   ├── 02-project-canvas.md             (existing)
│   ├── 03-setup-checklist.md            (existing)
│   ├── 04-implementation-plan.md        (existing)
│   ├── 05-testing-checklist.md          (existing)
│   ├── 06-presentation-script.md        (existing)
│   ├── 07-setup-evidence.md             (NEW — ID 2.1 evidence capture)
│   └── superpowers/specs/               (NEW)
│       └── 2026-04-22-campuscast-ai-etapa1-design.md   (this file)
├── examples/                            (existing; kept as schema/reference)
├── tools/                               (NEW)
│   ├── kokoro_server.py                 (FastAPI TTS wrapper)
│   ├── smoke.py                         (Python HTTP probes — ID 2.1)
│   ├── smoke_weather.sh                 (bash wrapper)
│   ├── smoke_ollama.sh                  (bash wrapper)
│   ├── smoke_kokoro.sh                  (bash wrapper)
│   └── requirements.txt                 (requests, fastapi, uvicorn, kokoro, soundfile)
├── workflow/                            (NEW)
│   └── campuscast.workflow.json         (n8n workflow export)
├── audio/                               (NEW, git-ignored)
└── .gitignore                           (NEW, entries for audio/ and local state)
```

The cloned `n8n/` source folder is not needed and can be deleted.

## 5. Components

Each unit has a single responsibility, a narrow interface, and minimal dependencies.

### 5.1 n8n workflow (`workflow/campuscast.workflow.json`)

- **Does:** orchestrates the pipeline, single linear chain, no sub-workflows.
- **Nodes (9 success path + 2 shared error-branch nodes = 11 total):**

  1. `Manual Trigger`
  2. `HTTP Request` — GET Open-Meteo
  3. `Google Sheets` — read `events` tab
  4. `Code` node (JavaScript) — filter events to today (America/Sao_Paulo), map `weather_code` to Portuguese phrase, build `payload` and `prompt` fields
  5. `HTTP Request` — POST `localhost:11434/api/generate` (model: `llama3.1:8b`)
  6. `Code` node — validate word count (50 ≤ words ≤ 200); route to error branch if invalid (via n8n's "On Error: Continue (using error output)" mode with `throw new Error("ollama_bad_output: words=N")`)
  7. `HTTP Request` — POST `localhost:8800/tts`
  8. `Set` node — assemble 12-column results row
  9. `Google Sheets` — append to `results` tab

  Error branch (shared by nodes 2, 3, 5, 6, 7): `Set` (build error row) → `Google Sheets` append with `status=error`, `error_message` populated.

  Failures of node 4 (deterministic prompt-building JS) or node 9 (final Sheets append) are **not** routed to the error branch — they halt execution with an n8n-level failure. This is acceptable because node 4 failing indicates a code bug (not runtime), and node 9 failing means the logging target itself is broken.

- **Interface:** "Execute Workflow" button in n8n editor. No CLI.
- **Depends on:** localhost:11434 (Ollama), localhost:8800 (Kokoro), Google OAuth2 credential.

### 5.2 `tools/kokoro_server.py` (FastAPI)

- **Does:** receives `POST /tts {text, voice?}`, synthesizes audio, writes WAV to `./audio/<ISO-timestamp>.wav`, returns `{audio_file, duration_seconds}`. Also `GET /health` for smoke tests.
- **Interface:** HTTP, two endpoints. Synchronous — no queue, no streaming.
- **Depends on:** `kokoro`, `soundfile`, `fastapi`, `uvicorn`. Python 3.12 (already installed).
- **Voice:** Brazilian Portuguese voice (e.g. `pf_dora`). Must be verified during smoke testing; if Kokoro's pt-BR quality is inadequate, the fallback plan is Piper TTS (`pt_BR-faber-medium`). The plan does not adopt Piper unless Kokoro smoke testing fails.

### 5.3 Ollama daemon (existing)

- **Does:** hosts `llama3.1:8b`, serves text completions.
- **Interface:** HTTP `POST /api/generate` on localhost:11434.
- **Depends on:** already-installed systemd service; GPU drivers present.

### 5.4 Google Sheets spreadsheet

One spreadsheet, two tabs, created manually once in the user's Google Drive:

- `events` tab — columns match `examples/sample-campus-events.csv`:
  `date, time, event_name, location, audience, priority`
- `results` tab — columns match `examples/google-sheets-columns.csv`:
  `timestamp, city, temperature, humidity, rain, precipitation, wind_speed, events_used, llm_response, audio_file, status, error_message`

OAuth2 credential bound in n8n Credentials UI once.

### 5.5 `tools/smoke.py` + bash wrappers

- **Does:** three independent HTTP probes — weather, Ollama, Kokoro. One CLI flag selects a single probe (`--only weather|ollama|kokoro`); default runs all three.
- **Output:** per-probe status line (green/red), JSON response summary, exit code 0 if all green else 1.
- **Interface:** `python tools/smoke.py [--only NAME]`; bash scripts are thin wrappers.
- **Depends on:** `requests` (listed in `tools/requirements.txt`).

## 6. Data flow

One workflow execution:

```text
[1] Manual Trigger
      ▼
[2] GET api.open-meteo.com/v1/forecast
      ?latitude=-25.4284&longitude=-49.2733
      &current=temperature_2m,relative_humidity_2m,precipitation,rain,
              weather_code,wind_speed_10m
      &timezone=America/Sao_Paulo
      ▼
    { "current": { "time": "...", "temperature_2m": 19.4,
                   "relative_humidity_2m": 72, "precipitation": 0.0,
                   "rain": 0.0, "weather_code": 3, "wind_speed_10m": 11.2 } }
      ▼
[3] Google Sheets → events tab (read all rows)
      ▼
    [ { date, time, event_name, location, audience, priority }, ... ]
      ▼
[4] Code node — filter to today (America/Sao_Paulo), map weather_code,
    build payload + prompt
      ▼
    {
      payload: { city: "Curitiba", weather_time, temperature, humidity,
                 rain, precipitation, wind_speed,
                 weather_phrase: "céu encoberto",
                 events_list: "- 2026-04-23 19:00 AI Study Group (Lab 3)\n..." },
      prompt: "<rendered from examples/ollama-prompt.txt>"
    }
      ▼
[5] POST localhost:11434/api/generate
      body: { model: "llama3.1:8b", prompt, stream: false }
      ▼
    { response: "Bom dia! Em Curitiba hoje...", done: true, ... }
      ▼
[6] Code node — word count validation (50..200)
      ▼
[7] POST localhost:8800/tts
      body: { text, voice: "pf_dora" }
      ▼
    { audio_file: "audio/2026-04-22T14-30-02.wav", duration_seconds: 28.3 }
      ▼
[8] Set node — build row (12 columns)
      ▼
[9] Google Sheets → results tab (append)
```

### Data-flow decisions

- **Curitiba coordinates hardcoded** in the HTTP node URL. No env var indirection for Etapa 1.
- **`events_list`** is a pre-rendered newline-joined string (not a JSON array). Matches `examples/ollama-prompt.txt` verbatim.
- **`events_used`** column stores the same pre-rendered string — direct audit trail of what the LLM received.
- **Empty events today** is normal, not an error: `events_list = "Nenhum evento registrado hoje."`
- **`weather_code` → Portuguese phrase** is mapped in the Code node using the WMO code table (deterministic). Unknown codes fall back to `"condição indefinida"`. A minimum mapping is included:

  | WMO code | pt-BR phrase |
  |---|---|
  | 0 | céu limpo |
  | 1, 2 | parcialmente nublado |
  | 3 | céu encoberto |
  | 45, 48 | neblina |
  | 51, 53, 55 | garoa |
  | 61, 63, 65 | chuva fraca / moderada / forte |
  | 66, 67 | chuva congelante |
  | 71, 73, 75 | neve |
  | 80, 81, 82 | pancadas de chuva |
  | 95, 96, 99 | trovoada |

- **Audio filenames** are ISO-8601 with colons replaced by dashes: `2026-04-22T14-30-02.wav`.

## 7. Error handling

Philosophy: errors are **visible and recorded**, not swallowed. Every failed run still produces a `results` row with `status=error` and a meaningful `error_message`.

| # | Failure | Detection | Response |
|---|---|---|---|
| 1 | Open-Meteo unreachable / non-200 | HTTP node "Continue On Fail" | Error branch → `error_message="weather_api: <code> <body>"` |
| 2 | Google Sheets `events` read fails | Sheets node error | Error branch → user re-authorizes credential and re-runs |
| 3 | Events tab empty for today | Code node sees `[].length === 0` | Not an error; sets `events_list = "Nenhum evento registrado hoje."` |
| 4 | Ollama daemon down | HTTP to :11434 fails | Error branch → `error_message="ollama_down: <error>"` |
| 5 | Ollama output empty or out-of-range word count | Code node validates `50..200` words | Error branch → `error_message="ollama_bad_output: words=N"`. The text is still saved in `llm_response` for inspection. |
| 6 | Kokoro server down | HTTP to :8800 fails | Error branch → `error_message="kokoro_down: <error>"`. Row still saves bulletin text; `audio_file=""`. |
| 7 | Kokoro synthesis fails (bad voice, long text) | Kokoro returns 5xx JSON `{error}` | Error branch → `error_message="kokoro_tts: <msg>"` |
| 8 | Google Sheets `results` append fails | Sheets node error | Logged to n8n console only. Workflow marks execution failed. |

Not in scope for Etapa 1: retries, alerting, circuit breakers, schema validation on Open-Meteo.

## 8. Testing

Three layers, mapping to `docs/05-testing-checklist.md`:

### Layer 1 — Component smoke tests

`python tools/smoke.py` runs three probes:

- `smoke_weather` — GET Open-Meteo; passes when `current.temperature_2m` is a number
- `smoke_ollama` — POST `/api/generate` with fixed pt-BR prompt; passes when `response` is a non-empty string <300 chars
- `smoke_kokoro` — POST `/tts` with "Bom dia. Este é um teste do CampusCast AI."; passes when the returned file exists on disk and >1 KB

Exit 0 on all green, 1 otherwise. Bash wrappers exist for single-probe convenience.

### Layer 2 — Workflow integration test (the graded demo)

Manual via the n8n editor:

1. Click Execute Workflow.
2. All success-path nodes turn green within ~60 seconds.
3. WAV exists at `./audio/<iso>.wav`, plays audibly.
4. Row appended to `results` tab with all 12 columns populated, `status=ok`.

### Layer 3 — Quality checks (direct from `docs/05-testing-checklist.md`)

- Bulletin ≤ 120 words (also enforced in Code node; 200 is the hard upper bound, 120 the soft target)
- Understandable Portuguese
- Does not invent events (audit `llm_response` against `events_used`)
- Audio is clear
- Risk advice only when warranted by weather data

### Failure-path evidence run

Intentional failure: stop the Kokoro server, execute the workflow, confirm an error row appears with `status=error` and a populated `error_message`. Screenshot both a success and failure row.

## 9. Evidence doc (`docs/07-setup-evidence.md`)

New file the user fills during setup. Minimum contents:

- JSON sample response from Open-Meteo (from `smoke.py`)
- Terminal output of `ollama run llama3.1:8b "..."` with a short Portuguese prompt
- Output of `python tools/smoke.py` with all three probes green
- Screenshot of n8n editor open at `localhost:5678` with the imported workflow visible
- Screenshot of the Google Sheet with at least one success row and one error row
- Pointer to the generated audio file in `./audio/`

## 10. Out of scope (YAGNI, explicitly deferred)

- Schedule Trigger (daily cron) — Etapa 2
- Email / WhatsApp / Telegram delivery — Etapa 2
- Retries, alerting, error dashboards — Etapa 2
- Env-var-driven city/coordinates — Etapa 2 (needed when multiple cities)
- Dockerfile / docker-compose — not needed for single-machine prototype
- CI pipeline / unit tests for the JS Code node — over-engineered for this scope
- Audio file upload to Drive — Etapa 2
- Caching of weather / events — one run/day makes caching pointless

## 11. Open items to verify during implementation

1. Kokoro Brazilian Portuguese voice quality (`pf_dora` or other pt-BR voice) — fall back to Piper TTS if inadequate.
2. Exact WMO weather-code list from Open-Meteo documentation — extend the mapping table if the live API emits codes we haven't mapped.
3. n8n Google Sheets OAuth2 setup — may require enabling the Google Sheets API in the Google Cloud project; the implementation plan will include the step-by-step.

## 12. Success criteria

The design is successful when the following are true simultaneously:

- `python tools/smoke.py` returns exit 0.
- Clicking "Execute Workflow" in n8n produces a green execution in ≤60 seconds.
- A WAV file plays intelligible Portuguese audio of the bulletin.
- A row with all 12 columns appears in the `results` tab with `status=ok`.
- An intentional-failure run produces a row with `status=error` and a meaningful `error_message`.
- `docs/07-setup-evidence.md` contains the artifacts listed in §9.
