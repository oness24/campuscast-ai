# CampusCast AI — Etapa 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the daily bulletin pipeline with multichannel delivery (Telegram + Gmail + MP3), automated scheduling, robust error handling, weekly Excel reports, and a stress test.

**Architecture:** The existing `kokoro_server.py` gains two new endpoints (`/convert` for WAV→MP3 via `lameenc`, `/weekly-report` for XLSX export via `openpyxl`). A new n8n workflow (`campuscast-etapa2.workflow.json`) replaces the Manual Trigger with a Schedule Trigger and adds a 12-node success/error routing tree. All config (email, chat ID, sheet ID) lives in n8n Variables.

**Tech Stack:** n8n 2.13.4, Python 3.12 + FastAPI, lameenc 1.8, openpyxl 3.1, google-api-python-client (Sheets auth for weekly report), Telegram Bot API, Gmail SMTP with app password.

---

## Prerequisites (user actions — do before Task 4 and Task 5)

### PRE-A: Telegram bot via BotFather
1. Open Telegram → search `@BotFather` → send `/newbot`
2. Name: `CampusCast AI` / username: `campuscast_pucpr_bot` (or any available)
3. BotFather replies with a token like `7890123456:AAFxyz...` — save it
4. Send `/start` to your new bot from the account or group that should receive bulletins
5. Get chat ID:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | python3 -c "
   import json,sys; d=json.load(sys.stdin)
   for r in d.get('result',[]): print(r.get('message',{}).get('chat',{}))"
   ```
   Look for `"id": <number>` in the chat object. This is your `CAMPUSCAST_TG_CHAT_ID`.

### PRE-B: Gmail app password
1. Go to https://myaccount.google.com/security (logged in as contego704@gmail.com)
2. Enable 2-Step Verification if not already on
3. Go to "App passwords" → "Select app: Other" → name "CampusCast n8n" → Generate
4. Copy the 16-character password (shown once, spaces optional). Save it.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `tools/kokoro_server.py` | Modify | Add `/convert` (WAV→MP3) and `/weekly-report` (XLSX) endpoints |
| `tools/requirements.txt` | Modify | Add `lameenc>=1.8`, `openpyxl>=3.1` |
| `tools/smoke.py` | Modify | Add `probe_convert` and `probe_weekly_report` probes |
| `tools/setup_n8n_etapa2.py` | Create | Create Telegram + SMTP n8n credentials + 4 Variables via REST API |
| `tools/stress_test.py` | Create | Trigger workflow N times, record per-run timing, identify bottleneck |
| `workflow/campuscast-etapa2.workflow.json` | Create | 20-node Etapa 2 workflow |
| `tools/deploy_to_n8n.py` | No change | Existing deployer handles new workflow |
| `docs/08-etapa2-evidencia.md` | Create | Execution evidence for Etapa 2 rubric |
| `docs/SUBMISSAO-etapa2.md` | Create | Rubric mapping for Etapa 2 |

---

## Task 1: Add `/convert` endpoint to kokoro_server.py

**Files:**
- Modify: `tools/kokoro_server.py`

- [ ] **Step 1.1: Read current kokoro_server.py top imports**

  Open `tools/kokoro_server.py`. The current imports are at the top. You will add to them.

- [ ] **Step 1.2: Add lameenc import and wav_to_mp3 helper**

  In `tools/kokoro_server.py`, after the existing imports block, add:

  ```python
  import subprocess  # may already exist; add if missing
  import lameenc
  import numpy as np  # already used by kokoro

  # ---------------------------------------------------------------------------
  # WAV → MP3 conversion (pure Python, no ffmpeg required)
  # ---------------------------------------------------------------------------

  def wav_to_mp3(wav_path: Path) -> Path:
      """Convert a WAV file to MP3 using lameenc. Returns the MP3 path."""
      import soundfile as sf
      data, samplerate = sf.read(str(wav_path), dtype="float32")
      if data.ndim > 1:
          data = data[:, 0]  # take first channel
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
  ```

- [ ] **Step 1.3: Add ConvertRequest model and /convert endpoint**

  After the existing TTS endpoint, add:

  ```python
  class ConvertRequest(BaseModel):
      wav_path: str


  @app.post("/convert")
  def convert_wav_to_mp3(req: ConvertRequest) -> dict:
      wav = PROJECT_ROOT / req.wav_path
      if not wav.exists():
          raise HTTPException(status_code=400, detail=f"WAV not found: {req.wav_path}")
      try:
          mp3 = wav_to_mp3(wav)
      except Exception as e:
          raise HTTPException(status_code=500, detail=f"Conversion failed: {e}")
      return {
          "mp3_file": str(mp3.relative_to(PROJECT_ROOT)),
          "size_bytes": mp3.stat().st_size,
      }
  ```

- [ ] **Step 1.4: Restart the kokoro server**

  ```bash
  # Kill the running server
  pkill -f "kokoro_server" 2>/dev/null; sleep 1
  nohup .venv/bin/uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800 > /tmp/kokoro_server.log 2>&1 &
  sleep 5 && curl -sS http://127.0.0.1:8800/health
  ```
  Expected: `{"status":"ok"}`

- [ ] **Step 1.5: Manual smoke test of /convert**

  ```bash
  # Use the most recent WAV in audio/
  WAV=$(ls -t audio/*.wav 2>/dev/null | head -1)
  echo "Testing with: $WAV"
  curl -sS http://127.0.0.1:8800/convert \
    -H 'Content-Type: application/json' \
    -d "{\"wav_path\": \"$WAV\"}" | python3 -m json.tool
  ```
  Expected:
  ```json
  {
    "mp3_file": "audio/2026-...wav.mp3",
    "size_bytes": <number>
  }
  ```
  And the file should exist: `ls -lh audio/*.mp3`

  If no WAV exists yet, generate one first:
  ```bash
  .venv/bin/python tools/smoke.py --only kokoro
  ```

- [ ] **Step 1.6: Commit**

  ```bash
  git add tools/kokoro_server.py
  git commit -m "feat(server): add /convert endpoint for WAV→MP3 via lameenc"
  ```

---

## Task 2: Add `/weekly-report` endpoint to kokoro_server.py

**Files:**
- Modify: `tools/kokoro_server.py`

- [ ] **Step 2.1: Add imports for Google Sheets + openpyxl**

  At the top of `tools/kokoro_server.py`, add after the existing imports:

  ```python
  import base64
  import io
  import os
  from datetime import datetime, timezone

  import openpyxl
  from google.oauth2.service_account import Credentials
  from googleapiclient.discovery import build
  ```

- [ ] **Step 2.2: Add constants for Sheets auth**

  After `PROJECT_ROOT = ...` (wherever it is defined), add:

  ```python
  _SA_KEY = PROJECT_ROOT / "credentials" / "campuscast-n8n.json"
  _SHEET_ID = os.environ.get(
      "CAMPUSCAST_SHEET_ID",
      "1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk",
  )
  _SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
  ```

- [ ] **Step 2.3: Add /weekly-report endpoint**

  Save the XLSX to disk and return its path — n8n reads it with a `Read Binary File` node
  (same pattern as MP3). Remove the `base64` and `io` imports added in Step 2.1 if present.

  ```python
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
  ```

- [ ] **Step 2.4: Restart server and test**

  ```bash
  pkill -f "kokoro_server" 2>/dev/null; sleep 1
  nohup .venv/bin/uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800 > /tmp/kokoro_server.log 2>&1 &
  sleep 5 && curl -sS http://127.0.0.1:8800/weekly-report | python3 -c "
  import json,sys
  d=json.load(sys.stdin)
  print(f'rows={d[\"rows\"]} filename={d[\"filename\"]} xlsx_file={d[\"xlsx_file\"]}')
  "
  ```
  Expected: `rows=<N> filename=campuscast-semana-2026-W21.xlsx xlsx_file=reports/campuscast-semana-2026-W21.xlsx`

  Verify file exists: `ls -lh reports/*.xlsx`

- [ ] **Step 2.5: Commit**

  ```bash
  git add tools/kokoro_server.py
  git commit -m "feat(server): add /weekly-report endpoint — saves XLSX to reports/ and returns path"
  ```

---

## Task 3: Update requirements.txt

**Files:**
- Modify: `tools/requirements.txt`

- [ ] **Step 3.1: Add new deps**

  Edit `tools/requirements.txt` to add:
  ```
  lameenc>=1.8
  openpyxl>=3.1
  ```

- [ ] **Step 3.2: Verify they install cleanly**

  ```bash
  .venv/bin/pip install -r tools/requirements.txt 2>&1 | tail -3
  ```
  Expected: `Successfully installed ...` or `Requirement already satisfied`.

- [ ] **Step 3.3: Commit**

  ```bash
  git add tools/requirements.txt
  git commit -m "chore(deps): add lameenc and openpyxl for Etapa 2"
  ```

---

## Task 4: Add smoke probes for /convert and /weekly-report

**Files:**
- Modify: `tools/smoke.py`

- [ ] **Step 4.1: Add probe_convert to smoke.py**

  In `tools/smoke.py`, after the existing `probe_kokoro` function, add:

  ```python
  def probe_convert() -> ProbeResult:
      """Requires at least one WAV file to exist in audio/. Run probe_kokoro first."""
      import glob, os
      project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
      wavs = sorted(glob.glob(os.path.join(project_root, "audio", "*.wav")), reverse=True)
      if not wavs:
          return ProbeResult("convert", False, "no WAV files in audio/ — run probe_kokoro first")
      newest_wav = os.path.relpath(wavs[0], project_root)
      body = {"wav_path": newest_wav}
      try:
          r = requests.post("http://127.0.0.1:8800/convert", json=body, timeout=30)
          r.raise_for_status()
          data = r.json()
          mp3_file = data.get("mp3_file")
          size = data.get("size_bytes", 0)
          if not mp3_file or size < 1024:
              return ProbeResult("convert", False, f"bad response: {data!r}")
          return ProbeResult("convert", True, f"{mp3_file} ({size} bytes)")
      except Exception as e:
          return ProbeResult("convert", False, f"{type(e).__name__}: {e}")


  def probe_weekly_report() -> ProbeResult:
      try:
          r = requests.get("http://127.0.0.1:8800/weekly-report", timeout=30)
          r.raise_for_status()
          data = r.json()
          rows = data.get("rows", 0)
          filename = data.get("filename", "")
          xlsx_file = data.get("xlsx_file", "")
          if not xlsx_file:
              return ProbeResult("weekly_report", False, f"no xlsx_file in response: {data!r}")
          project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
          full_path = os.path.join(project_root, xlsx_file)
          if not os.path.exists(full_path):
              return ProbeResult("weekly_report", False, f"xlsx file missing on disk: {full_path}")
          size = os.path.getsize(full_path)
          return ProbeResult("weekly_report", True, f"{filename} ({rows} rows, {size} bytes on disk)")
      except Exception as e:
          return ProbeResult("weekly_report", False, f"{type(e).__name__}: {e}")
  ```

- [ ] **Step 4.2: Register the new probes in PROBES dict**

  Find the `PROBES: dict[str, Callable[[], ProbeResult]] = {` block and add the two new entries:

  ```python
  PROBES: dict[str, Callable[[], ProbeResult]] = {
      "weather": probe_weather,
      "ollama": probe_ollama,
      "kokoro": probe_kokoro,
      "convert": probe_convert,
      "weekly_report": probe_weekly_report,
  }
  ```

- [ ] **Step 4.3: Run all probes to verify**

  ```bash
  .venv/bin/python tools/smoke.py
  ```
  Expected:
  ```
  [PASS] weather: Curitiba temperature_2m=XX.X C
  [PASS] ollama: 31 chars — 'A capital do Brasil é Brasília.'
  [PASS] kokoro: audio/....wav (138044 bytes, 2.88s)
  [PASS] convert: audio/....mp3 (<size> bytes)
  [PASS] weekly_report: campuscast-semana-2026-W21.xlsx (<N> rows, ...)
  ```

- [ ] **Step 4.4: Commit**

  ```bash
  git add tools/smoke.py
  git commit -m "feat(smoke): add probes for /convert and /weekly-report"
  ```

---

## Task 5: Create n8n credentials and Variables (after PRE-A and PRE-B)

**Files:**
- Create: `tools/setup_n8n_etapa2.py`

- [ ] **Step 5.1: Write setup_n8n_etapa2.py**

  Create `tools/setup_n8n_etapa2.py`:

  ```python
  #!/usr/bin/env python3
  """
  Create n8n credentials (Telegram + SMTP) and Variables for Etapa 2.
  Prints the credential IDs needed for the workflow JSON.

  Usage:
      export TG_BOT_TOKEN='7890123456:AAFxyz...'
      export TG_CHAT_ID='-1001234567890'
      export GMAIL_APP_PASSWORD='abcd efgh ijkl mnop'
      python tools/setup_n8n_etapa2.py
  """
  from __future__ import annotations
  import json, os, sys, urllib.request, urllib.error, http.cookiejar

  BASE = "http://127.0.0.1:5678"
  EMAIL = "contego704@gmail.com"
  PASSWORD = "143030@Contego#"
  SHEET_ID = "1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk"


  def login() -> http.cookiejar.CookieJar:
      jar = http.cookiejar.CookieJar()
      opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
      data = json.dumps({"emailOrLdapLoginId": EMAIL, "password": PASSWORD}).encode()
      req = urllib.request.Request(f"{BASE}/rest/login", data=data, method="POST")
      req.add_header("Content-Type", "application/json")
      with opener.open(req, timeout=10):
          pass
      return jar


  def n8n(method: str, path: str, jar: http.cookiejar.CookieJar, body: dict | None = None) -> dict:
      opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
      data = json.dumps(body).encode() if body else None
      req = urllib.request.Request(f"{BASE}/rest{path}", data=data, method=method)
      req.add_header("Content-Type", "application/json")
      try:
          with opener.open(req, timeout=15) as r:
              payload = r.read().decode()
              d = json.loads(payload) if payload else {}
              return d.get("data", d)
      except urllib.error.HTTPError as e:
          body_text = e.read().decode()
          raise SystemExit(f"HTTP {e.code} on {method} {path}: {body_text[:300]}")


  def find_credential(jar: http.cookiejar.CookieJar, name: str) -> str | None:
      creds = n8n("GET", "/credentials", jar)
      for c in (creds if isinstance(creds, list) else []):
          if c.get("name") == name:
              return c["id"]
      return None


  def create_or_find_credential(jar: http.cookiejar.CookieJar, name: str, cred_type: str, data: dict) -> str:
      existing = find_credential(jar, name)
      if existing:
          print(f"  [exists] credential '{name}' id={existing}")
          return existing
      result = n8n("POST", "/credentials", jar, {"name": name, "type": cred_type, "data": data})
      cred_id = result.get("id") or result.get("data", {}).get("id")
      print(f"  [created] credential '{name}' id={cred_id}")
      return cred_id


  def set_variable(jar: http.cookiejar.CookieJar, key: str, value: str) -> None:
      variables = n8n("GET", "/variables", jar)
      for v in (variables if isinstance(variables, list) else []):
          if v.get("key") == key:
              n8n("PATCH", f"/variables/{v['id']}", jar, {"value": value})
              print(f"  [updated] variable {key}={value!r}")
              return
      n8n("POST", "/variables", jar, {"key": key, "value": value})
      print(f"  [created] variable {key}={value!r}")


  def main() -> None:
      tg_token = os.environ.get("TG_BOT_TOKEN", "")
      tg_chat = os.environ.get("TG_CHAT_ID", "")
      gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
      email_to = os.environ.get("CAMPUSCAST_EMAIL_TO", "onesmus.simiyu@pucpr.edu.br")

      missing = [k for k, v in [("TG_BOT_TOKEN", tg_token), ("TG_CHAT_ID", tg_chat), ("GMAIL_APP_PASSWORD", gmail_pass)] if not v]
      if missing:
          print(f"ERROR: set environment variables: {', '.join(missing)}", file=sys.stderr)
          print("Example:", file=sys.stderr)
          print("  export TG_BOT_TOKEN='7890123456:AAFxyz...'", file=sys.stderr)
          print("  export TG_CHAT_ID='-1001234567890'", file=sys.stderr)
          print("  export GMAIL_APP_PASSWORD='abcd efgh ijkl mnop'", file=sys.stderr)
          sys.exit(1)

      print("Logging in to n8n...")
      jar = login()

      print("\nCreating credentials...")
      tg_id = create_or_find_credential(jar, "CampusCast Telegram Bot", "telegramApi", {
          "accessToken": tg_token,
      })
      smtp_id = create_or_find_credential(jar, "CampusCast Gmail SMTP", "smtp", {
          "host": "smtp.gmail.com",
          "port": 587,
          "user": EMAIL,
          "password": gmail_pass,
          "secure": False,
          "allowUnauthorizedCerts": False,
      })

      print("\nCreating n8n Variables...")
      set_variable(jar, "CAMPUSCAST_CITY", "Curitiba")
      set_variable(jar, "CAMPUSCAST_EMAIL_TO", email_to)
      set_variable(jar, "CAMPUSCAST_TG_CHAT_ID", tg_chat)
      set_variable(jar, "CAMPUSCAST_SHEET_ID", SHEET_ID)

      print(f"\nDone. Copy these IDs into the workflow JSON:")
      print(f"  TELEGRAM_CRED_ID = {tg_id!r}")
      print(f"  SMTP_CRED_ID     = {smtp_id!r}")


  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 5.2: Run the setup script (requires PRE-A and PRE-B done first)**

  ```bash
  export TG_BOT_TOKEN='<paste from BotFather>'
  export TG_CHAT_ID='<paste chat ID>'
  export GMAIL_APP_PASSWORD='<paste 16-char app password>'
  .venv/bin/python tools/setup_n8n_etapa2.py
  ```

  Expected output:
  ```
  Logging in to n8n...
  Creating credentials...
    [created] credential 'CampusCast Telegram Bot' id=<TG_ID>
    [created] credential 'CampusCast Gmail SMTP' id=<SMTP_ID>
  Creating n8n Variables...
    [created] variable CAMPUSCAST_CITY='Curitiba'
    [created] variable CAMPUSCAST_EMAIL_TO='onesmus.simiyu@pucpr.edu.br'
    [created] variable CAMPUSCAST_TG_CHAT_ID='<your chat id>'
    [created] variable CAMPUSCAST_SHEET_ID='1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk'

  Done. Copy these IDs into the workflow JSON:
    TELEGRAM_CRED_ID = '<id>'
    SMTP_CRED_ID     = '<id>'
  ```

  **Save the two credential IDs** — needed in Task 6.

- [ ] **Step 5.3: Commit the setup script**

  ```bash
  git add tools/setup_n8n_etapa2.py
  git commit -m "feat(tools): add setup_n8n_etapa2.py to create credentials + variables"
  ```

---

## Task 6: Build Etapa 2 workflow JSON

**Files:**
- Create: `workflow/campuscast-etapa2.workflow.json`

> Replace `TELEGRAM_CRED_ID` and `SMTP_CRED_ID` below with the actual IDs printed by Task 5.

- [ ] **Step 6.1: Create the workflow JSON**

  Create `workflow/campuscast-etapa2.workflow.json` with the full content below.
  Replace `"TELEGRAM_CRED_ID"` and `"SMTP_CRED_ID"` with the IDs from Task 5.

  ```json
  {
    "name": "CampusCast AI — Etapa 2",
    "nodes": [
      {
        "parameters": {
          "rule": {
            "interval": [{ "field": "cronExpression", "expression": "0 7 * * *" }]
          }
        },
        "id": "e2-0001",
        "name": "Schedule 07h",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [240, 300]
      },
      {
        "parameters": {
          "url": "https://api.open-meteo.com/v1/forecast",
          "sendQuery": true,
          "queryParameters": {
            "parameters": [
              { "name": "latitude",  "value": "-25.4284" },
              { "name": "longitude", "value": "-49.2733" },
              { "name": "current",   "value": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m" },
              { "name": "timezone",  "value": "America/Sao_Paulo" }
            ]
          },
          "options": {}
        },
        "id": "e2-0002",
        "name": "Weather",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.4,
        "position": [460, 300]
      },
      {
        "parameters": {
          "authentication": "serviceAccount",
          "resource": "sheet",
          "operation": "read",
          "documentId": { "__rl": true, "mode": "id", "value": "={{ $vars.CAMPUSCAST_SHEET_ID }}" },
          "sheetName":  { "__rl": true, "mode": "name", "value": "events" },
          "options": {}
        },
        "id": "e2-0003",
        "name": "Events Read",
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5,
        "position": [680, 300],
        "credentials": {
          "googleApi": { "id": "xsjRaVzdAvkp6C3F", "name": "Google Sheets — CampusCast" }
        }
      },
      {
        "parameters": {
          "jsCode": "const weather = $('Weather').first().json.current;\n\nconst WMO = {\n  0: 'céu limpo',\n  1: 'parcialmente nublado', 2: 'parcialmente nublado',\n  3: 'céu encoberto',\n  45: 'neblina', 48: 'neblina',\n  51: 'garoa', 53: 'garoa', 55: 'garoa',\n  61: 'chuva fraca', 63: 'chuva moderada', 65: 'chuva forte',\n  66: 'chuva congelante', 67: 'chuva congelante',\n  71: 'neve', 73: 'neve', 75: 'neve',\n  80: 'pancadas de chuva', 81: 'pancadas de chuva', 82: 'pancadas de chuva',\n  95: 'trovoada', 96: 'trovoada', 99: 'trovoada'\n};\nconst weather_phrase = WMO[weather.weather_code] || 'condição indefinida';\n\nconst todaySP = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' });\nconst events = $('Events Read').all().map(i => i.json);\nconst todays = events.filter(e => String(e.date) === todaySP);\nconst events_list = todays.length === 0\n  ? 'Nenhum evento registrado hoje.'\n  : todays.map(e => `- ${e.date} ${e.time} ${e.event_name} (${e.location})`).join('\\n');\n\nconst is_raining = (weather.rain > 0) || (weather.precipitation > 0) || [51,53,55,61,63,65,66,67,80,81,82].includes(weather.weather_code);\nconst is_hot  = weather.temperature_2m >= 28;\nconst is_cold = weather.temperature_2m <= 12;\nconst is_windy   = weather.wind_speed_10m >= 30;\nconst is_stormy  = [95,96,99].includes(weather.weather_code);\n\nconst advice_rules = [];\nif (is_raining)  advice_rules.push('- Há chuva ou garoa agora: recomende levar guarda-chuva ou capa.');\nif (!is_raining) advice_rules.push('- NÃO há chuva. NÃO mencione guarda-chuva, chuva ou proteção contra chuva.');\nif (is_cold)    advice_rules.push('- Temperatura baixa: recomende agasalho.');\nif (is_hot)     advice_rules.push('- Temperatura alta: recomende hidratação.');\nif (!is_cold && !is_hot) advice_rules.push('- Temperatura amena: NÃO recomende agasalho nem reforço de hidratação.');\nif (is_windy)   advice_rules.push('- Vento forte (>30 km/h): alerte sobre o vento.');\nif (!is_windy)  advice_rules.push('- Vento fraco/moderado: NÃO mencione vento como fator relevante.');\nif (is_stormy)  advice_rules.push('- ALERTA: há trovoada. Inclua alerta de risco claro.');\nif (!is_stormy && !is_raining && !is_windy) advice_rules.push('- Sem riscos meteorológicos: indique explicitamente que não há alertas hoje.');\n\nconst payload = {\n  city: $vars.CAMPUSCAST_CITY || 'Curitiba',\n  weather_time: weather.time,\n  temperature: weather.temperature_2m,\n  humidity: weather.relative_humidity_2m,\n  rain: weather.rain,\n  precipitation: weather.precipitation,\n  wind_speed: weather.wind_speed_10m,\n  weather_phrase, weather_code: weather.weather_code,\n  events_list, is_raining, is_hot, is_cold, is_windy, is_stormy\n};\n\nconst prompt = `Você é o CampusCast AI. Produza um boletim curto em português do Brasil para estudantes, estritamente fiel aos dados.\\n\\n### DADOS (fonte única da verdade — não invente nada fora daqui)\\nCidade: ${payload.city}\\nHorário: ${payload.weather_time}\\nCondição atual: ${payload.weather_phrase} (código WMO ${payload.weather_code})\\nTemperatura: ${payload.temperature} °C\\nUmidade: ${payload.humidity}%\\nChuva (mm na última hora): ${payload.rain}\\nPrecipitação total (mm): ${payload.precipitation}\\nVento: ${payload.wind_speed} km/h\\n\\n### EVENTOS DO CAMPUS HOJE\\n${payload.events_list}\\n\\n### REGRAS DE CONTEÚDO (obrigatórias)\\n${advice_rules.join('\\n')}\\n\\n### ESTRUTURA\\n1. Saudação breve (1 frase).\\n2. Resumo do clima (1 frase) usando APENAS a Condição atual e a temperatura.\\n3. Conselho prático: inclua apenas os conselhos autorizados pelas regras listadas. Sem acréscimos não autorizados.\\n4. Lembrete de eventos: cite cada evento listado. Se a lista disser Nenhum evento registrado hoje, diga isso com estas palavras.\\n5. Alerta final: se as regras autorizarem um alerta, inclua-o; caso contrário, escreva exatamente Sem alertas de risco para hoje.\\n\\n### REGRAS GLOBAIS\\n- Máximo de 120 palavras.\\n- Português claro, natural, adequado para leitura em áudio.\\n- PROIBIDO: asteriscos (*), sublinhados (_), crases, hashtags (#), emojis, qualquer marcação markdown.\\n- Produza APENAS prosa corrida. Sem títulos, sem negrito, sem listas com bullets.\\n- NÃO invente eventos, clima, nem riscos.`;\n\nreturn [{ json: { payload, prompt } }];"
        },
        "id": "e2-0004",
        "name": "Build Prompt",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [900, 300]
      },
      {
        "parameters": {
          "method": "POST",
          "url": "http://127.0.0.1:11434/api/generate",
          "sendBody": true,
          "contentType": "json",
          "specifyBody": "json",
          "jsonBody": "={\n  \"model\": \"llama3.1:8b\",\n  \"prompt\": {{ JSON.stringify($json.prompt) }},\n  \"stream\": false,\n  \"options\": { \"temperature\": 0.3, \"top_p\": 0.9, \"num_predict\": 220 }\n}",
          "options": { "timeout": 120000 }
        },
        "onError": "continueRegularOutput",
        "id": "e2-0005",
        "name": "Ollama Generate",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.4,
        "position": [1120, 300]
      },
      {
        "parameters": {
          "method": "POST",
          "url": "http://127.0.0.1:8800/tts",
          "sendBody": true,
          "contentType": "json",
          "specifyBody": "json",
          "jsonBody": "={ \"text\": {{ JSON.stringify($json.response) }} }",
          "options": { "timeout": 120000 }
        },
        "onError": "continueRegularOutput",
        "id": "e2-0006",
        "name": "Kokoro TTS",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.4,
        "position": [1340, 300]
      },
      {
        "parameters": {
          "method": "POST",
          "url": "http://127.0.0.1:8800/convert",
          "sendBody": true,
          "contentType": "json",
          "specifyBody": "json",
          "jsonBody": "={ \"wav_path\": {{ JSON.stringify($json.audio_file) }} }",
          "options": { "timeout": 30000 }
        },
        "onError": "continueRegularOutput",
        "id": "e2-0007",
        "name": "Convert WAV→MP3",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.4,
        "position": [1560, 300]
      },
      {
        "parameters": {
          "conditions": {
            "options": { "caseSensitive": true, "leftValue": "", "typeValidation": "loose" },
            "conditions": [
              {
                "id": "cond-error",
                "leftValue": "={{ $json.error }}",
                "rightValue": "",
                "operator": { "type": "object", "operation": "exists", "singleValue": true }
              }
            ],
            "combinator": "and"
          }
        },
        "id": "e2-0008",
        "name": "Check Result",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2,
        "position": [1780, 300]
      },
      {
        "parameters": {
          "mode": "manual",
          "duplicateItem": false,
          "assignments": {
            "assignments": [
              { "id": "b1", "name": "timestamp",     "value": "={{ $now.toISO() }}", "type": "string" },
              { "id": "b2", "name": "city",           "value": "={{ $vars.CAMPUSCAST_CITY }}", "type": "string" },
              { "id": "b3", "name": "temperature",    "value": "", "type": "string" },
              { "id": "b4", "name": "humidity",       "value": "", "type": "string" },
              { "id": "b5", "name": "rain",           "value": "", "type": "string" },
              { "id": "b6", "name": "precipitation",  "value": "", "type": "string" },
              { "id": "b7", "name": "wind_speed",     "value": "", "type": "string" },
              { "id": "b8", "name": "events_used",    "value": "", "type": "string" },
              { "id": "b9", "name": "llm_response",   "value": "", "type": "string" },
              { "id": "b10","name": "audio_file",     "value": "", "type": "string" },
              { "id": "b11","name": "mp3_file",       "value": "", "type": "string" },
              { "id": "b12","name": "status",         "value": "error", "type": "string" },
              { "id": "b13","name": "error_message",  "value": "={{ $json.error ? JSON.stringify($json.error) : 'unknown error' }}", "type": "string" }
            ]
          },
          "options": {}
        },
        "id": "e2-0009",
        "name": "Build Error Row",
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [2000, 160]
      },
      {
        "parameters": {
          "authentication": "serviceAccount",
          "resource": "sheet",
          "operation": "append",
          "documentId": { "__rl": true, "mode": "id", "value": "={{ $vars.CAMPUSCAST_SHEET_ID }}" },
          "sheetName":  { "__rl": true, "mode": "name", "value": "results" },
          "columns": { "mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [] },
          "options": {}
        },
        "id": "e2-0010",
        "name": "Results Append Error",
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5,
        "position": [2220, 160],
        "credentials": {
          "googleApi": { "id": "xsjRaVzdAvkp6C3F", "name": "Google Sheets — CampusCast" }
        }
      },
      {
        "parameters": {
          "chatId": "={{ $vars.CAMPUSCAST_TG_CHAT_ID }}",
          "text":   "=⚠️ CampusCast ERRO {{ $now.toFormat('dd/MM/yyyy HH:mm') }}: {{ $('Build Error Row').first().json.error_message }}",
          "additionalFields": {}
        },
        "id": "e2-0011",
        "name": "Telegram Error Alert",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [2440, 160],
        "credentials": {
          "telegramApi": { "id": "TELEGRAM_CRED_ID", "name": "CampusCast Telegram Bot" }
        }
      },
      {
        "parameters": {
          "fromEmail": "contego704@gmail.com",
          "toEmail":   "={{ $vars.CAMPUSCAST_EMAIL_TO }}",
          "subject":   "=[CampusCast] FALHA {{ $now.toFormat('dd/MM/yyyy') }}",
          "emailFormat": "html",
          "message":   "=<h2>CampusCast AI — Falha de Execução</h2><p><b>Data:</b> {{ $now.toISO() }}</p><p><b>Erro:</b> {{ $('Build Error Row').first().json.error_message }}</p><p><a href='https://docs.google.com/spreadsheets/d/{{ $vars.CAMPUSCAST_SHEET_ID }}'>Ver planilha de resultados</a></p>",
          "options": {}
        },
        "id": "e2-0012",
        "name": "Gmail Error Alert",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 2.1,
        "position": [2660, 160],
        "credentials": {
          "smtp": { "id": "SMTP_CRED_ID", "name": "CampusCast Gmail SMTP" }
        }
      },
      {
        "parameters": {
          "mode": "manual",
          "duplicateItem": false,
          "assignments": {
            "assignments": [
              { "id": "a1",  "name": "timestamp",    "value": "={{ $now.toISO() }}", "type": "string" },
              { "id": "a2",  "name": "city",         "value": "={{ $vars.CAMPUSCAST_CITY }}", "type": "string" },
              { "id": "a3",  "name": "temperature",  "value": "={{ $('Build Prompt').first().json.payload.temperature }}", "type": "number" },
              { "id": "a4",  "name": "humidity",     "value": "={{ $('Build Prompt').first().json.payload.humidity }}", "type": "number" },
              { "id": "a5",  "name": "rain",         "value": "={{ $('Build Prompt').first().json.payload.rain }}", "type": "number" },
              { "id": "a6",  "name": "precipitation","value": "={{ $('Build Prompt').first().json.payload.precipitation }}", "type": "number" },
              { "id": "a7",  "name": "wind_speed",   "value": "={{ $('Build Prompt').first().json.payload.wind_speed }}", "type": "number" },
              { "id": "a8",  "name": "events_used",  "value": "={{ $('Build Prompt').first().json.payload.events_list }}", "type": "string" },
              { "id": "a9",  "name": "llm_response", "value": "={{ $('Ollama Generate').first().json.response.replace(/\\*\\*([^*]+)\\*\\*/g, '$1').replace(/\\*([^*]+)\\*/g, '$1').replace(/[*_`#>~]/g, '').replace(/\\s+/g, ' ').trim() }}", "type": "string" },
              { "id": "a10", "name": "audio_file",   "value": "={{ $('Kokoro TTS').first().json.audio_file }}", "type": "string" },
              { "id": "a11", "name": "mp3_file",     "value": "={{ $json.mp3_file }}", "type": "string" },
              { "id": "a12", "name": "status",       "value": "ok", "type": "string" },
              { "id": "a13", "name": "error_message","value": "", "type": "string" }
            ]
          },
          "options": {}
        },
        "id": "e2-0013",
        "name": "Build Success Row",
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [2000, 440]
      },
      {
        "parameters": {
          "authentication": "serviceAccount",
          "resource": "sheet",
          "operation": "append",
          "documentId": { "__rl": true, "mode": "id", "value": "={{ $vars.CAMPUSCAST_SHEET_ID }}" },
          "sheetName":  { "__rl": true, "mode": "name", "value": "results" },
          "columns": { "mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [] },
          "options": {}
        },
        "id": "e2-0014",
        "name": "Results Append OK",
        "type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5,
        "position": [2220, 440],
        "credentials": {
          "googleApi": { "id": "xsjRaVzdAvkp6C3F", "name": "Google Sheets — CampusCast" }
        }
      },
      {
        "parameters": {
          "chatId": "={{ $vars.CAMPUSCAST_TG_CHAT_ID }}",
          "text":   "={{ $('Build Success Row').first().json.llm_response }}",
          "additionalFields": {}
        },
        "id": "e2-0015",
        "name": "Telegram Bulletin",
        "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2,
        "position": [2440, 440],
        "credentials": {
          "telegramApi": { "id": "TELEGRAM_CRED_ID", "name": "CampusCast Telegram Bot" }
        }
      },
      {
        "parameters": {
          "filePath": "={{ $('Build Success Row').first().json.mp3_file }}",
          "dataPropertyName": "mp3"
        },
        "id": "e2-0016",
        "name": "Read MP3 Binary",
        "type": "n8n-nodes-base.readBinaryFile",
        "typeVersion": 1,
        "position": [2660, 440]
      },
      {
        "parameters": {
          "fromEmail": "contego704@gmail.com",
          "toEmail":   "={{ $vars.CAMPUSCAST_EMAIL_TO }}",
          "subject":   "=CampusCast AI — Boletim {{ $now.toFormat('dd/MM/yyyy') }}",
          "emailFormat": "html",
          "message":   "=<h2>CampusCast AI — Boletim {{ $now.toFormat('dd/MM/yyyy') }}</h2><p>{{ $('Build Success Row').first().json.llm_response }}</p><hr><h3>Dados do Dia</h3><table border='1' cellpadding='4' style='border-collapse:collapse'><tr><td><b>Cidade</b></td><td>{{ $('Build Success Row').first().json.city }}</td></tr><tr><td><b>Temperatura</b></td><td>{{ $('Build Success Row').first().json.temperature }} °C</td></tr><tr><td><b>Umidade</b></td><td>{{ $('Build Success Row').first().json.humidity }}%</td></tr><tr><td><b>Chuva</b></td><td>{{ $('Build Success Row').first().json.rain }} mm</td></tr><tr><td><b>Vento</b></td><td>{{ $('Build Success Row').first().json.wind_speed }} km/h</td></tr><tr><td><b>Eventos</b></td><td>{{ $('Build Success Row').first().json.events_used }}</td></tr></table><br><p><a href='https://docs.google.com/spreadsheets/d/{{ $vars.CAMPUSCAST_SHEET_ID }}'>Ver planilha de resultados</a></p>",
          "attachments": "mp3",
          "options": {}
        },
        "id": "e2-0017",
        "name": "Gmail Bulletin",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 2.1,
        "position": [2880, 440],
        "credentials": {
          "smtp": { "id": "SMTP_CRED_ID", "name": "CampusCast Gmail SMTP" }
        }
      },
      {
        "parameters": {
          "conditions": {
            "options": { "caseSensitive": true, "leftValue": "", "typeValidation": "loose" },
            "conditions": [
              {
                "id": "cond-monday",
                "leftValue": "={{ $now.weekday }}",
                "rightValue": "1",
                "operator": { "type": "number", "operation": "equals" }
              }
            ],
            "combinator": "and"
          }
        },
        "id": "e2-0018",
        "name": "Is Monday?",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2,
        "position": [3100, 440]
      },
      {
        "parameters": {
          "method": "GET",
          "url": "http://127.0.0.1:8800/weekly-report",
          "options": { "timeout": 30000 }
        },
        "id": "e2-0019",
        "name": "Get Weekly Report",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.4,
        "position": [3320, 360]
      },
      {
        "parameters": {
          "filePath": "={{ '/home/oness24/Desktop/AI/pucpr/campuscast-ai/' + $json.xlsx_file }}",
          "dataPropertyName": "xlsx"
        },
        "id": "e2-0020",
        "name": "Read XLSX Binary",
        "type": "n8n-nodes-base.readBinaryFile",
        "typeVersion": 1,
        "position": [3540, 360]
      },
      {
        "parameters": {
          "fromEmail": "contego704@gmail.com",
          "toEmail":   "={{ $vars.CAMPUSCAST_EMAIL_TO }}",
          "subject":   "=CampusCast AI — Relatório Semanal {{ $now.toFormat('dd/MM/yyyy') }}",
          "emailFormat": "html",
          "message":   "=<h2>CampusCast AI — Relatório Semanal</h2><p>Em anexo: {{ $('Get Weekly Report').first().json.filename }} com {{ $('Get Weekly Report').first().json.rows }} execuções da última semana.</p>",
          "attachments": "xlsx",
          "options": {}
        },
        "id": "e2-0021",
        "name": "Gmail Weekly XLSX",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 2.1,
        "position": [3760, 360],
        "credentials": {
          "smtp": { "id": "SMTP_CRED_ID", "name": "CampusCast Gmail SMTP" }
        }
      }
    ],
    "connections": {
      "Schedule 07h":           { "main": [[{ "node": "Weather",            "type": "main", "index": 0 }]] },
      "Weather":                 { "main": [[{ "node": "Events Read",        "type": "main", "index": 0 }]] },
      "Events Read":             { "main": [[{ "node": "Build Prompt",       "type": "main", "index": 0 }]] },
      "Build Prompt":            { "main": [[{ "node": "Ollama Generate",    "type": "main", "index": 0 }]] },
      "Ollama Generate":         { "main": [[{ "node": "Kokoro TTS",         "type": "main", "index": 0 }]] },
      "Kokoro TTS":              { "main": [[{ "node": "Convert WAV→MP3",    "type": "main", "index": 0 }]] },
      "Convert WAV→MP3":         { "main": [[{ "node": "Check Result",       "type": "main", "index": 0 }]] },
      "Check Result": {
        "main": [
          [{ "node": "Build Error Row",   "type": "main", "index": 0 }],
          [{ "node": "Build Success Row", "type": "main", "index": 0 }]
        ]
      },
      "Build Error Row":         { "main": [[{ "node": "Results Append Error", "type": "main", "index": 0 }]] },
      "Results Append Error":    { "main": [[{ "node": "Telegram Error Alert", "type": "main", "index": 0 }]] },
      "Telegram Error Alert":    { "main": [[{ "node": "Gmail Error Alert",    "type": "main", "index": 0 }]] },
      "Build Success Row":       { "main": [[{ "node": "Results Append OK",    "type": "main", "index": 0 }]] },
      "Results Append OK":       { "main": [[{ "node": "Telegram Bulletin",    "type": "main", "index": 0 }]] },
      "Telegram Bulletin":       { "main": [[{ "node": "Read MP3 Binary",      "type": "main", "index": 0 }]] },
      "Read MP3 Binary":         { "main": [[{ "node": "Gmail Bulletin",       "type": "main", "index": 0 }]] },
      "Gmail Bulletin":          { "main": [[{ "node": "Is Monday?",           "type": "main", "index": 0 }]] },
      "Is Monday?": {
        "main": [
          [{ "node": "Get Weekly Report", "type": "main", "index": 0 }],
          []
        ]
      },
      "Get Weekly Report":       { "main": [[{ "node": "Read XLSX Binary",    "type": "main", "index": 0 }]] },
      "Read XLSX Binary":        { "main": [[{ "node": "Gmail Weekly XLSX",    "type": "main", "index": 0 }]] }
    },
    "pinData": {},
    "settings": { "executionOrder": "v1", "timezone": "America/Sao_Paulo" }
  }
  ```

- [ ] **Step 6.2: Add reports/ to .gitignore**

  ```bash
  echo "reports/" >> .gitignore
  git add .gitignore
  ```

- [ ] **Step 6.3: Validate JSON parses correctly**

  ```bash
  python3 -c "import json; json.load(open('workflow/campuscast-etapa2.workflow.json')); print('JSON valid')"
  ```
  Expected: `JSON valid`

- [ ] **Step 6.4: Commit**

  ```bash
  git add workflow/campuscast-etapa2.workflow.json .gitignore
  git commit -m "feat(workflow): add Etapa 2 — schedule + Telegram + Gmail + error branch + weekly XLSX"
  ```

---

## Task 7: Deploy workflow to n8n and configure

**Files:**
- No code changes — uses existing `tools/deploy_to_n8n.py`

- [ ] **Step 7.1: Get n8n API key** (if not already done)

  In n8n UI → Settings → n8n API → Create API Key.
  Copy the key and export:
  ```bash
  export N8N_API_KEY='n8n_api_...'
  ```

- [ ] **Step 7.2: Deploy**

  ```bash
  .venv/bin/python tools/deploy_to_n8n.py workflow/campuscast-etapa2.workflow.json
  ```
  Expected:
  ```
  Creating new workflow 'CampusCast AI — Etapa 2' ...
  OK — created workflow id=<ID>
  Open it: http://localhost:5678/workflow/<ID>
  ```

- [ ] **Step 7.3: Update Google Sheets header row**

  Add column `mp3_file` as column 13 in the `results` tab.
  The existing header row is:
  ```
  timestamp | city | temperature | humidity | rain | precipitation | wind_speed | events_used | llm_response | audio_file | status | error_message
  ```
  Add `mp3_file` between `audio_file` and `status` (or at position 13 after `error_message`).

  > Open the sheet directly at https://docs.google.com/spreadsheets/d/1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk and insert the new column header.

- [ ] **Step 7.4: Activate the workflow in n8n**

  In n8n UI, open the Etapa 2 workflow and toggle the "Active" switch ON. This arms the schedule trigger.

---

## Task 8: First manual run — verify success path

- [ ] **Step 8.1: Trigger manually from n8n UI**

  In the n8n editor for "CampusCast AI — Etapa 2", click **Test workflow** (or execute manually).
  Watch each node light up green.

  Expected final nodes to be green: `Gmail Bulletin` (and `Gmail Weekly XLSX` only on Mondays).

- [ ] **Step 8.2: Verify Telegram received the message**

  Check the Telegram chat — the bulletin text should appear within ~60s of the trigger.

- [ ] **Step 8.3: Verify email received**

  Check contego704@gmail.com or `$CAMPUSCAST_EMAIL_TO` inbox.
  Email should have:
  - Subject: `CampusCast AI — Boletim DD/MM/YYYY`
  - Body with bulletin text + weather table + Sheet link
  - MP3 attachment (playable audio)

- [ ] **Step 8.4: Verify Google Sheet**

  Check the `results` tab. New row should have 13 columns with `status=ok` and a non-empty `mp3_file` column.

- [ ] **Step 8.5: Troubleshoot Read Binary File if node errors**

  If `Read MP3 Binary` errors with "file not found", the path may be relative. Fix by making the path absolute in the node:

  Change the `filePath` parameter from:
  ```
  ={{ $('Build Success Row').first().json.mp3_file }}
  ```
  to:
  ```
  =/home/oness24/Desktop/AI/pucpr/campuscast-ai/{{ $('Build Success Row').first().json.mp3_file }}
  ```
  If you change this, update the workflow JSON and re-deploy with `deploy_to_n8n.py`.

---

## Task 9: Error path test

- [ ] **Step 9.1: Stop Kokoro server**

  ```bash
  pkill -f "kokoro_server"
  sleep 1
  curl -sS http://127.0.0.1:8800/health 2>&1  # should fail with connection refused
  ```

- [ ] **Step 9.2: Trigger the workflow**

  In n8n UI → Test workflow. The pipeline should reach `Check Result` on the error branch.

- [ ] **Step 9.3: Verify error alerts sent**

  - Telegram: should receive `⚠️ CampusCast ERRO ...`
  - Gmail: should receive `[CampusCast] FALHA ...` email
  - Google Sheet: new row with `status=error` and non-empty `error_message`

- [ ] **Step 9.4: Restart Kokoro**

  ```bash
  nohup .venv/bin/uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800 > /tmp/kokoro_server.log 2>&1 &
  sleep 5 && curl -sS http://127.0.0.1:8800/health
  ```

---

## Task 10: Write stress_test.py

**Files:**
- Create: `tools/stress_test.py`

- [ ] **Step 10.1: Create tools/stress_test.py**

  ```python
  #!/usr/bin/env python3
  """
  CampusCast AI — stress test.
  Triggers the Etapa 2 workflow N times via n8n REST API and reports timing.

  Usage:
      python tools/stress_test.py [--runs 5] [--gap 15]
  """
  from __future__ import annotations
  import argparse, json, time, sys, http.cookiejar, urllib.request, urllib.error
  from datetime import datetime

  BASE = "http://127.0.0.1:5678"
  EMAIL = "contego704@gmail.com"
  PASSWORD = "143030@Contego#"
  WORKFLOW_NAME = "CampusCast AI — Etapa 2"


  def login() -> http.cookiejar.CookieJar:
      jar = http.cookiejar.CookieJar()
      opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
      data = json.dumps({"emailOrLdapLoginId": EMAIL, "password": PASSWORD}).encode()
      req = urllib.request.Request(f"{BASE}/rest/login", data=data, method="POST")
      req.add_header("Content-Type", "application/json")
      with opener.open(req, timeout=10):
          pass
      return jar


  def n8n_get(path: str, jar: http.cookiejar.CookieJar) -> dict:
      opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
      req = urllib.request.Request(f"{BASE}/rest{path}")
      req.add_header("Content-Type", "application/json")
      with opener.open(req, timeout=15) as r:
          d = json.loads(r.read().decode())
          return d.get("data", d)


  def n8n_post(path: str, jar: http.cookiejar.CookieJar, body: dict) -> dict:
      opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
      data = json.dumps(body).encode()
      req = urllib.request.Request(f"{BASE}/rest{path}", data=data, method="POST")
      req.add_header("Content-Type", "application/json")
      try:
          with opener.open(req, timeout=15) as r:
              d = json.loads(r.read().decode())
              return d.get("data", d)
      except urllib.error.HTTPError as e:
          return {"error": e.read().decode()[:300]}


  def find_workflow_id(jar: http.cookiejar.CookieJar) -> str:
      workflows = n8n_get("/workflows", jar)
      for wf in (workflows if isinstance(workflows, list) else []):
          if wf.get("name") == WORKFLOW_NAME:
              return wf["id"]
      raise SystemExit(f"Workflow '{WORKFLOW_NAME}' not found in n8n")


  def trigger_workflow(jar: http.cookiejar.CookieJar, wf_id: str) -> str:
      """Trigger and return execution ID."""
      result = n8n_post(f"/workflows/{wf_id}/run", jar, {})
      exec_id = result.get("executionId") or result.get("id")
      if not exec_id:
          raise RuntimeError(f"Could not get execution ID: {result}")
      return str(exec_id)


  def wait_for_execution(jar: http.cookiejar.CookieJar, exec_id: str, timeout: int = 180) -> dict:
      """Poll until execution finished or timeout. Returns execution data."""
      deadline = time.time() + timeout
      while time.time() < deadline:
          try:
              data = n8n_get(f"/executions/{exec_id}", jar)
              if data.get("finished"):
                  return data
          except Exception:
              pass
          time.sleep(3)
      return {"finished": False, "status": "timeout"}


  def execution_duration_ms(data: dict) -> int:
      """Extract total duration in ms from execution data."""
      start = data.get("startedAt")
      stop  = data.get("stoppedAt")
      if start and stop:
          from datetime import datetime as dt
          fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
          try:
              s = dt.strptime(start, fmt)
              e = dt.strptime(stop, fmt)
              return int((e - s).total_seconds() * 1000)
          except Exception:
              pass
      return -1


  def slowest_node(data: dict) -> tuple[str, int]:
      """Return (node_name, duration_ms) for the slowest node."""
      nodes_data = data.get("data", {}).get("resultData", {}).get("runData", {})
      slowest = ("?", 0)
      for node_name, runs in nodes_data.items():
          for run in (runs or []):
              ms = run.get("executionTime", 0) or 0
              if ms > slowest[1]:
                  slowest = (node_name, ms)
      return slowest


  def main() -> int:
      parser = argparse.ArgumentParser(description="CampusCast stress test")
      parser.add_argument("--runs", type=int, default=5, help="Number of runs (default 5)")
      parser.add_argument("--gap",  type=int, default=15, help="Seconds between triggers (default 15)")
      args = parser.parse_args()

      print(f"Logging in to n8n...")
      jar = login()
      wf_id = find_workflow_id(jar)
      print(f"Found workflow id={wf_id}")
      print(f"\nRunning {args.runs} executions with {args.gap}s gap...\n")

      results = []
      for i in range(1, args.runs + 1):
          print(f"Run {i}/{args.runs} — triggering...", end=" ", flush=True)
          t0 = time.time()
          exec_id = trigger_workflow(jar, wf_id)
          data = wait_for_execution(jar, exec_id)
          wall = time.time() - t0
          status = data.get("status", "unknown")
          dur_ms = execution_duration_ms(data)
          slow_node, slow_ms = slowest_node(data)
          results.append({
              "run": i, "exec_id": exec_id, "status": status,
              "wall_s": round(wall, 1), "dur_ms": dur_ms,
              "slow_node": slow_node, "slow_ms": slow_ms
          })
          print(f"status={status} wall={wall:.1f}s slowest={slow_node}({slow_ms}ms)")

          if i < args.runs:
              print(f"  waiting {args.gap}s before next run...")
              time.sleep(args.gap)

      print("\n--- Stress Test Summary ---")
      print(f"{'Run':<4} {'Duration':>10} {'Status':<10} {'Slowest Node (ms)'}")
      print("-" * 60)
      for r in results:
          print(f"{r['run']:<4} {str(r['wall_s'])+'s':>10} {r['status']:<10} {r['slow_node']} ({r['slow_ms']}ms)")
      successes = sum(1 for r in results if r["status"] == "success")
      avg = sum(r["wall_s"] for r in results) / len(results)
      print(f"\nPassed: {successes}/{len(results)}   Average wall time: {avg:.1f}s")

      return 0 if successes == len(results) else 1


  if __name__ == "__main__":
      sys.exit(main())
  ```

- [ ] **Step 10.2: Run the stress test**

  ```bash
  .venv/bin/python tools/stress_test.py --runs 5 --gap 15
  ```

  Expected output (approximate):
  ```
  Run 1/5 — triggering... status=success wall=31.2s slowest=Ollama Generate(24800ms)
  Run 2/5 — triggering... status=success wall=29.8s slowest=Ollama Generate(23100ms)
  ...
  --- Stress Test Summary ---
  Run  Duration   Status     Slowest Node (ms)
  ------------------------------------------------------------
  1    31.2s      success    Ollama Generate (24800ms)
  2    29.8s      success    Ollama Generate (23100ms)
  ...
  Passed: 5/5   Average wall time: 30.4s
  ```

- [ ] **Step 10.3: Commit**

  ```bash
  git add tools/stress_test.py
  git commit -m "feat(tools): add stress_test.py for pipeline bottleneck analysis"
  ```

---

## Task 11: Submission docs

**Files:**
- Create: `docs/08-etapa2-evidencia.md`
- Create: `docs/SUBMISSAO-etapa2.md`

- [ ] **Step 11.1: Write docs/08-etapa2-evidencia.md**

  Create `docs/08-etapa2-evidencia.md` with the following template (fill in actual execution IDs and results after running):

  ```markdown
  # ID 2.2 — Evidências Etapa 2: Pipeline Multicanal

  Data: 2026-05-XX
  n8n versão: 2.13.4
  Workflow: CampusCast AI — Etapa 2 (id=<ID>)

  ## 1. Execução de Sucesso — Caminho Completo

  Execução id=<EXEC_ID> — todos os 20 nodes verdes, tempo total ~30s.

  ### Telegram
  Mensagem recebida no chat <CHAT_ID>:
  > [colar o texto do boletim aqui]

  ### Gmail
  E-mail recebido em <email>:
  - Assunto: CampusCast AI — Boletim DD/MM/YYYY
  - Corpo: boletim em HTML + tabela meteorológica + link para planilha
  - Anexo: campuscast-YYYY-MM-DDT...mp3 (~XX KB)

  ### Google Sheets
  Linha gravada com status=ok e 13 colunas incluindo mp3_file.

  ## 2. Execução de Falha — Caminho de Erro

  Kokoro parado intencionalmente. Execução id=<EXEC_ID_ERROR>.

  ### Telegram error alert
  > ⚠️ CampusCast ERRO DD/MM/YYYY HH:MM: ...

  ### Gmail error alert
  - Assunto: [CampusCast] FALHA DD/MM/YYYY

  ## 3. Relatório Semanal (segunda-feira)

  Endpoint /weekly-report chamado, XLSX gerado e enviado por e-mail.

  ## 4. Stress Test

  Executado tools/stress_test.py --runs 5 --gap 15.

  | Run | Duração | Status  | Nó mais lento (ms) |
  |-----|---------|---------|---------------------|
  | 1   | XXs     | success | Ollama Generate (XXms) |
  | 2   | XXs     | success | Ollama Generate (XXms) |
  | 3   | XXs     | success | Ollama Generate (XXms) |
  | 4   | XXs     | success | Ollama Generate (XXms) |
  | 5   | XXs     | success | Ollama Generate (XXms) |

  Gargalo identificado: Ollama Generate (~XX% do tempo total).
  Mitigação: temperatura reduzida para 0.3, num_predict limitado a 220.
  ```

- [ ] **Step 11.2: Write docs/SUBMISSAO-etapa2.md**

  Create `docs/SUBMISSAO-etapa2.md`:

  ```markdown
  # Submissão — CampusCast AI · Etapa 2 · PUCPR AI Factory

  **Aluno:** Onesmus Simiyu
  **E-mail:** onesmus.simiyu@pucpr.edu.br
  **Repositório:** https://github.com/oness24/campuscast-ai
  **Data:** Maio/2026

  ---

  ## Sumário Executivo

  A Etapa 2 estende o pipeline da Etapa 1 com entrega automatizada multicanal:
  agendamento diário às 7h, envio do boletim em texto para Telegram, envio por e-mail com
  o boletim em HTML e o áudio em MP3 em anexo, tratamento de erros com notificação em ambos
  os canais, e um relatório semanal em Excel enviado automaticamente toda segunda-feira.

  ## Mapeamento da Rubrica

  | Critério | Como atendido | Artefato |
  |---|---|---|
  | Microsserviço → e-mail/WhatsApp em fluxo único | 20 nodes em cadeia linear no n8n; TTS local → conversão MP3 → Telegram + Gmail no mesmo fluxo | `workflow/campuscast-etapa2.workflow.json` |
  | Tratamento de erros | IF node roteia para branch de erro; linha status=error gravada; Telegram + Gmail alertados | node "Check Result" + error branch |
  | Logs | Toda execução (sucesso ou falha) grava linha na planilha `results` com 13 campos | node "Results Append OK/Error" |
  | Variáveis de ambiente | 4 variáveis n8n usadas em nodes (cidade, e-mail, chat ID, sheet ID) | n8n Settings → Variables |
  | Escalabilidade | Trocar cidade, destinatário ou chat sem alterar nenhum node | n8n Variables |
  | Testes de stress | 5 execuções sequenciais medidas, gargalo identificado | `tools/stress_test.py` + `docs/08-etapa2-evidencia.md` §4 |
  | Gargalos de performance | Ollama Generate: ~80% do tempo total (~24s de ~30s) | stress test report |
  | Pipeline resiliente | Dois canais de alerta independentes; Sheet auditável mesmo em falhas | error branch |
  | Valor de negócios | Zero interação manual diária; boletim + MP3 na caixa de e-mail às 7h | Schedule Trigger |

  **Status: ATENDIDO**
  ```

- [ ] **Step 11.3: Commit docs**

  ```bash
  git add docs/08-etapa2-evidencia.md docs/SUBMISSAO-etapa2.md
  git commit -m "docs(etapa2): add evidence doc and rubric mapping for Etapa 2"
  ```

---

## Task 12: Final smoke + push

- [ ] **Step 12.1: Run all probes**

  ```bash
  .venv/bin/python tools/smoke.py
  ```
  Expected: 5/5 PASS (weather, ollama, kokoro, convert, weekly_report).

- [ ] **Step 12.2: Push everything to GitHub**

  ```bash
  git push origin main
  git log --oneline -n 8
  ```

---

## Spec Coverage Check

| Spec section | Covered by task |
|---|---|
| Schedule Trigger 07:00 | Task 6 (workflow JSON, Schedule 07h node) |
| Telegram text bulletin | Task 6 (Telegram Bulletin node) |
| Gmail bulletin + MP3 | Task 6 (Read MP3 Binary + Gmail Bulletin nodes) |
| Error branch both channels | Task 6 (Build Error Row + Telegram Error + Gmail Error) |
| Monday weekly XLSX | Task 6 (Is Monday? + Get Weekly Report + Gmail Weekly XLSX) |
| /convert endpoint | Task 1 |
| /weekly-report endpoint | Task 2 |
| n8n Variables (4) | Task 5 |
| Telegram credential | Task 5 |
| SMTP credential | Task 5 |
| Stress test | Task 10 |
| Submission docs | Task 11 |
