# ID 2.2 — Plano de Implementação do Protótipo

Este documento descreve, passo a passo, como o protótipo CampusCast AI foi construído. Para o plano detalhado de execução com tarefas individuais e comandos exatos, consulte `docs/superpowers/plans/2026-04-22-campuscast-ai-etapa1.md`.

## Workflow Final

```text
[1] When clicking 'Execute workflow'   (Manual Trigger)
        ↓
[2] Weather                              (HTTP GET Open-Meteo)
        ↓
[3] Events Read                          (Google Sheets — service account, aba 'events')
        ↓
[4] Build Prompt                         (Code node JS — mapeamento WMO + filtro de data + montagem do prompt)
        ↓
[5] Ollama Generate                      (HTTP POST 127.0.0.1:11434/api/generate, llama3.1:8b)
        ↓
[6] Kokoro TTS                           (HTTP POST 127.0.0.1:8800/tts → audio/<iso>.wav)
        ↓
[7] Build Success Row                    (Set node — 12 campos)
        ↓
[8] Results Append                       (Google Sheets — service account, aba 'results')
```

## Etapa 1 — Trigger Manual

**Ferramenta:** n8n.

**Por quê:** o gatilho manual permite executar o pipeline sob demanda durante desenvolvimento e demonstração. A migração para *Schedule Trigger* (`0 7 * * *` para 07:00 diariamente) é trabalho da Etapa 2.

**Resultado:** clicar em "Execute workflow" inicia toda a cadeia.

## Etapa 2 — Coletar Dados de Tempo

**Ferramenta:** n8n HTTP Request node.

**Configuração:**

```text
Method: GET
URL: https://api.open-meteo.com/v1/forecast
Send Query Parameters: ON
  latitude=-25.4284
  longitude=-49.2733
  current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m
  timezone=America/Sao_Paulo
```

**Decisão de design:** usar parâmetros de query separados (em vez de URL longa) evitou um bug de duplicação que ocorre quando o n8n insere parâmetros via dois canais simultaneamente.

**Resultado:** JSON com objeto `current` contendo 6 campos numéricos de meteorologia.

## Etapa 3 — Ler Eventos do Campus

**Ferramenta:** node `n8n-nodes-base.googleSheets` v4.5.

**Configuração:**

- Authentication: `serviceAccount`
- Credential: `Google Sheets — CampusCast` (criada via REST API, ID `xsjRaVzdAvkp6C3F`)
- Resource: `sheet`
- Operation: `read`
- Document ID: `1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk`
- Sheet name: `events`

**Decisão de design:** *service account* preferida sobre OAuth2 de usuário — não há fluxo de consentimento, não há expiração de refresh token, e a credencial é uma única chave JSON local.

**Resultado:** array de itens, um por linha da aba `events` (ignorando o cabeçalho).

## Etapa 4 — Preparar os Dados (Build Prompt)

**Ferramenta:** n8n Code node (JavaScript).

**Responsabilidades do node:**

1. Recuperar o objeto `current` da resposta do node Weather.
2. Traduzir o `weather_code` (WMO) para uma frase em português via tabela hardcoded:

   | Código | Frase |
   |---|---|
   | 0 | céu limpo |
   | 1, 2 | parcialmente nublado |
   | 3 | céu encoberto |
   | 45, 48 | neblina |
   | 51, 53, 55 | garoa |
   | 61, 63, 65 | chuva fraca/moderada/forte |
   | 66, 67 | chuva congelante |
   | 71, 73, 75 | neve |
   | 80, 81, 82 | pancadas de chuva |
   | 95, 96, 99 | trovoada |

3. Calcular booleanos derivados (`is_raining`, `is_hot`, `is_cold`, `is_windy`, `is_stormy`) para alimentar regras condicionais no prompt.
4. Filtrar eventos pelo dia atual em fuso `America/Sao_Paulo`.
5. Renderizar a lista de eventos como string única (`- date hora event (location)\n…`) ou `Nenhum evento registrado hoje.`.
6. Compor um prompt rígido contendo:
   - DADOS (fonte única da verdade)
   - EVENTOS DO CAMPUS HOJE
   - REGRAS DE CONTEÚDO (derivadas dos booleanos — ex.: `NÃO há chuva. NÃO mencione guarda-chuva, chuva ou proteção contra chuva.`)
   - ESTRUTURA (5 itens obrigatórios)
   - REGRAS GLOBAIS (≤120 palavras, sem markdown, sem invenções)

**Resultado:** um item de saída com `{ payload: {...}, prompt: "<texto>" }`.

## Etapa 5 — Gerar o Boletim (Ollama)

**Ferramenta:** n8n HTTP Request node.

**Configuração:**

```text
Method: POST
URL: http://127.0.0.1:11434/api/generate
Send Body: ON
Content Type: application/json
Body:
{
  "model": "llama3.1:8b",
  "prompt": {{ JSON.stringify($json.prompt) }},
  "stream": false,
  "options": {
    "temperature": 0.3,
    "top_p": 0.9,
    "num_predict": 220
  }
}
Timeout: 120000 ms
```

