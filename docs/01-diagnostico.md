# ID 1.1 — Diagnóstico do Problema

## Nome do Projeto

**CampusCast AI** — Boletim diário automatizado em áudio para estudantes da PUCPR.

## Contexto

Estudantes universitários precisam, a cada manhã, de um conjunto pequeno de informações práticas antes de irem ao campus: condições do tempo, risco de chuva, deslocamento, lembretes acadêmicos e horários de eventos. Essas informações já existem, mas estão fragmentadas em fontes distintas:

- aplicativos de previsão do tempo (AccuWeather, Climatempo, Google);
- portais e e-mails da universidade;
- grupos de mensagens (WhatsApp, Telegram);
- agendas pessoais e calendários;
- lembretes informais entre colegas.

O custo dessa fragmentação não é tecnológico — todos os dados são públicos ou já estão registrados em algum sistema. O custo é cognitivo: o estudante precisa, manualmente, abrir várias fontes, ler dados crus (números de temperatura, mm de chuva, códigos de tempo) e *interpretá-los* em uma decisão prática ("levo guarda-chuva?", "vou de carro ou ônibus?", "preciso lembrar daquele evento?").

## Problema Real

> **Estudantes deixam de tomar decisões diárias bem informadas porque a informação relevante está espalhada em múltiplos canais e não é automaticamente transformada em uma recomendação prática e acessível.**

Exemplos observáveis no cotidiano:

- O estudante chega molhado no campus porque não checou o radar de chuva.
- Perde uma oficina porque o lembrete ficou em um e-mail não lido.
- Escolhe um espaço de estudo aberto sem consultar a previsão de vento.
- Gasta 5–10 minutos toda manhã abrindo aplicativos diferentes para chegar à mesma decisão repetida.

## Evidências e Fontes de Dados

O protótipo apoia-se em dados objetivos e reproduzíveis:

### Dados meteorológicos (Open-Meteo, API pública e gratuita)

A API `https://api.open-meteo.com/v1/forecast` retorna, para Curitiba (`latitude=-25.4284`, `longitude=-49.2733`), no fuso `America/Sao_Paulo`:

| Campo | Unidade | Significado |
|---|---|---|
| `temperature_2m` | °C | Temperatura do ar a 2 metros |
| `relative_humidity_2m` | % | Umidade relativa |
| `precipitation` | mm | Precipitação acumulada |
| `rain` | mm | Chuva (subconjunto da precipitação) |
| `weather_code` | código WMO | Condição do tempo (0=céu limpo, 3=encoberto, 95=trovoada, etc.) |
| `wind_speed_10m` | km/h | Vento a 10 metros |
| `time` | ISO 8601 | Carimbo da observação |

Esses campos são suficientes para gerar advertências como "leve guarda-chuva", "agasalhe-se", "atenção à trovoada".

### Dados de eventos do campus (Google Sheets)

Uma planilha controlada pela própria equipe de comunicação ou pelos próprios estudantes, com o esquema:

| Campo | Tipo | Exemplo |
|---|---|---|
| `date` | YYYY-MM-DD | `2026-04-22` |
| `time` | HH:MM | `19:00` |
| `event_name` | string | `Workshop: Prototype Demo` |
| `location` | string | `Building A` |
| `audience` | string | `All students` |
| `priority` | enum | `low \| medium \| high` |

### Dados de execução do próprio sistema

O protótipo grava cada execução em uma aba `results` da mesma planilha, com timestamp, status (`ok`/`error`), mensagem de erro quando aplicável e o caminho do arquivo de áudio gerado, permitindo auditoria reproduzível.

## Causas Identificadas

