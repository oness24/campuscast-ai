# Impacto Ético, Legal e Social — CampusCast AI (ID 3.2)

## 1. Inventário de Dados Pessoais Processados

| Dado | Fonte | Finalidade | Natureza |
|------|-------|------------|----------|
| Endereço de email do destinatário | Config node (hardcoded) | Entrega do boletim | Dado pessoal (Art. 5º, I, LGPD) |
| Número WhatsApp do destinatário | Env var `TWILIO_TO` | Notificação via mensageria | Dado pessoal |
| ID de chat Telegram | Config node | Entrega do boletim | Identificador de conta |
| Dados meteorológicos | Open-Meteo API | Geração do boletim | Dado público, não pessoal |
| Eventos acadêmicos | Google Sheets (entrada manual) | Contexto do boletim | Dado institucional |
| Logs de execução | Google Sheets (results) | Rastreabilidade | Metadado operacional |

**Dados sensíveis (Art. 11, LGPD):** nenhum. O sistema não processa dados de saúde, biometria, origem racial, convicção religiosa ou dado de criança/adolescente.

---

## 2. Base Legal (LGPD — Lei 13.709/2018)

| Atividade | Base Legal | Artigo |
|-----------|------------|--------|
| Envio de email ao destinatário configurado | **Legítimo interesse** do controlador (comunicação institucional) | Art. 7º, IX |
| Envio de WhatsApp via Twilio | **Consentimento explícito** (destinatário enviou "join pure-iron" ao sandbox) | Art. 7º, I |
| Armazenamento de logs em Google Sheets | **Legítimo interesse** (rastreabilidade operacional) | Art. 7º, IX |
| Geração de áudio (TTS) com conteúdo público | Não envolve dado pessoal | — |

### Princípios LGPD Atendidos (Art. 6º)

- **Finalidade**: dados coletados exclusivamente para entrega de comunicação acadêmica.
- **Adequação**: o tratamento é compatível com a finalidade informada ao titular.
- **Necessidade**: apenas email, WhatsApp e Telegram ID são armazenados — sem dados adicionais.
- **Transparência**: o titular recebe mensagem identificando "CampusCast AI — n8n" como remetente.
- **Segurança**: credenciais Twilio armazenadas em variáveis de ambiente (não em código ou banco). Chave de serviço Google em arquivo gitignored.
- **Prevenção**: sistema não expõe dados de terceiros; logs em Sheets são visíveis apenas ao titular da conta Google.

### Direitos do Titular (Art. 18, LGPD)

O titular pode, a qualquer momento:
- Solicitar exclusão de email da lista de destinatários (alteração no Config node).
- Revogar consentimento WhatsApp enviando "stop" ao sandbox Twilio ou bloqueando o número.
- Solicitar acesso aos logs de execução (disponíveis no Google Sheets compartilhado).

---

## 3. Diretrizes de IA Responsável

### 3.1 Transparência Algorítmica

- O boletim gerado por LLM é identificado como "gerado automaticamente" no rodapé de cada mensagem.
- O modelo utilizado (llama3.1:8b via Ollama) é open-source e auditável.
- Nenhuma decisão com efeito jurídico ou significativo sobre pessoas é tomada pelo sistema.

### 3.2 Viés e Equidade

- O conteúdo gerado (boletim climático) é factual e baseado em dados estruturados — baixo risco de viés discriminatório.
- O prompt instrui o modelo a usar linguagem neutra e objetiva.
- **Risco residual**: LLMs podem gerar formulações culturalmente enviesadas em português. Mitigação: o prompt limita a resposta a fatos meteorológicos e lista de eventos.

### 3.3 Responsabilidade e Supervisão Humana (Human-in-the-loop)

- O workflow é configurado por humano (Config node) e executado sob agendamento controlado.
- Alertas de erro são enviados ao administrador via Telegram + Gmail — garantindo supervisão passiva.
- Nenhuma ação irreversível (exclusão, pagamento, acesso a sistemas críticos) é executada automaticamente.

### 3.4 Privacidade por Design (Privacy by Design)

- Credenciais não aparecem em código-fonte (variáveis de ambiente, gitignore).
- Logs não armazenam conteúdo completo das mensagens, apenas metadados (status, timestamp, cidade).
- O endpoint `/whatsapp` atua como proxy — o workflow n8n nunca vê o Account SID ou Auth Token do Twilio.

### 3.5 Impacto Social Positivo

- Democratiza o acesso à informação meteorológica e de eventos para a comunidade acadêmica.
- Reduz carga de trabalho administrativo repetitivo (~25 min/dia → 15 segundos).
- Modelo executável localmente (Ollama + Kokoro) — sem dependência de APIs pagas de LLM, preservando soberania dos dados.

---

## 4. Riscos Identificados e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Vazamento de credencial Twilio | Baixa (env vars, gitignore) | Alto | Rotação semestral; nunca comitar em repositório |
| LLM gera conteúdo incorreto/ofensivo | Baixa (prompt restrito) | Médio | Prompt engineering + revisão manual periódica dos boletins |
| Email/WhatsApp enviado a destinatário errado por erro de config | Baixa (Config node simples) | Médio | Validação do destinatário antes de ativar em produção |
| Cold start falha (Kokoro timeout) | Média (observado em testes) | Baixo | continueOnFail + alerta de erro + retry (Telegram) |
| Dependência de serviço externo (Open-Meteo, Twilio) | Média | Médio | continueOnFail registra erro em Sheets; alerta enviado |

---

## 5. Conformidade com Diretrizes Nacionais e Internacionais

| Diretriz | Atendimento |
|----------|-------------|
| LGPD (Lei 13.709/2018) | ✅ Base legal definida, princípios atendidos, direitos do titular mapeados |
| Marco Civil da Internet (Lei 12.965/2014) | ✅ Sem coleta de dados de navegação; identificação do remetente |
| Estratégia Brasileira de IA (EBIA 2024) | ✅ IA centrada no ser humano, transparente, auditável |
| EU AI Act (referência) | ✅ Sistema de risco mínimo (comunicação automatizada sem decisão sobre pessoas) |
| Princípios de IA da OCDE | ✅ Transparência, responsabilidade, segurança, bem-estar humano |

---

## 6. Conclusão Ética

O CampusCast AI opera dentro dos limites éticos e legais aplicáveis. Os principais pontos de atenção para uma implantação em produção são:

1. **Obter consentimento formal** dos destinatários de email (Art. 7º, I — substituindo legítimo interesse).
2. **Migrar do Twilio sandbox para WhatsApp Business API** — o sandbox exige opt-in manual não escalável.
3. **Publicar Política de Privacidade** descrevendo tratamento de dados dos destinatários.
4. **Nomear DPO** (Encarregado de Proteção de Dados) se o sistema for expandido para toda a universidade.

O projeto demonstra que automação com IA pode ser construída com responsabilidade desde a concepção — não como adaptação posterior.
