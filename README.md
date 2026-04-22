# CampusCast AI

CampusCast AI is an intelligent automation prototype that creates a daily campus audio bulletin for students.

The pipeline collects public weather data, combines it with campus event data, asks a local LLM to generate a short useful bulletin, converts the text into audio, and stores the result in a spreadsheet or simple database.

## Project Goal

Build a functional prototype for the first stage of the AI Factory project:

```text
input -> process -> output
```

## Prototype Flow

```text
Schedule or Manual Trigger
        -> Open-Meteo API
        -> Campus events data
        -> n8n data treatment
        -> Ollama local LLM
        -> Kokoro text-to-speech
        -> Google Sheets or SQLite
```

## Main Tools

- Open-Meteo API: public weather data
- Google Sheets: event source and result storage
- n8n: automation orchestration
- Ollama: local LLM response generation
- Kokoro: local text-to-speech generation
- Python, Postman, or Insomnia: API testing

## Main Deliverables

- Problem diagnosis
- Project Canvas
- Environment setup evidence
- n8n workflow
- LLM-generated campus bulletin
- TTS audio file
- Spreadsheet or database record
- Testing checklist
- Short presentation script

## Recommended Etapa 1 Scope

For the first version, keep the prototype focused:

1. Get current weather for Curitiba from Open-Meteo.
2. Read campus events from a Google Sheet or from a small static list in n8n.
3. Generate a short Portuguese bulletin with Ollama.
4. Convert the bulletin to audio with Kokoro.
5. Save the result to Google Sheets or SQLite.

## Folder Structure

```text
campuscast-ai/
├── README.md
├── docs/
│   ├── 01-diagnosis.md
│   ├── 02-project-canvas.md
│   ├── 03-setup-checklist.md
│   ├── 04-implementation-plan.md
│   ├── 05-testing-checklist.md
│   └── 06-presentation-script.md
└── examples/
    ├── ollama-prompt.txt
    ├── google-sheets-columns.csv
    └── sample-campus-events.csv
```