| # | Causa | Justificativa técnica |
|---|---|---|
| 1 | Fragmentação informacional | Cada fonte (clima, eventos, lembretes) usa um canal e um formato próprios; não há agregador no nível do estudante. |
| 2 | Ausência de interpretação automática | Os dados são apresentados na forma crua (números, códigos WMO). Falta uma camada que os traduza em recomendação prática. |
| 3 | Verificação repetitiva e manual | A decisão diária ("hoje preciso de quê?") exige abrir 3–5 ferramentas e correlacioná-las mentalmente. |
| 4 | Acessibilidade limitada | Pessoas com baixa visão, leitura limitada ou que se deslocam (caminhada, transporte) ganham mais com áudio do que com texto. |
| 5 | Inexistência de canal único | Não há um "boletim diário do campus" curto, padronizado e fácil de consumir antes da saída de casa. |

## Consequências Observáveis

| # | Consequência | Impacto |
|---|---|---|
| 1 | Lembretes de eventos perdidos | Queda de participação em palestras, oficinas e atividades extracurriculares. |
| 2 | Mau planejamento climático | Estudantes molhados, sem agasalho ou pegos pelo vento — desconforto e produtividade reduzida no campus. |
| 3 | Tempo desperdiçado | 5–10 minutos diários de checagem manual repetida. Em escala de turma, milhares de horas/semestre. |
| 4 | Acessibilidade prejudicada | Quem precisa de áudio ou tem dificuldade de ler em movimento não tem alternativa institucionalizada. |
| 5 | Decisões tardias sobre transporte | Sem alerta antecipado de chuva forte, alunos saem na hora errada e têm atrasos. |

## Oportunidade de Automação

O problema é altamente automatizável porque segue um ciclo determinístico de **dados → interpretação → mensagem → publicação**:

```text
coleta de dados públicos  →  limpeza e padronização
    →  geração de texto pelo LLM
    →  síntese de áudio (TTS)
    →  publicação e armazenamento
```

Cada etapa tem ferramentas locais e gratuitas:

- **Coleta:** Open-Meteo (HTTP público, sem autenticação).
- **Limpeza:** node *Code* do n8n (JavaScript, mapeamento WMO → frase em português).
- **Geração:** Ollama com `llama3.1:8b` rodando localmente — sem custo por chamada, sem dependência de nuvem paga.
- **TTS:** Kokoro 0.9.2 com voz `pf_dora` em `lang_code="p"` (Brazilian Portuguese) — também 100% local.
- **Publicação:** Google Sheets como sink simples (uma linha por execução).

A oportunidade técnica é grande porque **todos os componentes já existem como software livre** e **o problema é cíclico** (mesma rotina, mesmas fontes, todo dia).

## Solução Proposta

O **CampusCast AI** será um pipeline executado uma vez por dia (manualmente no Etapa 1, automaticamente em etapas futuras) que produz um **boletim curto em português falado**, contendo:

1. Saudação breve.
2. Resumo objetivo do clima atual em Curitiba (1–2 frases).
3. Conselho prático condicional aos dados (ex.: levar guarda-chuva apenas se `rain > 0`).
4. Lembrete dos eventos do dia que estão na planilha.
5. Alerta de risco quando `weather_code` indica trovoada ou precipitação intensa.

Limite rígido: ≤120 palavras. Saída em prosa corrida (sem markdown), pronta para TTS.

## Valor Esperado

| Beneficiário | Valor |
|---|---|
| Estudantes | Decisão diária mais rápida e bem informada; menos esquecimentos; acessibilidade por áudio. |
| Equipe acadêmica | Canal padronizado para reforçar lembretes de eventos importantes. |
| Comunidade do projeto | Modelo reutilizável que pode ser estendido para outras universidades, outros idiomas ou outros canais (e-mail, WhatsApp, Telegram). |
| Aprendizagem | Demonstração concreta do ciclo *input → process → output*, integração via API e oportunidade de automação — o objetivo central da disciplina. |

## Justificativa para a Etapa 1

A Etapa 1 valida o ciclo completo *input → process → output* num cenário enxuto: uma cidade (Curitiba), um modelo (`llama3.1:8b`), uma planilha. Isso prova viabilidade técnica e abre caminho para a Etapa 2 (gatilho agendado, múltiplos canais de entrega, várias cidades).
