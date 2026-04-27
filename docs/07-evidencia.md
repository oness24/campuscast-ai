# ID 2.1 — Evidências de Configuração + Roteiro de Demonstração

Este documento captura as evidências exigidas pelo requisito **ID 2.1** (chamadas HTTP em Python, n8n, Ollama e Kokoro rodando localmente) e os artefatos de validação do protótipo completo.

Data de captura: **2026-04-22 e 2026-04-27**
Versão do n8n: **2.13.4 (auto-hospedado)**
Máquina: Linux (Pop!_OS), 31 GB RAM, 16 núcleos, GPU NVIDIA
Python: 3.12.3 em `.venv/`

---

## 1. Open-Meteo (chamada HTTP em Python)

A chamada é feita por `tools/smoke.py` com a biblioteca `requests` (atende diretamente o requisito *"chamadas HTTP em Python"* da rubrica ID 2.1).

```bash
$ .venv/bin/python tools/smoke.py --only weather
[PASS] weather: Curitiba temperature_2m=19.0 C
```

Resposta JSON (primeiros 400 caracteres):

```json
{"latitude":-25.375,"longitude":-49.25,"generationtime_ms":0.113,
 "utc_offset_seconds":-10800,"timezone":"America/Sao_Paulo",
 "timezone_abbreviation":"GMT-3","elevation":920.0,
 "current_units":{"time":"iso8601","interval":"seconds",
   "temperature_2m":"°C","relative_humidity_2m":"%",
   "precipitation":"mm","rain":"mm","weather_code":"wmo code",
   "wind_speed_10m":"km/h"},
 "current":{ ... }}
```

Local da chamada: `tools/smoke.py` → função `probe_weather()`, linhas 50–62.

---

## 2. Ollama (LLM local)

Versão: `ollama version is 0.17.0`
Serviço systemd: ativo
Modelo instalado: `llama3.1:8b` (4.9 GB, quantização Q4_K_M)

### Teste interativo (CLI)

```text
$ ollama run llama3.1:8b "Em uma frase, fale sobre o clima de Curitiba."
O clima da cidade é subtropical úmido e é influenciado pela proximidade
com a Serra do Mar, trazendo chuvas intensas na primavera. Durante o ano,
ocorrem também temperaturas frias, especialmente em julho e agosto,
tornando o inverno um dos períodos mais frios da cidade.
```

### Teste via API HTTP

```bash
$ .venv/bin/python tools/smoke.py --only ollama
[PASS] ollama: 31 chars — 'A capital do Brasil é Brasília.'
```

---

## 3. Kokoro (TTS local)

**Engine:** Kokoro 0.9.2 (pacote Python), PyTorch 2.11.0 com CUDA, NumPy 2.4.4, soundfile 0.13.1.
**Voz:** `pf_dora` (português brasileiro), `lang_code="p"`.

### Teste de qualidade da voz pt-BR

Sintetizamos uma frase pt-BR de teste e validamos audivelmente. Resultado: voz feminina, pt-BR inteligível, sem necessidade de fallback para Piper TTS.

### Servidor local

`tools/kokoro_server.py` é uma fina camada FastAPI que:

