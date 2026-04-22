# ID 2.1 - Environment Setup Checklist

Use this checklist to configure and prove the automation environment.

## 1. Test the Public API

Open this URL in a browser, Postman, Insomnia, or Python:

```text
https://api.open-meteo.com/v1/forecast?latitude=-25.4284&longitude=-49.2733&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m&timezone=America%2FSao_Paulo
```

Expected result:

- JSON response
- current weather data
- fields such as temperature, humidity, rain, precipitation, and wind speed

Evidence to save:

- screenshot of the response
- copied JSON sample
- short note explaining that the API works

## 2. Install and Test Ollama

After installing Ollama, download a model:

```bash
ollama pull llama3.2
```

Test the model:

```bash
ollama run llama3.2
```

Then test the local HTTP API:

```bash
curl http://localhost:11434/api/generate \
  -d '{
    "model": "llama3.2",
    "prompt": "Create a short campus weather recommendation for students.",
    "stream": false
  }'
```

Expected result:

- JSON response from Ollama
- generated text in the `response` field

## 3. Install and Test Kokoro

The exact command depends on the Kokoro package or server you use.

The important requirement is:

- Kokoro must receive text
- Kokoro must generate an audio file
- n8n must be able to call Kokoro directly or indirectly

Beginner-friendly test:

```text
"Bom dia. Este e um teste do CampusCast AI."
```

Expected result:

- one audio file generated
- file can be played locally

## 4. Install and Open n8n

Common local option:

```bash
npx n8n
```

Alternative with Docker:

```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

Open:

```text
http://localhost:5678
```

Expected result:

- n8n editor opens in the browser
- you can create a new workflow

## 5. Prepare Google Sheets

Create one spreadsheet with two tabs:

```text
events
results
```

The `events` tab stores campus event input.

The `results` tab stores generated bulletin output.

If Google Sheets authentication is difficult, use SQLite or CSV as a backup for Etapa 1.

## Setup Evidence Checklist

```text
[ ] Public API tested
[ ] Ollama installed
[ ] Ollama model downloaded
[ ] Ollama HTTP API tested
[ ] Kokoro tested with a sample sentence
[ ] n8n opens locally
[ ] Google Sheets or database prepared
```

