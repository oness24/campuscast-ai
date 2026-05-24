# Submissão — Etapa 2: Expansão com Integração Inteligente e Comunicação Automatizada

## Identificação

- **Aluno:** Onesmus Simiyu
- **Curso:** PUCPR — AI Factory
- **Repositório:** `campuscast-ai` (branch `main`)
- **Data:** 2026-05-24

---

## Mapeamento rubrica → artefatos

### 2.1 Chamadas HTTP em Python para serviços externos

| Rubrica | Implementação |
|---|---|
| Chamadas HTTP em Python | `tools/smoke.py` — 5 probes: weather (Open-Meteo), ollama (LLM), kokoro (TTS), convert (WAV→MP3), weekly_report (Sheets→XLSX) |
| Prova de funcionamento | Saída: `[PASS] weather`, `[PASS] ollama`, `[PASS] kokoro`, `[PASS] convert`, `[PASS] weekly_report` |
| Arquivo | `tools/smoke.py` |

### 2.2 Integração multichannel: WhatsApp + Telegram + Email

| Rubrica | Implementação |
|---|---|
| Envio de mensagem WhatsApp | Nó "WhatsApp Bulletin" — Twilio REST API, sandbox `+14155238886` → `+5541988667710` |
| Notificação de erro WhatsApp | Nó "WhatsApp Error Alert" — mesma API, dispara no ramo de erro |
| Envio de mensagem Telegram | Nó "Telegram Bulletin" — boletim diário com texto gerado pelo LLM |
| Notificação de erro Telegram | Nó "Telegram Error Alert" — acionado quando Kokoro TTS ou LLM falha |
| Email HTML com dados | Nó "Gmail Bulletin" — HTML com tabela de dados do dia + link para Sheets |
| Email com anexo MP3 | Nó "Gmail Bulletin" — MP3 da narração anexado via HTTP Request download |
| Notificação de erro Email | Nó "Gmail Error Alert" — HTML com mensagem de erro + link Sheets |
| Arquivo workflow | `workflow/campuscast-etapa2.workflow.json` |

### 2.3 Tratamento de erros com notificação

| Rubrica | Implementação |
|---|---|
| Detecção de falha | `continueOnFail=true` em Ollama Generate, Kokoro TTS, Convert WAV→MP3 |
| Roteamento de erro | Nó "Check Result" (IF): `$json.mp3_file notExists` → ramo de erro |
| Log de erro em Sheets | Nó "Results Append Error" — linha com status=error + mensagem |
| Alerta duplo (Telegram + Gmail) | Nós "Telegram Error Alert" + "Gmail Error Alert" |
| Execução de evidência | exec=127702: status=success, 13 nós no ramo de erro |

### 2.4 Configuração centralizada para escalabilidade

| Rubrica | Implementação |
|---|---|
| Config centralizada | Nó "Config" (Code): `city`, `emailTo`, `tgChatId`, `sheetId` |
| Todos os nós referenciam Config | `$('Config').first().json.city`, `.emailTo`, etc. |
| Substituição de n8n Variables | Community plan não suporta Variables — Config Code node equivalente |

### 2.5 Relatório semanal (Excel/XLSX)

| Rubrica | Implementação |
|---|---|
| Geração de XLSX | Endpoint `GET /weekly-report` — `tools/kokoro_server.py` com openpyxl |
| Fonte de dados | Google Sheets `results!A:M`, últimas 7 execuções |
| Entrega por email | Nó "Gmail Weekly XLSX" com XLSX em anexo |
| Agendamento | Nó "Is Monday?" → ramo semanal executado toda segunda-feira |
| Arquivo de exemplo | `reports/campuscast-semana-2026-W21.xlsx` (7 linhas, 6.395 bytes) |

### 2.6 Teste de carga (stress test) para identificar gargalos

| Rubrica | Implementação |
|---|---|
| Script de stress | `tools/stress_test.py` — N runs (default 5), wall-clock por run, ranking de nós |
| Resultado 3 runs warm | min=15.1s avg=15.1s max=15.1s, 3/3 sucesso |
| Gargalo identificado | Ollama Generate (inferência CPU llama3.1:8b ~11s) + Kokoro TTS (~2s) |
| Melhoria proposta 1 | Trocar llama3.1:8b → gemma2:2b: redução de ~50% sem hardware adicional |
| Melhoria proposta 2 | GPU NVIDIA: inferência LLM de 11s → 0.5s, TTS de 2s → 0.1s |
| Melhoria proposta 3 | Cache diário: skip Ollama se boletim do dia já existe em Sheets |
| Reflexão crítica | `docs/09-analise-desempenho.md` |

### 2.7 Trigger agendado (sem botão manual)

| Rubrica | Implementação |
|---|---|
| Schedule Trigger | Nó "Schedule 07h" — `scheduleTrigger`, hora 7, minuto 0, todos os dias |
| Sem Manual Trigger | Workflow não tem nó de trigger manual — executa apenas via agendamento |

---

## Arquivos principais

```
tools/
  kokoro_server.py      — FastAPI TTS server + /convert + /weekly-report + /audio + /reports
  smoke.py              — 5 probes HTTP em Python
  stress_test.py        — stress test com relatório de gargalos
  setup_n8n_etapa2.py   — provisiona credenciais Telegram + SMTP no n8n

workflow/
  campuscast-etapa2.workflow.json  — workflow Etapa 2 (22 nós)

docs/
  08-etapa2-evidencia.md   — execuções, smoke tests, stress test, saídas

reports/
  campuscast-semana-2026-W21.xlsx  — relatório semanal gerado
```

---

## Execuções de referência para avaliação

| Execução | Cenário | Resultado |
|---|---|---|
| 127693 | Sucesso completo (domingo) | 15 nós, Telegram + Gmail enviados |
| 127702 | Erro path (Kokoro desligado) | 13 nós, Telegram Error + WhatsApp Error + Gmail Error |
| 127760 | Sucesso completo com WhatsApp | 16 nós, Telegram + WhatsApp + Gmail com MP3 |
| 127711–127714 | Stress test 3 runs warm | 3/3 success, avg 15.1s |
