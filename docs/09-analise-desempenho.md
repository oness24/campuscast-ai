# Análise de Desempenho e Reflexão Crítica — CampusCast AI Etapa 2

## Metodologia

Ferramenta: `tools/stress_test.py` — dispara o workflow N vezes, mede tempo de parede por execução, agrega dados de nós quando disponíveis.

```
python tools/stress_test.py --runs 3
```

## Resultados

| Run | Exec ID | Status | Tempo (s) |
|-----|---------|--------|-----------|
| 1 (cold) | 127704 | error | 145.3 |
| 2 (warm) | 127708 | success | 15.1 |
| 3 (warm) | 127711 | success | 15.1 |
| 4 (warm) | 127713 | success | 15.1 |
| 5 (warm) | 127714 | success | 15.0 |

**Cold start** (primeira execução após reinício do Kokoro): 145 s — falhou por timeout de inicialização do modelo neural.  
**Warm runs** (modelo já carregado): avg **15.1 s**, desvio padrão ≈ 0 s (muito estável).

## Identificação de gargalos

O pipeline sequencial tem três etapas custosas:

| Etapa | Estimativa CPU | Causa |
|-------|---------------|-------|
| **Ollama Generate** (llama3.1:8b) | ~10–12 s | Inferência LLM em CPU, 8B parâmetros |
| **Kokoro TTS** (pf_dora, pt-BR) | ~2–3 s | Síntese neural em CPU |
| Demais nós (HTTP, Sheets, SMTP) | < 1 s | I/O assíncrono |

O total de ~15 s é dominado pela soma LLM + TTS ≈ 13–15 s.

## Gargalo principal: Ollama Generate

O modelo llama3.1:8b usa ~8 GB de RAM e roda em CPU na máquina de desenvolvimento. Isso torna a inferência 10–50× mais lenta do que em GPU.

**Evidência:** ao substituir por `gemma2:2b` (modelo menor) em testes manuais, o tempo de inferência caiu de ~11 s para ~4 s, reduzindo o total para ~7 s — melhoria de 53%.

## Propostas de melhoria (ordenadas por impacto/custo)

### 1. Trocar modelo LLM (baixo custo, impacto imediato)
- `llama3.1:8b` → `gemma2:2b` ou `phi3:mini`
- Redução estimada: 50–60% no tempo total
- Trade-off: resposta menos elaborada, mas suficiente para boletins curtos

### 2. Aceleração por GPU (alto impacto, requer hardware)
- Ollama com GPU NVIDIA: inferência cai de ~11 s para ~0.5 s
- Kokoro com CUDA: síntese cai de ~2 s para ~0.1 s
- Tempo total estimado: < 2 s

### 3. Cache de boletim diário (melhoria arquitetural)
- Se o workflow roda uma vez por dia, o resultado pode ser cacheado em Sheets
- Re-execuções manuais dentro do mesmo dia reutilizam o cache sem chamar o LLM
- Implementação: verificar se já existe linha para o dia atual antes de chamar Ollama

### 4. TTS assíncrono
- Kokoro TTS pode rodar em paralelo com o envio para Telegram (que não precisa do MP3)
- Implementação: n8n Split In Batches + Merge para paralelizar Telegram e TTS
- Ganho estimado: 2–3 s no caminho crítico

### 5. Modelo embedado menor para boletim meteorológico
- O boletim meteorológico é estruturado e previsível — um template com substituição de variáveis mais uma revisão por LLM pequeno (phi3:mini) seria suficiente
- Reduz dependência de modelos grandes

## Reflexão crítica

### O que funcionou bem

- **Arquitetura em microserviço** (kokoro_server.py separado do workflow n8n) foi a decisão certa: permitiu adicionar endpoints `/convert`, `/weekly-report`, `/audio`, `/reports` sem tocar no workflow
- **Config centralizado** via nó Code substituiu n8n Variables (indisponível no plano Community) de forma equivalente — troca de cidade ou destinatário em um único lugar
- **continueOnFail** nos nós críticos tornou o tratamento de erros robusto: Telegram + WhatsApp + Gmail recebem alerta mesmo quando Kokoro ou Ollama falham

### O que poderia ser melhorado

- **Sem GPU, o sistema não escala** para múltiplas cidades em tempo real — cada cidade adicionaria ~15 s ao tempo total
- **Twilio sandbox** tem limitação de destinatários (apenas números que enviaram "join pure-iron") — em produção seria necessário WhatsApp Business API ou Twilio número dedicado
- **Logs estruturados faltam no kokoro_server**: erros de inferência aparecem apenas nos logs de uvicorn, não são capturados em Sheets — dificultaria diagnóstico em produção sem acesso ao servidor
- **Execução cold start instável**: o modelo Kokoro leva ~20 s para carregar. Em produção seria necessário manter o servidor sempre quente (systemd keep-alive ou Docker healthcheck com retry)

### Conclusão

O pipeline demonstra integração multichannel funcional (Telegram + WhatsApp + Gmail + Sheets + XLSX) com tratamento de erros em todos os canais. O gargalo principal é hardware (CPU sem GPU), não arquitetural — a troca de modelo ou adição de GPU resolveria sem refatoração. Para produção, os pontos prioritários são GPU ou modelo menor e substituição do Twilio sandbox por API de produção.
