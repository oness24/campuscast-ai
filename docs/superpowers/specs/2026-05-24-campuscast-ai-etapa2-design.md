# CampusCast AI — Etapa 2 Design Spec
**Date:** 2026-05-24
**Author:** Onesmus Simiyu
**Status:** Approved

---

## 1. Context

Etapa 1 delivered a fully local, on-demand pipeline: weather + events → LLM bulletin → TTS audio → Google Sheets audit log. The trigger was manual.

Etapa 2 adds:
- **Automated daily delivery** via Schedule Trigger (07:00 BRT)
- **Multichannel distribution**: Telegram text + Gmail bulletin + MP3 attachment
- **Error handling with notifications**: both channels receive an alert when any node fails
- **Weekly Excel report**: every Monday the successful daily run also emails a 7-day XLSX summary
- **Scalability**: n8n Variables for all configuration, WAV→MP3 conversion, stress test

---

## 2. Architecture — Single Workflow

One n8n workflow (`CampusCast AI — Etapa 2`) replaces the MVP's manual trigger.

```
Schedule Trigger (0 7 * * *)
  → Weather (HTTP GET Open-Meteo)
    → Events Read (Google Sheets — events tab)
      → Build Prompt (Code JS — existing WMO map + conditional rules)
        → Ollama Generate (HTTP POST, timeout=120s, continue-on-fail)
          → Kokoro TTS (HTTP POST, timeout=120s, continue-on-fail)
            → Convert WAV→MP3 (HTTP POST /convert, timeout=30s, continue-on-fail)
              → Check Result (IF: $json.error !== undefined)
                │
                ├─ [TRUE — error branch]
                │   → Build Error Row (Set — status=error)
                │   → Results Append Error (Google Sheets)
                │   → Telegram Error Alert (Telegram node)
                │   → Gmail Error Alert (SMTP node)
                │
                └─ [FALSE — success branch]
                    → Build Success Row (Set — 13 fields, adds mp3_file)
                    → Results Append OK (Google Sheets)
                    → Telegram Bulletin (Telegram node — bulletin text)
                    → Gmail Bulletin (SMTP — text body + MP3 + weather table + Sheet link)
                      → Is Monday? (IF: $now.weekday === 1)
                        └─ [YES]
                           → HTTP GET /weekly-report
                             → Gmail Weekly XLSX (SMTP — XLSX attachment)
```

**Node count:** ~17 nodes (vs 8 in Etapa 1).

---

## 3. New Nodes (detail)

### 3.1 Schedule Trigger
- Cron: `0 7 * * *` (07:00 America/Sao_Paulo)
- n8n timezone set to `America/Sao_Paulo`

### 3.2 Convert WAV→MP3
- `POST http://127.0.0.1:8800/convert`
- Body: `{ "wav_path": "{{ $json.audio_file }}" }`
- Response: `{ "mp3_file": "audio/2026-05-24T07-00-00.mp3", "size_bytes": 25600 }`
- Uses `ffmpeg -i <in.wav> -codec:a libmp3lame -q:a 4 <out.mp3>` via subprocess

### 3.3 Check Result (IF node)
- Condition: `{{ $json.error !== undefined }}` → true = error branch
- Checks the output of the most recent node for the `error` key that n8n injects on continue-on-fail

### 3.4 Telegram Bulletin
- n8n Telegram node (credential: `CampusCast Telegram Bot`)
- Operation: Send Message
- Chat ID: `{{ $vars.CAMPUSCAST_TG_CHAT_ID }}`
- Text: the bulletin text from `$('Ollama Generate').first().json.response` (already stripped by Kokoro server)

### 3.5 Read MP3 Binary (node between Convert and Gmail Bulletin)
- n8n **Read Binary File** node
- File path: `{{ $('Convert WAV→MP3').first().json.mp3_file }}`
- Outputs binary data keyed as `mp3` — consumed by the SMTP attachment field

### 3.6 Gmail Bulletin
- n8n SMTP node (credential: `CampusCast Gmail SMTP`)
- To: `{{ $vars.CAMPUSCAST_EMAIL_TO }}`
- Subject: `CampusCast AI — Boletim {{ $now.toFormat('dd/MM/yyyy') }}`
- Body (HTML): bulletin text + weather data table + Sheet link
- Attachment: binary property `mp3` from the Read MP3 Binary node above

### 3.7 Build Error Row (Set)
Fields: `timestamp`, `city`, `status=error`, `error_message` (from `$json.error.message`), remaining fields empty.

### 3.8 Telegram Error Alert
- Same bot credential
- Text: `⚠️ CampusCast ERRO {{ $now.toISO() }}: {{ $json.error_message }}`

### 3.9 Gmail Error Alert
- Same SMTP credential
- Subject: `[CampusCast] FALHA {{ $now.toFormat('dd/MM/yyyy') }}`
- Body: error details + link to n8n executions log

### 3.10 Is Monday? (IF node)
- Condition: `{{ $now.weekday === 1 }}`
- Only the true branch has a next node

### 3.11 HTTP GET /weekly-report
- `GET http://127.0.0.1:8800/weekly-report`
- Response: `{ "xlsx_base64": "<base64>", "filename": "campuscast-semana-2026-W21.xlsx", "rows": 7 }`

### 3.12 Gmail Weekly XLSX
- SMTP node with base64-decoded attachment
- Subject: `CampusCast AI — Relatório Semanal {{ $now.toFormat('dd/MM/yyyy') }}`

---

## 4. kokoro_server.py — New Endpoints

