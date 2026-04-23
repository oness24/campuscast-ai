"""CampusCast AI smoke tests.

Runs Python HTTP probes against the three external services the workflow
depends on. Satisfies ID 2.1 ("chamadas HTTP em Python").

Usage:
    python tools/smoke.py               # run all three probes
    python tools/smoke.py --only weather
    python tools/smoke.py --only ollama
    python tools/smoke.py --only kokoro
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Callable

import requests

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=-25.4284&longitude=-49.2733"
    "&current=temperature_2m,relative_humidity_2m,precipitation,rain,"
    "weather_code,wind_speed_10m"
    "&timezone=America/Sao_Paulo"
)
OLLAMA_URL = "http://localhost:11434/api/generate"
KOKORO_URL = "http://localhost:8800/tts"

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


@dataclass
class ProbeResult:
    name: str
    ok: bool
    detail: str


def probe_weather() -> ProbeResult:
    try:
        r = requests.get(OPEN_METEO_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        temp = data["current"]["temperature_2m"]
        if not isinstance(temp, (int, float)):
            return ProbeResult("weather", False, f"temperature_2m not numeric: {temp!r}")
        return ProbeResult("weather", True, f"Curitiba temperature_2m={temp} C")
    except Exception as e:
        return ProbeResult("weather", False, f"{type(e).__name__}: {e}")


def probe_ollama() -> ProbeResult:
    body = {
        "model": "llama3.1:8b",
        "prompt": "Responda em uma frase curta: qual é a capital do Brasil?",
        "stream": False,
    }
    try:
        r = requests.post(OLLAMA_URL, json=body, timeout=60)
        r.raise_for_status()
        data = r.json()
        response = data.get("response", "")
        if not isinstance(response, str) or not response.strip():
            return ProbeResult("ollama", False, f"empty/invalid response: {response!r}")
        preview = response.strip().replace("\n", " ")[:120]
        return ProbeResult("ollama", True, f"{len(response)} chars — {preview!r}")
    except Exception as e:
        return ProbeResult("ollama", False, f"{type(e).__name__}: {e}")


def probe_kokoro() -> ProbeResult:
    body = {"text": "Bom dia. Este é um teste do CampusCast AI."}
    try:
        r = requests.post(KOKORO_URL, json=body, timeout=120)
        r.raise_for_status()
        data = r.json()
        audio_file = data.get("audio_file")
        if not audio_file or not isinstance(audio_file, str):
            return ProbeResult("kokoro", False, f"no audio_file in response: {data!r}")
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(project_root, audio_file)
        if not os.path.exists(full_path):
            return ProbeResult("kokoro", False, f"audio file missing: {full_path}")
        size = os.path.getsize(full_path)
        if size < 1024:
            return ProbeResult("kokoro", False, f"audio file too small: {size} bytes")
        duration = data.get("duration_seconds", 0)
        return ProbeResult("kokoro", True, f"{audio_file} ({size} bytes, {duration}s)")
    except Exception as e:
        return ProbeResult("kokoro", False, f"{type(e).__name__}: {e}")


PROBES: dict[str, Callable[[], ProbeResult]] = {
    "weather": probe_weather,
    "ollama": probe_ollama,
    "kokoro": probe_kokoro,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="CampusCast AI smoke tests")
    parser.add_argument(
        "--only",
        choices=sorted(PROBES),
        help="Run only the named probe. Default runs all probes.",
    )
    args = parser.parse_args()

    names = [args.only] if args.only else list(PROBES)
    results: list[ProbeResult] = []
    for name in names:
        result = PROBES[name]()
        results.append(result)
        color = GREEN if result.ok else RED
        marker = "PASS" if result.ok else "FAIL"
        print(f"{color}[{marker}]{RESET} {result.name}: {result.detail}")

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
