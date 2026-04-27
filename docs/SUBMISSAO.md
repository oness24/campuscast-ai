# Submissão — CampusCast AI · Etapa 1 · PUCPR AI Factory

**Aluno:** Onesmus Simiyu
**E-mail:** onesmus.simiyu@pucpr.edu.br
**Repositório:** https://github.com/oness24/campuscast-ai
**Data:** Abril/2026

---

## Sumário Executivo

O **CampusCast AI** é um protótipo funcional de automação inteligente que produz, sob demanda, um boletim diário em áudio para estudantes do campus, em português brasileiro. A pipeline é totalmente local: nenhuma chamada paga a serviços de IA externos. Em uma única máquina com GPU, o sistema:

1. Coleta dados meteorológicos públicos da **API Open-Meteo** (Curitiba).
2. Lê eventos do dia em uma planilha **Google Sheets**.
3. Gera um boletim em pt-BR com **Ollama + llama3.1:8b** (LLM local).
4. Sintetiza áudio com **Kokoro TTS** (também local).
5. Registra o resultado completo (12 colunas, incluindo o caminho do áudio) na planilha.

Tudo orquestrado por um único workflow do **n8n** com 8 nodes em cadeia linear.

---

## Mapeamento da Rubrica

### ID 1.1 — Diagnóstico do Problema

> *"Apresenta uma descrição clara, contextualizada e embasada em dados específicos, e identifica causas, consequências e oportunidades com justificativas técnicas."*

| Critério | Como atendido | Localização |
|---|---|---|
| Descrição clara | §*Contexto* descreve a rotina diária do estudante e a fragmentação informacional | `docs/01-diagnostico.md` §Contexto |
| Contextualização | Cita 5 fontes concretas (apps, e-mail, WhatsApp, calendários, lembretes) | `docs/01-diagnostico.md` §Contexto |
| Dados específicos | Lista todos os 7 campos do Open-Meteo com unidades + 6 campos da planilha de eventos | `docs/01-diagnostico.md` §Evidências e Fontes de Dados |
| 5 causas com justificativa técnica | Tabela de Causas com coluna "Justificativa técnica" | `docs/01-diagnostico.md` §Causas Identificadas |
| 5 consequências mensuráveis | Tabela de Consequências com coluna "Impacto" | `docs/01-diagnostico.md` §Consequências Observáveis |
| Oportunidade com justificativa técnica | Diagrama do ciclo `coleta → limpeza → geração → TTS → publicação`, com ferramenta livre listada para cada etapa | `docs/01-diagnostico.md` §Oportunidade de Automação |

**Status: ATENDIDO**

---

### ID 1.2 — Canvas do Projeto

> *"Define objetivos SMART; estrutura lógica de etapas e entregáveis realistas; antecipa riscos relevantes com estratégias de mitigação bem definidas."*

| Critério | Como atendido | Localização |
|---|---|---|
| Objetivos SMART | 6 objetivos formulados como SMART, cada um com indicador de sucesso mensurável | `docs/02-canvas-projeto.md` §Objetivos SMART |
| Estrutura lógica de etapas | Tabelas separadas para Insumos, Processamento, Saídas | `docs/02-canvas-projeto.md` §Insumos / §Processamento / §Saídas |
| Entregáveis realistas | 13 entregáveis com localização concreta no repositório | `docs/02-canvas-projeto.md` §Entregáveis |
| Riscos relevantes | 8 riscos identificados (técnicos, operacionais e de segurança) | `docs/02-canvas-projeto.md` §Riscos e Estratégias de Mitigação |
| Mitigações bem definidas | Cada risco tem coluna "Mitigação aplicada" descrevendo a ação específica que foi tomada (não apenas teórica) | `docs/02-canvas-projeto.md` §Riscos e Estratégias de Mitigação |
| Critérios de sucesso | 7 critérios verificáveis, todos atualmente cumpridos | `docs/02-canvas-projeto.md` §Critérios de Sucesso |

**Status: ATENDIDO**

---

### ID 2.1 — Configuração do Ambiente de Automação

> *"Configura seu ambiente de automação: realiza chamadas HTTP em Python ou Postman/Insomnia, cria fluxos básicos no n8n e executa o Ollama/Kokoro localmente."*

| Critério | Como atendido | Localização |
|---|---|---|
| Chamadas HTTP em Python | `tools/smoke.py` usa `requests` para Open-Meteo, Ollama, Kokoro — três probes ativas | `tools/smoke.py` |
| Fluxos no n8n | Workflow CampusCast AI MVP com 8 nodes implantado e em execução | `workflow/campuscast-mvp.workflow.json` |
| Ollama local | `llama3.1:8b` instalado, daemon ativo em `127.0.0.1:11434`, validado por probe | `docs/07-evidencia.md` §2 |
| Kokoro local | Servidor FastAPI em `tools/kokoro_server.py`, voz `pf_dora` pt-BR validada audivelmente | `docs/07-evidencia.md` §3 |