### 4.1 `POST /convert`
```python
class ConvertRequest(BaseModel):
    wav_path: str

@app.post("/convert")
def convert_wav_to_mp3(req: ConvertRequest) -> dict:
    wav = Path(PROJECT_ROOT) / req.wav_path
    mp3 = wav.with_suffix(".mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav), "-codec:a", "libmp3lame", "-q:a", "4", str(mp3)],
        check=True, capture_output=True
    )
    return {"mp3_file": str(mp3.relative_to(PROJECT_ROOT)), "size_bytes": mp3.stat().st_size}
```

### 4.2 `GET /weekly-report`
```python
@app.get("/weekly-report")
def weekly_report() -> dict:
    # Auth: service account from credentials/campuscast-n8n.json (same JSON used by n8n)
    # Reads last 7 rows from Google Sheets results tab (spreadsheetId from env var)
    # Builds XLSX with openpyxl: one sheet "Semana", columns = Sheet headers
    # Saves to reports/campuscast-semana-<YYYY-WNN>.xlsx
    # Returns {"xlsx_base64": base64.b64encode(xlsx_bytes).decode(), "filename": ..., "rows": N}
```
Deps: `openpyxl`, `google-api-python-client`, `google-auth`.
Google Sheets spreadsheet ID read from `CAMPUSCAST_SHEET_ID` env var (set in server startup or process env).

---

## 5. n8n Variables (Settings → Variables)

| Name | Description | Example value |
|---|---|---|
| `CAMPUSCAST_CITY` | Target city | `Curitiba` |
| `CAMPUSCAST_EMAIL_TO` | Delivery email address | `onesmus.simiyu@pucpr.edu.br` |
| `CAMPUSCAST_TG_CHAT_ID` | Telegram chat/group ID | `-1001234567890` |
| `CAMPUSCAST_SHEET_ID` | Google Sheets spreadsheet ID | `1DQ1hYUaf...` |

---

## 6. New n8n Credentials

| Name | Type | Fields |
|---|---|---|
| `CampusCast Telegram Bot` | Telegram API | `Bot Token` from BotFather |
| `CampusCast Gmail SMTP` | SMTP | host=smtp.gmail.com, port=587, user=contego704@gmail.com, pass=\<16-char app password\> |

---

## 7. Telegram Bot Setup (BotFather — user action required)

1. Open Telegram → search `@BotFather` → `/newbot`
2. Name: `CampusCast AI`, username: `campuscast_pucpr_bot`
3. Copy the token (format: `1234567890:ABCdef...`)
4. Send `/start` to the bot from the target chat/account
5. Get chat ID: `GET https://api.telegram.org/bot<TOKEN>/getUpdates` → look for `message.chat.id`

---

## 8. Google Sheets — results tab change

Add one column: `mp3_file` (column 13). Update the Build Success Row node to include it.
Update header row in the Sheet manually.

---

## 9. Stress Test — `tools/stress_test.py`

- Triggers the Etapa 2 workflow N times (default 5) via n8n REST API
- Waits between triggers (default 15s — allows Ollama to finish before next run)
- Polls `/rest/executions/{id}` until `finished=true`
- Records wall-clock time per run and per-node time from execution data
- Prints summary table:
  ```
  Run  | Duration | Status  | Slowest node (ms)
  1    | 28.4s    | success | Ollama Generate (22100ms)
  2    | 31.1s    | success | Ollama Generate (25300ms)
  ```
- Exits code 1 if any run failed

---

## 10. Files Created / Modified

| File | Action |
|---|---|
| `workflow/campuscast-etapa2.workflow.json` | Create — Etapa 2 daily+weekly workflow |
| `tools/kokoro_server.py` | Modify — add `/convert` and `/weekly-report` endpoints |
| `tools/stress_test.py` | Create — multichannel stress test |
| `tools/requirements.txt` | Modify — add `openpyxl` |
| `docs/08-etapa2-canvas.md` | Create — Etapa 2 SMART objectives and canvas |
| `docs/09-etapa2-evidencia.md` | Create — execution evidence for Etapa 2 |
| `docs/SUBMISSAO-etapa2.md` | Create — rubric mapping for Etapa 2 |

---

## 11. Rubric Mapping

| Rubric item | Implementation | Location |
|---|---|---|
| Encadeia microsserviço → e-mail/WhatsApp em fluxo único | 17-node workflow: TTS → Convert → Telegram → Gmail in one chain | `workflow/campuscast-etapa2.workflow.json` |
| Tratamento de erros | IF node routes error branch; Ollama + Kokoro continue-on-fail; error row + alert on both channels | IF node + error branch |
| Logs e variáveis de ambiente | n8n Variables for all config; execution log in Google Sheets | n8n Settings → Variables |
| Escalabilidade | City, email, chat ID swappable without touching nodes | n8n Variables |
| Testes de stress | `tools/stress_test.py` — 5 runs, per-node timing, bottleneck report | `tools/stress_test.py` |
| Gargalos de performance | Stress test output identifies Ollama Generate as primary bottleneck | stress test report |
| Pipeline resiliente | Dual-channel error alerts; Sheet audit log on every run regardless of outcome | error branch |
| Valor de negócios | Daily audio bulletin + email + Telegram + weekly XLSX report = zero manual effort | full workflow |

---

## 12. Success Criteria

- [ ] Schedule fires at 07:00 and completes all 17 nodes without manual intervention
- [ ] Telegram receives the bulletin text within 60s of trigger
- [ ] Gmail receives bulletin email with MP3 attachment
- [ ] On intentional Kokoro kill: both Telegram + Gmail receive error alert within 60s
- [ ] Every Monday: Gmail receives XLSX with 7-day summary
- [ ] Stress test 5 runs: ≥ 4/5 succeed, average < 45s per run
- [ ] All 4 n8n Variables are used in at least one node expression
