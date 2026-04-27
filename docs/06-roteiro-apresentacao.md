# Roteiro de Apresentação — Etapa 1

Use este roteiro como base para uma apresentação de **2 a 4 minutos** explicando o protótipo CampusCast AI.

## Abertura (~20 segundos)

Olá. Nosso projeto chama-se **CampusCast AI** — um protótipo de automação inteligente que produz, todos os dias, um boletim curto em áudio para estudantes do nosso campus, em português, totalmente gerado e sintetizado em uma única máquina local, sem depender de nenhum serviço pago de IA.

## Problema e Oportunidade (~30 segundos)

Estudantes precisam, antes de sair de casa, de um conjunto pequeno de informações: o tempo, o risco de chuva, e os eventos do dia. Esses dados existem, mas estão espalhados — em apps de previsão, em e-mails da universidade, em grupos de WhatsApp, em calendários. O problema não é a falta de informação; é o esforço cognitivo de juntar tudo manualmente toda manhã.

Isso é uma oportunidade clara de automação porque o processo é cíclico e determinístico: coletar dados, interpretar, gerar uma mensagem, publicar. Cada etapa tem uma ferramenta livre disponível.

## Solução (~30 segundos)

O CampusCast AI orquestra essa cadeia em um único workflow do **n8n** com 8 nodes:

1. Coleta a previsão atual de Curitiba na API pública **Open-Meteo**.
2. Lê os eventos do dia em uma planilha **Google Sheets**.
3. Em um node Code, monta um prompt rígido em português, com regras condicionais derivadas dos próprios dados — por exemplo, *só* mencionar guarda-chuva se `rain > 0`.
4. Envia o prompt ao **Ollama** rodando localmente com `llama3.1:8b`, que produz um boletim de até 120 palavras.
5. Manda o texto para o **Kokoro TTS**, também local, que gera um arquivo de áudio `.wav` na voz `pf_dora` (português brasileiro).
6. Grava uma linha de auditoria na aba `results` da planilha — com timestamp, dados climáticos, eventos usados, texto do boletim, caminho do áudio e status.

## Pipeline Técnico (~20 segundos)

```text
Manual Trigger
    → HTTP Open-Meteo
        → Google Sheets (events)
            → Code (prompt + WMO map)
                → Ollama (llama3.1:8b)
                    → Kokoro TTS (audio/<iso>.wav)
                        → Set (12 campos)
                            → Google Sheets (results)
```

Esse fluxo demonstra exatamente o ciclo exigido pela disciplina: **input → process → output**.

## Resultado Esperado (~30 segundos)

A saída final é um boletim curto em texto e em áudio. Por exemplo, em uma execução real desta semana, o sistema produziu:

> "Bom dia! Está parcialmente nublado com 15.5 graus em Curitiba. Não há chuva, temperatura amena, vento fraco. Lembre-se dos eventos: Workshop de Protótipo às 14h no prédio A e AI Study Group às 19h no Lab 3. Sem alertas de risco para hoje."

Audio reproduzido ao vivo no momento da demonstração.

## Decisões Técnicas Notáveis (~30 segundos)

Três decisões merecem destaque:

1. **Service account do Google em vez de OAuth de usuário** — sem fluxo de consentimento, sem expiração de refresh token. A credencial é uma chave JSON local, gitignorada.
2. **Sanitização defensiva no servidor TTS** — o LLM ocasionalmente injeta markdown como `**Bom dia!**`. Sem tratamento, o Kokoro pronunciaria os asteriscos. O servidor `tools/kokoro_server.py` aplica `strip_markup()` antes da síntese.
3. **`127.0.0.1` em vez de `localhost`** — Ollama e Kokoro escutam apenas em IPv4. Em sistemas que resolvem `localhost` para IPv6 primeiro, o resultado é `ECONNREFUSED`. Fixar IPv4 elimina a classe inteira do problema.

## Valor (~20 segundos)

O protótipo transforma dados brutos em uma recomendação prática e acessível. Reduz checagem manual diária. Facilita acessibilidade por áudio. Cria uma base reutilizável para canais futuros — e-mail, WhatsApp, Telegram — sem trocar de tecnologia.

## Próximos Passos (~20 segundos)

Na Etapa 2, este mesmo pipeline será automatizado por um *Schedule Trigger* (rodando às 7h todo dia) e estendido para entregar o boletim por canais como e-mail, WhatsApp Cloud API e Telegram. Vamos adicionar um branch de erro que escreve `status=error` na planilha em caso de falha, métricas de qualidade (taxa de aderência ao limite de palavras, fidelidade aos dados) e, eventualmente, suporte a múltiplas cidades.

## Encerramento (~10 segundos)

O CampusCast AI demonstra, em uma única máquina, todo o ciclo de uma fábrica de IA: API pública como entrada, LLM e TTS locais como processamento, planilha e arquivo de áudio como saída — auditável, replicável, e sem custo recorrente. Obrigado.

---

## Apêndice — Resposta a Perguntas Comuns

| Pergunta | Resposta |
|---|---|
| "Por que llama3.1:8b e não um modelo maior/menor?" | 8B é o ponto-doce: cabe em 5 GB de VRAM, gera português decente, e responde em 5–30 s. Modelos menores (3B) hesitam em fluência; maiores (70B) não cabem na máquina e são lentos. |
| "Por que Kokoro e não outro TTS?" | Kokoro 82M é leve, suporta nativamente português brasileiro com a voz `pf_dora`, e roda em GPU. Plano B documentado: Piper TTS com voz `pt_BR-faber-medium`. |
| "E se a API Open-Meteo cair?" | Pipeline timeout em 10 s. Em produção, branch de erro registraria `status=error` (planejado para Etapa 2). |
| "Por que armazenar em Google Sheets e não em banco?" | Para um protótipo de Etapa 1 com 1 execução/dia, planilha é mais simples para auditoria humana. SQLite/Postgres é evolução natural quando o volume crescer. |
| "Quanto custa rodar isso?" | Zero por execução. Open-Meteo é gratuito; Ollama, Kokoro e n8n self-hosted não cobram. Apenas custo elétrico da máquina. |