**Comando único para verificar:**

```bash
.venv/bin/python tools/smoke.py
```

Saída esperada (e atual):

```text
[PASS] weather: Curitiba temperature_2m=19.0 C
[PASS] ollama: 31 chars — 'A capital do Brasil é Brasília.'
[PASS] kokoro: audio/2026-04-27T18-38-49.wav (138044 bytes, 2.88s)
```

**Status: ATENDIDO**

---

### ID 2.2 — Protótipo Funcional

> *"Protótipo executa todas as etapas: chamada de API, resposta do LLM (Ollama), síntese de voz (Kokoro) e gravação de resultado; integração fluida e funcional."*

| Etapa exigida | Implementação | Evidência |
|---|---|---|
| Chamada de API | Node **Weather**: GET `api.open-meteo.com/v1/forecast` | `workflow/campuscast-mvp.workflow.json` + linha em `results` |
| Resposta do LLM (Ollama) | Node **Ollama Generate**: POST `127.0.0.1:11434/api/generate`, modelo `llama3.1:8b` | coluna `llm_response` da planilha |
| Síntese de voz (Kokoro) | Node **Kokoro TTS**: POST `127.0.0.1:8800/tts`, voz `pf_dora` | coluna `audio_file` + arquivo `audio/<iso>.wav` no disco |
| Gravação de resultado | Node **Results Append**: append-row na aba `results` da planilha | linha completa de 12 colunas |
| Integração fluida e funcional | Execução **122001** terminou com `status=success`, 8/8 nodes verdes em ~30 s | n8n executions log |

**Status: ATENDIDO**

---

## Aprendizagem-chave

> *"Compreender o ciclo completo: input → process → output, conectar sistemas via API e enxergar oportunidades de automação."*

| Aprendizado | Demonstração no projeto |
|---|---|
| Ciclo input → process → output | Workflow linear de 8 nodes onde cada um tem responsabilidade única (input: Weather + Events Read; process: Build Prompt + Ollama + Kokoro; output: Set + Results Append) |
| Conectar sistemas via API | Três integrações HTTP distintas (Open-Meteo público, Ollama local, Kokoro local) + Google Sheets via service account |
| Enxergar oportunidades de automação | `docs/01-diagnostico.md` §Oportunidade de Automação articula explicitamente por que o problema é bom candidato à automação (cíclico, dados públicos, ferramentas livres existentes) |

---

## Como Reproduzir (em qualquer máquina Linux com GPU)

```bash
# 1. Clonar
git clone https://github.com/oness24/campuscast-ai.git
cd campuscast-ai

# 2. Python venv + dependências
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt

# 3. Ollama (uma vez)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b

# 4. Service account do Google em credentials/campuscast-sa.json
# (criar na Google Cloud Console; compartilhar planilha com client_email)

# 5. Subir Kokoro
.venv/bin/uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800

# 6. Verificar
.venv/bin/python tools/smoke.py
# Esperado: 3 [PASS], exit 0

# 7. n8n
npm install -g n8n && n8n
# Importar workflow/campuscast-mvp.workflow.json
# Reapontar credenciais e ID da planilha para o seu ambiente
# Executar
```

---

## Estatísticas do Projeto

| Métrica | Valor |
|---|---|
| Commits | 16+ no `main`, histórico limpo (Conventional Commits) |
| Linhas de código Python (smoke + servidor + deploy) | ~250 |
| Nodes no workflow n8n | 8 |
| Documentos em pt-BR | 7 (`docs/01..07`) + este `SUBMISSAO.md` |
| Dependências Python | 5 pinadas + suas transitivas |
| Modelos de IA usados | `llama3.1:8b` (LLM) + Kokoro 82M (TTS) |
| Custo de execução por dia | R$ 0,00 (apenas custo elétrico) |

---

## Observações Finais

- O repositório está público no GitHub. Pode ser auditado integralmente.
- O histórico do git mostra a evolução real do trabalho (de scaffolding inicial → smoke probes → integração Sheets → fortalecimento de prompt → saneamento de markdown), preservando o aprendizado.
- O projeto está pronto para Etapa 2: gatilho agendado (`Schedule Trigger 0 7 * * *`), entrega multicanal (e-mail, WhatsApp, Telegram), branch de erro com `status=error` na planilha, e suporte a múltiplas cidades via variáveis de ambiente.

**Conclusão: Etapa 1 entregue, todos os critérios da rubrica atendidos.**