**Decisão de design:** `127.0.0.1` em vez de `localhost` evita o problema de resolução IPv6 (`::1`) em sistemas onde o Ollama escuta apenas em IPv4. Temperatura baixa (0.3) torna a geração determinística e reduz invenções.

**Resultado:** JSON `{ "response": "<boletim>", "done": true, ... }`.

## Etapa 6 — Sintetizar o Áudio (Kokoro)

**Ferramenta:** n8n HTTP Request node + servidor FastAPI local (`tools/kokoro_server.py`).

**Configuração do node n8n:**

```text
Method: POST
URL: http://127.0.0.1:8800/tts
Body:
{ "text": {{ JSON.stringify($json.response) }} }
Timeout: 120000 ms
```

**Servidor Kokoro:** O wrapper FastAPI:

1. Aceita `{ text, voice? }` em POST `/tts`
2. Aplica `strip_markup()` para remover `**bold**`, `*italic*`, `# headings`, `> blockquotes`, bullets e qualquer caractere markdown residual — porque Kokoro pronunciaria literalmente caracteres como `*`
3. Sintetiza com `KPipeline(lang_code="p")` e voz `pf_dora`
4. Grava WAV em `audio/<ISO>.wav` (16-bit mono 24 kHz)
5. Retorna `{ audio_file, duration_seconds }`

**Decisão de design:** sanitização defensiva no servidor (não apenas no prompt). Mesmo com instrução explícita "PROIBIDO asteriscos", o `llama3.1:8b` ocasionalmente injeta markdown — então a defesa final é remover esses caracteres antes da síntese.

**Resultado:** arquivo `.wav` no disco e referência no JSON de resposta.

## Etapa 7 — Montar a Linha de Resultado (Set Node)

**Ferramenta:** n8n Set node v3.4.

**Campos compostos** (12 ao total, casando o esquema da aba `results`):

| Campo | Origem |
|---|---|
| `timestamp` | `={{ $now.toISO() }}` |
| `city` | constante `Curitiba` |
| `temperature, humidity, rain, precipitation, wind_speed` | `$('Build Prompt').first().json.payload.<campo>` |
| `events_used` | `payload.events_list` (mesma string entregue ao LLM) |
| `llm_response` | `$('Ollama Generate').first().json.response` |
| `audio_file` | `$json.audio_file` (do Kokoro TTS) |
| `status` | `ok` |
| `error_message` | string vazia |

**Decisão de design:** `events_used` armazenado como a string já renderizada e não como JSON cru — facilita auditoria de "qual lista de eventos o LLM viu?" diretamente na célula da planilha.

## Etapa 8 — Gravar Resultado (Google Sheets Append)

**Ferramenta:** node `n8n-nodes-base.googleSheets` v4.5.

**Configuração:**

- Operation: `append`
- Sheet: `results`
- Mapping mode: `autoMapInputData` (mapeia automaticamente pelos nomes de campo do Set node)

**Resultado:** uma nova linha na planilha; a planilha cresce em uma linha por execução bem-sucedida.

## Etapa 9 — Exportar Evidências

Gravar para inclusão na apresentação:

- Screenshot do workflow no n8n com todos os 8 nodes verdes
- Captura de tela da aba `results` mostrando linha bem-sucedida
- Arquivo de áudio `audio/<timestamp>.wav` reproduzível
- Output do `python tools/smoke.py` (3 PASS)
- Histórico de commits do git (`git log --oneline`)

**Localização das evidências:** `docs/07-evidencia.md`.

## Etapa 10 (Etapa 2 — Fora de Escopo)

Itens explicitamente diferidos para após a Etapa 1:

- Schedule Trigger diário
- Branch de erro que escreve `status=error` na planilha em caso de falha (atualmente capturado apenas no log de execução do n8n)
- Entrega multicanal: e-mail, WhatsApp Cloud API, Telegram
- Suporte a múltiplas cidades via variáveis de ambiente
- Métricas de qualidade (palavras-por-bulletin, fidelidade ao dado)

## Resumo de Decisões Técnicas

| Decisão | Justificativa |
|---|---|
| `127.0.0.1` em vez de `localhost` | Ollama e Kokoro escutam apenas em IPv4; resolução IPv6 daria ECONNREFUSED |
| Temperatura 0.3 no Ollama | Reduz alucinações e mantém o boletim previsível |
| Service account em vez de OAuth de usuário | Sem fluxo de consentimento, sem expiração |
| `strip_markup()` no servidor TTS | Defesa final contra markdown que o LLM teima em produzir |
| Lista de eventos como string única no prompt e na planilha | Auditoria humana imediata: a célula `events_used` mostra exatamente o que o LLM leu |
| Workflow linear sem error branch (na Etapa 1) | Simplicidade; falhas são capturadas no log de execução do n8n; branch de erro fica para Etapa 2 |