- Aceita `POST /tts` com `{ text, voice? }`
- Aplica `strip_markup()` (remove `**`, `*`, `_`, `` ` ``, `#`, `>`, headings, bullets) **antes** de invocar o Kokoro — sem isso, o LLM ocasionalmente injeta markdown que o TTS pronuncia literalmente
- Sintetiza com `KPipeline(lang_code="p")` e voz `pf_dora`
- Grava `audio/<ISO>.wav` (16-bit mono 24 kHz) e devolve `{ audio_file, duration_seconds }`
- Expõe `GET /health` para sondas

### Probe HTTP

```bash
$ .venv/bin/python tools/smoke.py --only kokoro
[PASS] kokoro: audio/2026-04-27T18-38-49.wav (138044 bytes, 2.88s)
```

### Sanidade do servidor

```bash
$ curl -sS http://127.0.0.1:8800/health
{"status":"ok"}
```

---

## 4. n8n (orquestração)

Editor: `http://localhost:5678`
Workflow: **CampusCast AI MVP** (ID `OPL0o46PElOTFv7M`, projeto `Contego NOC`)
JSON exportado: `workflow/campuscast-mvp.workflow.json` (versionado no git)

### Pipeline (8 nodes em cadeia linear)

```text
Manual Trigger
  → Weather              (HTTP GET Open-Meteo)
    → Events Read        (Google Sheets — service account)
      → Build Prompt     (Code, JS — mapa WMO + regras condicionais)
        → Ollama Generate (HTTP POST 127.0.0.1:11434/api/generate)
          → Kokoro TTS    (HTTP POST 127.0.0.1:8800/tts)
            → Build Success Row (Set — 12 campos)
              → Results Append (Google Sheets — service account)
```

O workflow foi implantado e atualizado via REST API (`POST /rest/workflows`, `PATCH /rest/workflows/{id}`), não pela UI manualmente. O script `tools/deploy_to_n8n.py` espelha o padrão de deploy de outro projeto do autor.

---

## 5. Google Sheets

Planilha: **CampusCast AI**
ID: `1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk`
URL: https://docs.google.com/spreadsheets/d/1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk/edit

### Abas

- **`events`** (6 colunas: `date | time | event_name | location | audience | priority`) — populada com 2 eventos do dia atual via Google Sheets API (script Python usando `googleapiclient`).
- **`results`** (12 colunas: `timestamp | city | temperature | humidity | rain | precipitation | wind_speed | events_used | llm_response | audio_file | status | error_message`).

### Autenticação

**Service account** (`campuscast-n8n@campuscast-n8n.iam.gserviceaccount.com`), planilha compartilhada como **Editor**. Credencial JSON local em `credentials/campuscast-n8n.json` (gitignorado).

Credencial no n8n: `Google Sheets — CampusCast` (tipo `googleApi`, ID `xsjRaVzdAvkp6C3F`), criada via REST.

---

## 6. Execução end-to-end (resultados verificados)

Várias execuções foram observadas. Os destaques:

### 6.1 Execução de sucesso (122001) — pós-fortalecimento de prompt

Boletim gerado (72 palavras, ≤120 conforme rubrica):

> Boletim CampusCast para estudantes de Curitiba.
>
> O clima está parcialmente nublado com temperatura de 15.5 °C.
>
> Para aproveitar o tempo, é recomendável estar preparado para condições climáticas estáveis e sem chuva. Não há necessidade de agasalho ou reforço de hidratação por conta da temperatura amena.
>
> Lembre-se dos eventos programados: Workshop: Prototype Demo às 14h no Building A e AI Study Group às 19h no Lab 3.
>
> Sem alertas de risco para hoje.

**Validações:** sem invenção de chuva, sem invenção de eventos, conselho prático coerente com `rain=0` e `temperature_2m=15.5`. Linha gravada na aba `results` com `status=ok`.

### 6.2 Endurecimento do prompt

Após uma execução inicial alucinar guarda-chuva mesmo com `rain=0`, o node `Build Prompt` e o body do `Ollama Generate` foram fortalecidos:

- Booleanos derivados (`is_raining`, `is_hot`, `is_cold`, `is_windy`, `is_stormy`) injetados no prompt como regras condicionais explícitas.
- Temperatura do modelo reduzida para `0.3`, `top_p=0.9`.
- Regras anti-invenção e anti-markdown adicionadas.

### 6.3 Saneamento de markdown no servidor TTS

Mesmo com o prompt explícito, `llama3.1:8b` ocasionalmente injeta `**Bom dia!**`. Sem tratamento, o Kokoro pronuncia os asteriscos. A função `strip_markup()` em `tools/kokoro_server.py` remove esses caracteres **antes** da síntese, garantindo áudio limpo. Validado em execução 122013.

### 6.4 Execução de falha intencional (122003) — caminho de erro

O servidor Kokoro foi propositalmente parado e o workflow disparado. A execução terminou com `status=error` e a falha registrada:

```text
connect ECONNREFUSED 127.0.0.1:8800
```

— exatamente o esperado quando o Kokoro está offline. A falha é capturada no histórico de execuções do n8n (`GET /rest/executions/122003`).

**Nota sobre armazenamento durante falha:** o workflow MVP não tem branch de erro conectado ao Sheets, então uma execução falha não produz linha `status=error` na planilha. O design completo prevê esse branch (ver `docs/superpowers/specs/...-design.md` §7); essa é a evolução planejada para a Etapa 2.

---

## 7. Histórico do Git (até esta evidência)

Versionamento integral do esforço com mensagens de commit no padrão *Conventional Commits*:

```text
1a1ae42 fix(kokoro,prompt): strip markdown server-side + forbid it in prompt
589882b docs(evidence): add prompt-hardening result + failure-path run (exec 122003)
8d859e7 feat(workflow): harden LLM prompt against hallucinations
520a413 docs(readme): rewrite as proper GitHub README with architecture, quick-start, rubric map
ddc462e docs: add ID 2.1 setup evidence + live demo runbook
c1242d8 feat(workflow): add Google Sheets read/append for full pipeline (8 nodes)
549e30b fix(workflow): use 127.0.0.1 instead of localhost (Ollama/Kokoro IPv4-only)
830f376 feat(workflow): extend MVP with Kokoro TTS node (5 nodes total)
02ca809 feat(smoke): add Python HTTP probe for Kokoro TTS server
0da4357 feat(kokoro): add FastAPI server wrapping Kokoro TTS on :8800
528d336 feat(tools): add Python deployer for n8n workflows (mirrors zabbix pattern)
20642c8 feat(workflow): add 4-node MVP workflow for import (Trigger → Weather → Prompt → Ollama)
f96d7f5 feat(smoke): add Python HTTP probe for local Ollama llama3.1:8b
3e78664 feat(smoke): add Python HTTP probe for Open-Meteo weather
e72ad0b chore: import existing project docs and examples
bbd90ad chore: initialize project scaffolding
```

Repositório público: https://github.com/oness24/campuscast-ai

---

## 8. Roteiro de Demonstração ao Vivo (2–4 minutos)

Use isso como roteiro para a apresentação. Tudo abaixo funciona em uma única máquina, com os serviços já rodando.

### Pré-flight (uma vez antes da apresentação)

Abrir **três terminais** lado a lado:

- **Terminal A** — para os smoke tests (vazio)
- **Terminal B** — log do servidor Kokoro (`uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800` rodando; deixar visível)
- **Terminal C** — reprodução de áudio (vazio)

Abrir **duas abas no navegador**:

- **Aba 1** — n8n editor em http://localhost:5678/workflow/OPL0o46PElOTFv7M
- **Aba 2** — Planilha em https://docs.google.com/spreadsheets/d/1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk/edit (na aba `results` para a audiência ver linhas novas aparecendo)

### Passos da demo (com fala sugerida)

1. **Provar que os três serviços estão online** (~20 s)
   - No terminal A:
     ```bash
     cd ~/Desktop/AI/pucpr/campuscast-ai
     source .venv/bin/activate
     python tools/smoke.py
     ```
   - *"Estes três probes Python confirmam que Open-Meteo, Ollama e Kokoro estão respondendo. Todos verdes."*

2. **Mostrar o workflow no n8n** (~15 s)
   - Aba 1, com zoom para mostrar todos os 8 nodes.
   - *"O pipeline é: gatilho manual, API de tempo, leitura da planilha de eventos, code node que monta o prompt, Ollama gerando o boletim em português, Kokoro virando áudio, e gravação na planilha."*

3. **Mostrar os eventos do dia na planilha** (~10 s)
   - Aba 2, alternar para a aba `events`.
   - *"Dois eventos estão registrados para hoje. O workflow vai incluí-los no boletim."*

4. **Executar o pipeline ao vivo** (~45 s)
   - Voltar à aba 1, clicar em **Execute workflow**.
   - Narrar enquanto cada node fica verde: *"Tempo coletado. Eventos lidos. Prompt montado. Ollama está pensando... Boletim gerado. Kokoro sintetizando o áudio... Linha gravada."*
   - Ao final: *"Oito nodes, todos verdes."*

5. **Mostrar a linha nova na planilha** (~20 s)
   - Aba 2, voltar para `results`. A linha nova deve aparecer (atualizar se necessário).
   - *"Esta linha tem o timestamp, os valores climáticos, a lista de eventos que o LLM viu, o boletim em português completo, o caminho do áudio gerado, e status=ok."*
   - Clicar na célula `llm_response` para a audiência ler o texto.

6. **Reproduzir o áudio** (~30 s)
   - No terminal C:
     ```bash
     ls -t ~/Desktop/AI/pucpr/campuscast-ai/audio/*.wav | head -1 | xargs -I {} aplay {}
     ```
   - *"Este é exatamente o arquivo de áudio referenciado na linha que acabamos de ver."*
   - Pausa para a audiência ouvir o boletim em pt-BR.

7. **Encerramento** (~10 s)
   - *"Input → process → output: dados públicos de uma API e uma planilha, combinados pelo n8n, interpretados por um LLM local, transformados em áudio por TTS local e registrados em Google Sheets — tudo rodando nessa única máquina, sem serviços pagos."*

### Tabela de recuperação se algo falhar ao vivo

| Sintoma | Recuperação rápida |
|---|---|
| Node Kokoro vermelho — "ECONNREFUSED" | Terminal B caiu. Reiniciar: `cd ~/Desktop/AI/pucpr/campuscast-ai && source .venv/bin/activate && uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800` |
| Node Ollama vermelho — timeout | GPU pode estar ocupada. Aguardar ou repetir. Primeira chamada após ociosidade leva 10–30 s. |
| Node Google Sheets vermelho | Geralmente autenticação. Recarregar a página do n8n; a credencial permanece. |
| Linha não aparece na planilha | Confirmar que está na aba `results` (não `events`); recarregar o navegador. |

---

## 9. Localização dos Artefatos

| Artefato | Localização |
|---|---|
| Spec de design | `docs/superpowers/specs/2026-04-22-campuscast-ai-etapa1-design.md` |
| Plano de implementação detalhado | `docs/superpowers/plans/2026-04-22-campuscast-ai-etapa1.md` |
| Diagnóstico (PT) | `docs/01-diagnostico.md` |
| Canvas (PT) | `docs/02-canvas-projeto.md` |
| Checklist de ambiente (PT) | `docs/03-checklist-ambiente.md` |
| Plano de implementação (PT) | `docs/04-plano-implementacao.md` |
| Checklist de testes (PT) | `docs/05-checklist-testes.md` |
| Roteiro de apresentação (PT) | `docs/06-roteiro-apresentacao.md` |
| Esta evidência (PT) | `docs/07-evidencia.md` |
| Workflow JSON | `workflow/campuscast-mvp.workflow.json` |
| Smoke tests (Python) | `tools/smoke.py`, `tools/smoke_*.sh` |
| Servidor Kokoro | `tools/kokoro_server.py` |
| Deploy helper | `tools/deploy_to_n8n.py` |
| Áudios gerados | `audio/*.wav` (gitignored) |
| Service account JSON | `credentials/campuscast-n8n.json` (gitignored) |
| Mapeamento da rubrica | `docs/SUBMISSAO.md` |
