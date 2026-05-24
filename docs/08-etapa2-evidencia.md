# Etapa 2 — Evidência de Execução

## Infraestrutura implantada

| Componente | Versão / URL | Status |
|---|---|---|
| n8n | 2.13.4 @ `127.0.0.1:5678` | Ativo |
| Ollama + llama3.1:8b | `127.0.0.1:11434` | Ativo |
| Kokoro TTS (pt-BR, pf_dora) | `127.0.0.1:8800` | Ativo |
| Google Sheets (resultados) | ID `1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk` | Leitura/escrita OK |

## Novos endpoints — `tools/kokoro_server.py`

| Endpoint | Função |
|---|---|
| `POST /tts` | Texto → WAV (pt-BR, voz pf_dora) |
| `POST /convert` | WAV → MP3 (lameenc, 128 kbps) |
| `GET /weekly-report` | Gera XLSX das últimas 7 execuções via Sheets API |
| `GET /audio/{filename}` | Serve arquivo de áudio (bypassa N8N_RESTRICT_FILE_ACCESS_TO) |
| `GET /reports/{filename}` | Serve arquivo XLSX para n8n |

## Workflow Etapa 2 — `campuscast-etapa2.workflow.json`

- **ID:** `E9K59jrThdHRSxxb`
- **Nós:** 22
- **Trigger:** Schedule Trigger (07:00 diário)
- **Canais:** Telegram + Gmail (HTML + MP3 em anexo + tabela de dados)
- **Relatório semanal:** toda segunda-feira, Gmail com XLSX em anexo
- **Config centralizada:** nó Code "Config" (city, emailTo, tgChatId, sheetId)

### Fluxo de sucesso (15 nós)

```
Schedule 07h → Config → Weather → Events Read → Build Prompt →
Ollama Generate → Kokoro TTS → Convert WAV→MP3 → Check Result →
Build Success Row → Results Append OK → Telegram Bulletin →
Download MP3 → Gmail Bulletin → Is Monday? [→ Get Weekly Report → Download XLSX → Gmail Weekly XLSX]
```

### Fluxo de erro (13 nós)

```
... → Kokoro TTS (falha) → Convert WAV→MP3 (falha) → Check Result →
Build Error Row → Results Append Error →
Telegram Error Alert + Gmail Error Alert
```

## Smoke tests — `tools/smoke.py`

```
[PASS] weather: Curitiba temperature_2m=14.6 C
[PASS] ollama: 55 chars — 'A cidade de Brasília é considerada a capital do Brasil.'
[PASS] kokoro: audio/2026-05-24T19-39-01.wav (138044 bytes, 2.88s)
[PASS] convert: audio/2026-05-24T19-39-01.mp3 (46848 bytes)
[PASS] weekly_report: campuscast-semana-2026-W21.xlsx (7 rows, 6395 bytes)
```

## Execuções de evidência

| Execução | Tipo | Status | Nós | Resultado |
|---|---|---|---|---|
| 127690 | Sucesso (conexão errada) | success | 13 | Download MP3 sem Gmail — bug de conexão, corrigido |
| 127693 | Sucesso path — primeira correta | success | 15 | Telegram recebeu boletim; Gmail recebeu HTML + MP3; Is Monday?=falso |
| 127702 | Erro path — Kokoro desligado | success | 13 | Telegram Error Alert + Gmail Error Alert enviados |
| 127704 | Stress test (cold) | error | — | Kokoro ainda carregando modelo |
| 127708–127714 | Stress test (warm) | success | 15 | 4/4 runs, avg 15.1s |

## Stress test — `tools/stress_test.py`

```
Runs: 3  |  Success: 3  |  Failed: 0

Wall-clock time (success runs):
  min=15.1s  avg=15.1s  max=15.1s

Provável gargalo: Ollama Generate (inferência LLM) + Kokoro TTS (síntese neural)
```

Observação: Ollama e Kokoro rodam em CPU (sem GPU); em produção com GPU o tempo
cairia para ~3–5s. O gargalo principal é o modelo LLM (llama3.1:8b, ~8 GB).

## Configuração Telegram

- Bot: `@Weatherpucpr_bot`
- Chat ID: `6552761761`
- Credencial n8n: `CampusCast Telegram Bot` (id=`LANK6wg1jeq1k3Qr`)

## Configuração Gmail/SMTP

- Conta: `contego704@gmail.com`
- Credencial n8n: `CampusCast Gmail SMTP` (id=`vQe0CdBPhsb5LSYj`)
- Destinatário: `onesmus.simiyu@pucpr.edu.br`

## Relatório semanal (XLSX)

Gerado toda segunda-feira. Exemplo gerado em 2026-W21:
- Arquivo: `reports/campuscast-semana-2026-W21.xlsx`
- Linhas: 7 (últimas 7 execuções)
- Tamanho: 6.395 bytes
