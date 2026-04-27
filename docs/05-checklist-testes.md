# Checklist de Testes — Etapa 1

Use este checklist antes de apresentar a Etapa 1. Cada item tem uma forma clara de verificação e gera uma evidência citável em `docs/07-evidencia.md`.

## Testes de Componentes

```text
[x] API Open-Meteo retorna JSON válido
[x] Campos meteorológicos presentes: temperature_2m, relative_humidity_2m, precipitation, rain, weather_code, wind_speed_10m
[x] Aba 'events' da planilha contém pelo menos 1 linha do dia atual
[x] Ollama está rodando localmente (systemd service ativa)
[x] Modelo llama3.1:8b responde a um prompt simples
[x] API HTTP do Ollama (porta 11434) retorna JSON com campo 'response'
[x] Servidor Kokoro está rodando (porta 8800, /health → {"status":"ok"})
[x] Endpoint /tts do Kokoro recebe texto e devolve audio_file + duration_seconds
[x] Aba 'results' da planilha está pronta com cabeçalho de 12 colunas
[x] Sanitização strip_markup() do servidor remove asteriscos antes da síntese
```

## Testes de Workflow (n8n)

```text
[x] Workflow inicia ao clicar em Execute workflow
[x] Node Weather recebe dados climáticos (temperature, humidity, rain, etc.)
[x] Node Events Read recebe os eventos da planilha
[x] Node Build Prompt produz objeto com payload e prompt
[x] Prompt enviado ao Ollama contém TODAS as regras condicionais derivadas dos booleanos
[x] Node Ollama Generate retorna boletim entre 50 e 200 palavras
[x] Node Kokoro TTS gera arquivo .wav em audio/
[x] Node Build Success Row produz linha com 12 campos
[x] Node Results Append insere linha na aba 'results' da planilha
[x] Linha registrada contém todos os 12 campos (sem nulos exceto error_message=='')
```

## Testes de Qualidade (saída)

```text
[x] Boletim final tem ≤ 120 palavras (verificado em execução 122001: 72 palavras)
[x] Boletim é compreensível em português brasileiro (revisão humana)
[x] Boletim NÃO inventa eventos (audit comparando llm_response com events_used)
[x] Boletim NÃO recomenda guarda-chuva quando rain=0 (verificado pós-hardening em exec 122001)
[x] Boletim inclui conselho prático apenas quando justificado pelos dados
[x] Boletim só emite alerta de risco quando weather_code indica trovoada
[x] Áudio gerado é audivelmente inteligível (revisão humana)
[x] Áudio NÃO pronuncia caracteres markdown (verificado em exec 122013 pós-strip_markup)
[x] Linha gravada inclui timestamp em formato ISO 8601
[x] Linha gravada inclui status=='ok' em execução bem-sucedida
```

## Teste de Falha (caminho de erro)

```text
[x] Pipeline detecta serviço Kokoro indisponível (testado em exec 122003)
[x] Mensagem de erro inclui causa identificável (ECONNREFUSED 127.0.0.1:8800)
[x] Status da execução no n8n marca 'error'
[ ] (Etapa 2) Linha com status=error é adicionada na planilha — branch de erro será implantado
```

## Teste de Demonstração

A demonstração é considerada bem-sucedida quando exibe:

```text
[x] Smoke probes (Python) → 3 PASS, exit 0
[x] Workflow no n8n com todos os 8 nodes verdes em ≤ 60s
[x] Linha nova aparecendo na aba 'results' da planilha
[x] Arquivo WAV recém-criado, reproduzível em alto-falante/headset
[x] Bulletin lido em pt-BR sem caracteres especiais audíveis
```

## Comandos de Verificação Rápida

Antes da apresentação, executar:

```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
source .venv/bin/activate

# 1. Probes externos
python tools/smoke.py

# 2. Confirmar serviços de pé
curl -sS http://127.0.0.1:11434/api/tags | grep llama3.1
curl -sS http://127.0.0.1:8800/health

# 3. Sanidade do git
git status
git log --oneline -n 5
```

Esperado: smoke 3/3 PASS, llama3.1:8b listado, kokoro {"status":"ok"}, working tree clean, commits visíveis.
