# ID 1.2 — Canvas do Projeto

## Resumo Executivo

| Campo | Descrição |
|---|---|
| **Nome do projeto** | CampusCast AI |
| **Ideia central** | Boletim diário automatizado em áudio para estudantes da PUCPR |
| **Público-alvo** | Estudantes de graduação e pós-graduação, comunidade acadêmica do campus |
| **Contexto de uso** | Rotina matinal antes do deslocamento ao campus |
| **Problema central** | Informação prática (clima + eventos) está fragmentada em múltiplas fontes e não é automaticamente transformada em recomendação |
| **Solução proposta** | Pipeline n8n que coleta dados públicos, gera resposta em português via LLM local, sintetiza áudio via TTS local e armazena evidências em planilha |

## Objetivo Geral

Construir um protótipo funcional que **demonstre o ciclo completo de automação inteligente** — entrada (APIs e planilha), processamento (LLM + TTS) e saída (texto, áudio e registro estruturado) — usando exclusivamente componentes locais e gratuitos.

## Objetivos SMART

Cada objetivo segue o padrão **S** (específico), **M** (mensurável), **A** (atingível), **R** (relevante), **T** (temporal — concluído até o término da Etapa 1, prazo nominal de 2 semanas).

| # | Objetivo SMART | Indicador de sucesso |
|---|---|---|
| 1 | **Coletar dados meteorológicos públicos**: o protótipo fará uma requisição HTTP GET à API Open-Meteo para Curitiba e extrairá os campos `temperature_2m`, `relative_humidity_2m`, `precipitation`, `rain`, `weather_code`, `wind_speed_10m` em até 10 segundos. | Resposta JSON 200 OK com os 6 campos preenchidos; `tools/smoke.py --only weather` retorna `[PASS]`. |
| 2 | **Ler eventos do campus**: o protótipo lerá uma planilha Google Sheets compartilhada via service account e filtrará as linhas cujo campo `date` é igual ao dia atual em fuso `America/Sao_Paulo`. | Aba `events` com pelo menos 1 linha do dia presente nos dados que chegam ao node *Build Prompt*. |
| 3 | **Gerar boletim em português via LLM local**: o protótipo enviará prompt estruturado para Ollama com modelo `llama3.1:8b` e receberá um boletim entre 50 e 200 palavras em português brasileiro. | Resposta com `done=true`, conteúdo em pt-BR, palavras dentro do intervalo, fidelidade aos dados (sem invenção de eventos ou condições não presentes). |
| 4 | **Sintetizar áudio em pt-BR**: o protótipo chamará o servidor Kokoro local (`/tts`) e gravará um arquivo WAV em `audio/<timestamp>.wav` audível e inteligível. | WAV de tamanho > 50 KB, reprodutível via `aplay`/`paplay`, voz feminina pt-BR (`pf_dora`) compreensível. |
| 5 | **Registrar resultado**: o protótipo gravará uma linha completa (12 colunas) na aba `results` da planilha contendo timestamp, dados climáticos, eventos usados, texto do boletim, caminho do áudio e status. | Aba `results` cresce em uma linha por execução bem-sucedida; auditoria por timestamp possível. |
| 6 | **Demonstrar execução end-to-end**: a equipe apresentará pelo menos uma execução manual completa em vivo (≤ 4 minutos), com todos os 8 nodes do n8n verdes e o áudio reproduzido. | Demonstração registrada em `docs/07-evidencia.md` §8 com talk-track e checklist de recuperação. |

## Insumos (Inputs)

| Fonte | Tipo | Acesso |
|---|---|---|
| Open-Meteo API | HTTP GET (público, sem autenticação) | direto pela internet |
| Google Sheets — aba `events` | Sheets API (service account) | credencial JSON local, planilha compartilhada |

## Processamento

| Etapa | Tecnologia | Responsabilidade |
|---|---|---|
| Orquestração | n8n 2.13.x (auto-hospedado, `localhost:5678`) | encadeamento dos 8 nodes do workflow |
| Limpeza e prompt | n8n Code Node (JavaScript) | mapeamento de `weather_code` para frase pt-BR (tabela WMO), filtragem de eventos por data, montagem do prompt com regras condicionais |
| Geração de texto | Ollama 0.17.0 + `llama3.1:8b` (4.9 GB, Q4_K_M) | inferência local, sem custo por chamada |
| Síntese de voz | Kokoro 0.9.2 + voz `pf_dora` (`lang_code="p"`) via FastAPI | conversão texto → WAV 24 kHz mono |
| Armazenamento | Google Sheets — aba `results` | uma linha por execução, 12 colunas |

## Saídas (Outputs)

| Saída | Localização | Formato |
|---|---|---|
| Boletim em texto | Aba `results`, coluna `llm_response` | Português brasileiro, ≤ 120 palavras, sem markdown |
| Arquivo de áudio | `audio/<ISO>.wav` (caminho na coluna `audio_file`) | WAV 16-bit mono 24 kHz |
| Registro auditável | Linha em `results` | timestamp, cidade, temperatura, umidade, chuva, vento, eventos usados, texto, áudio, status, mensagem de erro |
| Status de execução | Coluna `status` da linha | `ok` ou `error` |

## Entregáveis

