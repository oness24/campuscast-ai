# Short Presentation Script

Use this as a base for a 2 to 4 minute Etapa 1 explanation.

## Opening

Our project is called CampusCast AI. It is an intelligent automation prototype that creates a short daily audio bulletin for students.

The problem we identified is that students often need practical daily information before going to campus, such as weather conditions, event reminders, and risk alerts. This information exists, but it is fragmented across weather apps, calendars, emails, university pages, and messaging groups.

## Problem and Opportunity

The main issue is not the lack of information. The issue is that students need to manually check multiple sources and interpret the data themselves.

This creates an opportunity for automation because the process follows a clear cycle: collect data, process it, generate a useful response, create an accessible output, and store the result.

## Solution

CampusCast AI solves this by creating an automated pipeline.

First, the workflow collects current weather data from the Open-Meteo public API. Then it combines this data with campus event information. After that, n8n sends the treated data to Ollama, which runs locally and generates a short Portuguese bulletin for students.

The generated text is then sent to Kokoro, which converts it into audio. Finally, the result is saved in Google Sheets or a simple database with the timestamp, input data, generated response, audio reference, and execution status.

## Technical Pipeline

The pipeline follows this structure:

```text
Open-Meteo API and campus events
    -> n8n automation
    -> Ollama local LLM
    -> Kokoro text-to-speech
    -> Google Sheets or database
```

This demonstrates the complete cycle required in the project: input, processing, and output.

## Expected Result

The final output is a short campus bulletin in text and audio.

For example, the system can say that the weather in Curitiba has rain risk, recommend that students bring an umbrella, remind them about an academic event, and warn them to plan transportation earlier if needed.

## Value

The value of this prototype is that it transforms raw data into practical and accessible information. It reduces manual checking, supports students in daily planning, and creates a base for future multichannel communication.

## Next Steps

In the next stage, this same bulletin can be sent automatically by email, WhatsApp, or Telegram. We can also add error handling, logs, environment variables, and performance metrics such as latency and success rate.

