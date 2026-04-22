# ID 1.2 - Project Canvas

## Project Summary

| Field | Description |
|---|---|
| Project name | CampusCast AI |
| Main idea | Automated campus audio bulletin for students |
| Target users | Students, classmates, campus community |
| Context | Daily student routine and campus planning |
| Main problem | Campus information is fragmented and not automatically converted into practical recommendations |
| Proposed solution | An automation pipeline that creates a short text and audio bulletin using API data and local AI |

## Objective

Create a functional prototype that collects weather data and campus event data, generates a short daily bulletin with a local LLM, converts the text into audio with Kokoro, and stores the result in Google Sheets or a simple database.

## SMART Objectives

| Objective | SMART definition |
|---|---|
| Collect public data | The prototype will collect current weather data from Open-Meteo for Curitiba using an HTTP request |
| Generate AI response | The prototype will send treated data to Ollama and receive a bulletin under 120 words |
| Generate audio | The prototype will send the bulletin text to Kokoro and generate an audio file |
| Store output | The prototype will save timestamp, input data, generated text, audio reference, and status in Google Sheets or SQLite |
| Demonstrate functionality | The team will present at least one successful end-to-end execution |

## Inputs

- Weather data from Open-Meteo
- Campus event data from Google Sheets or a simple table

## Processing

- n8n workflow orchestration
- data cleaning and field selection
- prompt construction
- Ollama LLM generation
- Kokoro TTS generation

## Outputs

- generated bulletin text
- generated audio file
- spreadsheet or database row
- execution status and timestamp

## Deliverables

| Deliverable | Description |
|---|---|
| Diagnosis | Context, problem, causes, consequences, and automation opportunity |
| Canvas | Objectives, roles, deliverables, risks, and success criteria |
| API test evidence | Screenshot or log showing the Open-Meteo response |
| Ollama test evidence | Screenshot or log showing local LLM response |
| Kokoro test evidence | Audio generated from sample text |
| n8n workflow | Functional pipeline exported as JSON |
| Result storage | Google Sheet or SQLite table with at least one execution record |
| Presentation | Short explanation of problem, pipeline, result, and next steps |

## Team Roles

| Role | Responsibility |
|---|---|
| Researcher | Defines the problem, context, and diagnosis |
| Automation developer | Builds the n8n flow and API integrations |
| AI/TTS developer | Tests Ollama and Kokoro locally |
| Tester/documenter | Validates outputs, records evidence, and prepares presentation |

If the project is individual, one person can perform all roles and describe them as responsibilities instead of separate people.

## Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Ollama model is slow | Workflow latency increases | Use a smaller model and keep the prompt short |
| Kokoro setup is difficult | Audio generation may fail | Test Kokoro separately before connecting it to n8n |
| Google Sheets authentication fails | Results are not saved | Use SQLite or CSV as a backup |
| API returns unexpected data | LLM prompt receives incomplete data | Add default values and error handling in n8n |
| Bulletin invents events | Incorrect information | Instruct the LLM not to invent events |

## Success Criteria

The prototype is successful when:

- the workflow receives weather data from Open-Meteo
- event data is included in the prompt
- Ollama generates a relevant bulletin
- Kokoro generates an audio file
- the result is saved in a spreadsheet or database
- the team can demonstrate one complete execution

