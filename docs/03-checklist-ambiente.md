# ID 2.1 — Checklist de Configuração do Ambiente

Use este checklist para configurar e provar o ambiente de automação do CampusCast AI. Cada item gera uma evidência concreta a ser citada em `docs/07-evidencia.md`.

## 1. Testar a API pública (Open-Meteo)

Endpoint:

```text
https://api.open-meteo.com/v1/forecast?latitude=-25.4284&longitude=-49.2733&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m&timezone=America%2FSao_Paulo
```

Pode ser testado em três meios (a rubrica ID 2.1 aceita Python, Postman ou Insomnia):

### Python (recomendado — atende diretamente o requisito)

```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
.venv/bin/python tools/smoke.py --only weather
```

Esperado:

```text
[PASS] weather: Curitiba temperature_2m=15.7 C
```

### curl (alternativa)

```bash
curl -sS "https://api.open-meteo.com/v1/forecast?latitude=-25.4284&longitude=-49.2733&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m&timezone=America/Sao_Paulo" | python3 -m json.tool
```

Esperado: JSON com objeto `current` contendo todos os campos numéricos.

**Evidências a guardar:** trecho do JSON e linha `[PASS]` do smoke probe (já capturadas em `docs/07-evidencia.md` §1).

## 2. Instalar e testar o Ollama

```bash
# Instalação (linux)
curl -fsSL https://ollama.com/install.sh | sh

# Baixar o modelo
ollama pull llama3.1:8b

# Verificar versão e modelos
ollama --version
ollama list
```

Esperado: `ollama version is 0.17.0` (ou superior) e `llama3.1:8b` listado.

### Teste interativo

```bash
ollama run llama3.1:8b "Em uma frase, fale sobre o clima de Curitiba."
```

Esperado: resposta coerente em português, sem alucinações grosseiras.

### Teste via API HTTP local

```bash
.venv/bin/python tools/smoke.py --only ollama
```

Esperado: `[PASS] ollama: <N> chars — '<resposta>'`.

**Evidência:** capturada em `docs/07-evidencia.md` §2.

## 3. Instalar e testar o Kokoro TTS

```bash
# Já incluído em tools/requirements.txt (kokoro==0.9.2)
.venv/bin/pip install -r tools/requirements.txt
```

### Subir o servidor FastAPI

```bash
cd /home/oness24/Desktop/AI/pucpr/campuscast-ai
.venv/bin/uvicorn tools.kokoro_server:app --host 127.0.0.1 --port 8800
```

Aguardar (~10–20 s na primeira inicialização) até ver:

```text
INFO:     Uvicorn running on http://127.0.0.1:8800
```

### Health check

```bash
curl -sS http://127.0.0.1:8800/health
```

Esperado: `{"status":"ok"}`.

### Teste end-to-end

```bash
.venv/bin/python tools/smoke.py --only kokoro
```

Esperado: `[PASS] kokoro: audio/<timestamp>.wav (<bytes>, <duração>s)`.

**Validação manual:** reproduza o arquivo `audio/<timestamp>.wav`. A voz deve ser feminina, em português brasileiro, inteligível.

```bash
aplay audio/$(ls -t audio/*.wav | head -1 | xargs basename)
```

## 4. Instalar e abrir o n8n

Existem três caminhos. Recomenda-se um install global (mais estável que `npx` e mais leve que clonar o repositório fonte).

```bash
# Instalar via npm global
npm install -g n8n

# Ou via npx (sem install)
npx n8n

# Iniciar
n8n
```

Acessar:

```text
http://localhost:5678
```

Esperado: editor n8n abre no navegador. Caso seja primeira execução, criar conta de proprietário (e-mail + senha).

**Evidência:** screenshot do editor com o workflow CampusCast AI MVP carregado, já presente em `docs/07-evidencia.md` §4.

## 5. Preparar o Google Sheets

### 5.1 Criar projeto no Google Cloud

1. Acessar https://console.cloud.google.com/projectcreate
2. Nome do projeto: `campuscast-n8n`
3. Aguardar criação

### 5.2 Habilitar APIs

- Google Sheets API: https://console.cloud.google.com/apis/library/sheets.googleapis.com → Enable
- Google Drive API: https://console.cloud.google.com/apis/library/drive.googleapis.com → Enable

### 5.3 Criar service account

1. https://console.cloud.google.com/iam-admin/serviceaccounts → **+ Create service account**
2. Nome: `campuscast-n8n`
3. Ignorar concessão de papéis (não necessário)
4. Após criar: clicar na conta → aba **Keys** → **Add Key** → **Create new key** → **JSON**
5. Salvar arquivo em `credentials/campuscast-n8n.json` (já gitignorado)

### 5.4 Criar planilha e compartilhar

1. https://sheets.new → renomear para `CampusCast AI`
2. Compartilhar com o e-mail da service account (campo `client_email` do JSON, exemplo `campuscast-n8n@campuscast-n8n.iam.gserviceaccount.com`) com papel **Editor**
3. Copiar o ID da planilha da URL

### 5.5 Criar abas com cabeçalhos

Pode ser feito manualmente ou programaticamente (o projeto já fez via `googleapiclient`):

- Aba `events`: `date | time | event_name | location | audience | priority`
- Aba `results`: `timestamp | city | temperature | humidity | rain | precipitation | wind_speed | events_used | llm_response | audio_file | status | error_message`

## Checklist Final de Evidências

```text
[x] API Open-Meteo testada (Python via tools/smoke.py)
[x] Ollama instalado (versão 0.17.0)
[x] Modelo llama3.1:8b baixado (4.9 GB)
[x] Ollama API HTTP testada (smoke.py)
[x] Kokoro instalado (kokoro 0.9.2 + soundfile + fastapi + uvicorn)
[x] Servidor Kokoro iniciado em 127.0.0.1:8800
[x] Voz pt-BR (pf_dora, lang_code='p') validada audivelmente
[x] n8n acessível em localhost:5678 (instância existente, projeto Contego NOC)
[x] Google Cloud project criado (campuscast-n8n)
[x] APIs Sheets + Drive habilitadas
[x] Service account criada com chave JSON baixada
[x] Planilha CampusCast AI criada e compartilhada com a service account
[x] Abas events e results criadas com cabeçalhos corretos
[x] Probes Python tools/smoke.py executando com 3 [PASS] e exit 0
```

Todos os itens marcados, validados em `docs/07-evidencia.md`.
