# Testing Checklist

Use this checklist before presenting Etapa 1.

## Component Tests

```text
[ ] Open-Meteo API returns JSON data
[ ] Weather fields are present: temperature, humidity, rain, precipitation, wind speed
[ ] Event data source has at least one event
[ ] Ollama is running locally
[ ] Ollama model responds to a simple prompt
[ ] Ollama HTTP API returns a JSON response
[ ] Kokoro receives text input
[ ] Kokoro generates an audio file
[ ] Google Sheets or SQLite is ready to receive data
```

## Workflow Tests

```text
[ ] n8n workflow starts manually
[ ] n8n receives weather data
[ ] n8n includes campus event data
[ ] n8n prepares a clean prompt
[ ] n8n sends the prompt to Ollama
[ ] n8n receives a generated bulletin
[ ] n8n sends text to Kokoro
[ ] Kokoro generates an audio file
[ ] n8n saves the result
[ ] final spreadsheet/database row is complete
```

## Quality Tests

```text
[ ] Bulletin is under 120 words
[ ] Bulletin is understandable in Portuguese
[ ] Bulletin does not invent events
[ ] Bulletin includes practical advice
[ ] Bulletin mentions risk only when relevant
[ ] Audio is clear enough to understand
[ ] Stored data includes timestamp and status
```

## Demo Success Test

The demo is successful when you can show:

```text
API input -> n8n workflow -> Ollama text -> Kokoro audio -> saved spreadsheet row
```