| # | Entregável | Localização |
|---|---|---|
| 1 | Diagnóstico do problema | `docs/01-diagnostico.md` |
| 2 | Canvas do projeto (este arquivo) | `docs/02-canvas-projeto.md` |
| 3 | Evidência do ambiente | `docs/03-checklist-ambiente.md` + `docs/07-evidencia.md` |
| 4 | Plano de implementação | `docs/04-plano-implementacao.md` + `docs/superpowers/plans/2026-04-22-campuscast-ai-etapa1.md` |
| 5 | Workflow n8n exportado | `workflow/campuscast-mvp.workflow.json` |
| 6 | Servidor Kokoro TTS | `tools/kokoro_server.py` |
| 7 | Probes Python (compliance ID 2.1) | `tools/smoke.py` + wrappers shell |
| 8 | Boletim gerado pelo LLM | aba `results` da planilha CampusCast AI |
| 9 | Arquivo de áudio sintetizado | `audio/2026-04-22T22-24-37.wav` (e demais) |
| 10 | Linha registrada na planilha | linhas 2..n da aba `results` |
| 11 | Checklist de testes | `docs/05-checklist-testes.md` |
| 12 | Roteiro de apresentação | `docs/06-roteiro-apresentacao.md` |
| 13 | Doc de evidência + roteiro de demo ao vivo | `docs/07-evidencia.md` |

## Papéis e Responsabilidades

Por se tratar de projeto individual, todas as responsabilidades concentram-se em **Onesmus Simiyu**, segmentadas por chapéu funcional:

| Chapéu | Responsabilidade |
|---|---|
| Pesquisador | Definir contexto, problema, causas e consequências (`docs/01-diagnostico.md`). |
| Arquiteto | Especificar componentes, fronteiras e fluxo de dados (`docs/superpowers/specs/...-design.md`). |
| Desenvolvedor de automação | Implementar workflow n8n, deploy via REST API, integração com Google Sheets. |
| Desenvolvedor de IA/TTS | Subir Ollama com `llama3.1:8b`, escrever wrapper FastAPI para Kokoro, validar voz pt-BR. |
| Testador / Documentador | Executar smoke probes, capturar evidências, escrever roteiro de demo, manter o repositório. |

## Riscos e Estratégias de Mitigação

| Risco | Probabilidade | Impacto | Mitigação aplicada |
|---|---|---|---|
| Modelo Ollama lento ou indisponível | Baixa | Alto | Adotamos `llama3.1:8b` quantizado (Q4_K_M) que cabe em 5 GB de VRAM; timeout de 120 s no node HTTP; smoke probe `tools/smoke.py --only ollama` valida disponibilidade antes da execução real. |
| Configuração do Kokoro difícil em outras máquinas | Média | Médio | Encapsulamos em FastAPI (`tools/kokoro_server.py`), com `requirements.txt` versionado. Fallback documentado: Piper TTS com voz `pt_BR-faber-medium` se Kokoro falhar. |
| Autenticação Google Sheets falhar | Média | Alto | Optamos por **service account** (não OAuth de usuário) — sem fluxo de consentimento, sem expiração de refresh token. Credencial JSON local, gitignorada. Probe direto via `googleapiclient` valida acesso antes do n8n. |
| API Open-Meteo retorna formato inesperado | Baixa | Médio | Code node valida `temperature_2m` numérico antes de prosseguir; em caso de falha, error branch (planejada para Etapa 2) registraria `status=error`. |
| LLM inventa eventos ou condições | Alta | Alto | Resolvido com **prompt rígido**: regras de conteúdo derivadas de booleanos (`is_raining`, `is_hot`, ...) injetadas no prompt; temperatura do modelo reduzida para 0.3; instrução explícita de "fonte única da verdade". Validação observada em execuções 122001 e 122013. |
| LLM produz markdown que TTS lê literalmente | Alta (observada) | Médio | Resolvido com **sanitização defensiva** em `tools/kokoro_server.py` (`strip_markup()`); a regex remove `*`, `_`, `` ` ``, `#`, `>`, headings, bullets antes da síntese. |
| Resolução `localhost` → IPv6 quebra chamada IPv4-only | Alta (observada) | Alto | Resolvido fixando `127.0.0.1` em todas as URLs internas (Ollama e Kokoro), evitando ECONNREFUSED em sistemas que resolvem `localhost` para `::1`. |
| Vazamento da chave do service account | Baixa | Crítico | `credentials/*.json` em `.gitignore`; chave nunca committada; recomendação de rotação periódica. |

## Critérios de Sucesso

A Etapa 1 será considerada concluída com sucesso quando, simultaneamente:

1. `python tools/smoke.py` retornar exit code 0 (todos os três probes verdes).
2. Uma execução manual do workflow no n8n terminar com `status=success` em ≤ 60 segundos.
3. O arquivo WAV produzido for audivelmente inteligível em português brasileiro.
4. A aba `results` da planilha contiver pelo menos uma linha com todas as 12 colunas preenchidas e `status=ok`.
5. Pelo menos uma execução intencional com falha (Kokoro desligado) terminar com `status=error` e a mensagem de erro for capturada (em log do n8n ou em linha de erro na planilha quando o branch de erro estiver implantado).
6. A documentação (`docs/01..07`) estiver completa e em português.
7. O repositório estiver versionado em git e publicado no GitHub com histórico limpo.

**Status atual: todos os 7 critérios atendidos** (verificado nas execuções 122001 success e 122003 error).
