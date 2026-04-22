# ID 1.1 - Problem Diagnosis

## Project Name

CampusCast AI: Automated Campus Audio Bulletin

## Context

Students often need daily practical information before going to campus. This includes weather conditions, rain risk, transportation planning, academic reminders, and event schedules.

This information usually exists, but it is fragmented across different places:

- weather apps
- university pages
- emails
- messaging groups
- calendars
- informal reminders

The problem is not the absence of information. The problem is that students need to manually check different sources and interpret raw data before making simple daily decisions.

## Real Problem

Students may miss useful daily context because relevant information is scattered and not automatically transformed into a simple recommendation.

Examples:

- A student does not bring an umbrella because they did not check rain risk.
- A student misses an academic event because the reminder was hidden in a message or email.
- A student chooses an outdoor study area even when rain or wind makes it impractical.
- A student wastes time checking multiple platforms before leaving home.

## Evidence and Data Sources

The prototype uses observable data from real or structured sources:

- current weather data from the Open-Meteo public API
- event data from a Google Sheet or simple table
- generated output stored in Google Sheets or SQLite
- execution timestamp and status for each automation run

Open-Meteo provides objective weather indicators such as:

- temperature
- humidity
- rain
- precipitation
- wind speed
- weather code
- timestamp

The event source provides structured campus context such as:

- event date
- event time
- event name
- location
- target audience
- priority

## Causes

The main causes of the problem are:

- information fragmentation across many channels
- manual checking of repetitive information
- lack of personalized interpretation of raw data
- limited accessibility for users who prefer or need audio
- absence of a single daily summary focused on student decisions

## Consequences

The consequences include:

- missed reminders
- poor planning for rain, wind, or transportation delays
- wasted time checking different sources
- lower participation in campus events
- reduced accessibility for students who benefit from audio information

## Automation Opportunity

This problem is suitable for automation because it follows a repeatable data cycle:

```text
collect data -> clean data -> interpret data -> generate message -> publish and store result
```

An automation pipeline can collect public data, combine it with event information, generate a clear recommendation using local AI, convert the result into audio, and save the output for monitoring.

## Proposed Solution

CampusCast AI will generate a short daily campus bulletin.

The bulletin will include:

- weather summary
- practical advice for students
- event reminders
- risk alert when necessary
- audio version for accessibility

## Expected Value

The solution creates value by:

- reducing manual information checking
- transforming raw data into practical guidance
- supporting accessibility with audio output
- creating a reusable automation model for future channels
- preparing the project for later integration with email, WhatsApp, Telegram, or dashboards

