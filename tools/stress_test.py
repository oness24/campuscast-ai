"""CampusCast AI stress test.

Fires the Etapa-2 workflow N times (default 5), records per-node timing
for each run, then prints a bottleneck report.

Usage:
    python tools/stress_test.py
    python tools/stress_test.py --runs 3

Prerequisites:
    - n8n running at 127.0.0.1:5678
    - kokoro_server running at 127.0.0.1:8800
    - N8N_EMAIL / N8N_PASSWORD env vars (or defaults below)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import requests

N8N_BASE = "http://127.0.0.1:5678"
N8N_EMAIL = os.environ.get("N8N_EMAIL", "contego704@gmail.com")
N8N_PASSWORD = os.environ.get("N8N_PASSWORD", "143030@Contego#")
WORKFLOW_ID = "E9K59jrThdHRSxxb"
BROWSER_ID = "campuscast-stress-test"
POLL_INTERVAL_S = 5
EXECUTION_TIMEOUT_S = 300


@dataclass
class NodeTiming:
    name: str
    start_ms: float
    end_ms: float

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms


@dataclass
class RunResult:
    run_number: int
    execution_id: str
    status: str
    wall_time_s: float
    node_timings: list[NodeTiming] = field(default_factory=list)
    error: str = ""


def n8n_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"browser-id": BROWSER_ID})
    r = s.post(
        f"{N8N_BASE}/rest/login",
        json={"emailOrLdapLoginId": N8N_EMAIL, "password": N8N_PASSWORD},
        timeout=10,
    )
    r.raise_for_status()
    for cookie in s.cookies:
        cookie.secure = False
    return s


def trigger_run(s: requests.Session) -> str:
    r = s.post(
        f"{N8N_BASE}/rest/workflows/{WORKFLOW_ID}/run",
        json={"triggerToStartFrom": {"name": "Schedule 07h"}},
        timeout=15,
    )
    r.raise_for_status()
    d = r.json()
    return d["data"]["executionId"]


def poll_until_done(s: requests.Session, exec_id: str) -> dict[str, Any]:
    deadline = time.time() + EXECUTION_TIMEOUT_S
    while time.time() < deadline:
        r = s.get(f"{N8N_BASE}/rest/executions/{exec_id}?includeData=true", timeout=15)
        r.raise_for_status()
        data = r.json().get("data", r.json())
        status = data.get("status", "running")
        if status in ("success", "error", "crashed", "canceled"):
            return data
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"Execution {exec_id} did not finish within {EXECUTION_TIMEOUT_S}s")


def extract_node_timings(exec_data: dict[str, Any]) -> list[NodeTiming]:
    timings: list[NodeTiming] = []
    raw = exec_data.get("data")
    if not raw:
        return timings
    try:
        inner = json.loads(raw) if isinstance(raw, str) else raw
        # n8n stores execution times in executionTime per node via startedAt/stoppedAt
        # The inner data is a "ropes" serialized structure; iterate top-level items
        # looking for dicts that contain ISO timestamps (startedAt/stoppedAt pattern).
        # Simpler: use the outer exec_data fields startedAt/stoppedAt for total only.
        # Per-node times: find all dicts in the rope table that have executionTime or
        # startTime + endTime fields.
        seen = set()
        for item in (inner if isinstance(inner, list) else [inner]):
            if not isinstance(item, dict):
                continue
            for key, val in item.items():
                if isinstance(val, dict) and "executionTime" in val:
                    if key not in seen:
                        seen.add(key)
                        et = val["executionTime"]
                        timings.append(NodeTiming(name=key, start_ms=0, end_ms=et))
                elif isinstance(val, dict) and "startTime" in val and "endTime" in val:
                    if key not in seen:
                        seen.add(key)
                        timings.append(NodeTiming(
                            name=key,
                            start_ms=val["startTime"],
                            end_ms=val["endTime"],
                        ))
    except Exception:
        pass
    return timings


def run_stress_test(n_runs: int) -> list[RunResult]:
    print(f"Connecting to n8n at {N8N_BASE}...")
    s = n8n_session()
    print(f"Starting {n_runs} runs of workflow {WORKFLOW_ID}\n")

    results: list[RunResult] = []
    for i in range(1, n_runs + 1):
        print(f"[Run {i}/{n_runs}] Triggering...", end=" ", flush=True)
        t0 = time.time()
        try:
            exec_id = trigger_run(s)
            print(f"exec={exec_id}", end=" ", flush=True)
            exec_data = poll_until_done(s, exec_id)
            wall = round(time.time() - t0, 2)
            status = exec_data.get("status", "?")
            timings = extract_node_timings(exec_data)
            result = RunResult(
                run_number=i,
                execution_id=exec_id,
                status=status,
                wall_time_s=wall,
                node_timings=timings,
            )
            print(f"→ {status} ({wall}s)")
        except Exception as e:
            wall = round(time.time() - t0, 2)
            result = RunResult(
                run_number=i,
                execution_id="?",
                status="exception",
                wall_time_s=wall,
                error=str(e),
            )
            print(f"→ EXCEPTION: {e}")
        results.append(result)

    return results


def print_report(results: list[RunResult]) -> None:
    print("\n" + "=" * 60)
    print("STRESS TEST REPORT")
    print("=" * 60)

    success = [r for r in results if r.status == "success"]
    fail = [r for r in results if r.status != "success"]

    print(f"\nRuns: {len(results)}  |  Success: {len(success)}  |  Failed: {len(fail)}")

    if not success:
        print("\nNo successful runs to report.")
        if fail:
            for r in fail:
                print(f"  Run {r.run_number} [{r.status}]: {r.error}")
        return

    wall_times = [r.wall_time_s for r in success]
    print(f"\nWall-clock time (success runs):")
    print(f"  min={min(wall_times):.1f}s  avg={sum(wall_times)/len(wall_times):.1f}s  max={max(wall_times):.1f}s")

    # Per-node aggregation across runs that had timing data
    node_totals: dict[str, list[float]] = {}
    for r in success:
        for t in r.node_timings:
            node_totals.setdefault(t.name, []).append(t.duration_ms)

    if node_totals:
        print("\nPer-node average duration (ms):")
        sorted_nodes = sorted(node_totals.items(), key=lambda x: -sum(x[1]) / len(x[1]))
        for name, durations in sorted_nodes:
            avg = sum(durations) / len(durations)
            print(f"  {name:<35} avg={avg:>8.1f} ms  ({len(durations)} samples)")
        bottleneck = sorted_nodes[0][0]
        print(f"\n  ↳ Bottleneck: {bottleneck}")
    else:
        print("\n(Per-node timing not available — n8n did not expose executionTime.)")
        print("  Likely bottleneck: Ollama Generate (LLM inference) or Kokoro TTS.")

    if fail:
        print(f"\nFailed runs:")
        for r in fail:
            print(f"  Run {r.run_number} exec={r.execution_id} [{r.status}]: {r.error[:80]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CampusCast AI stress test")
    parser.add_argument("--runs", type=int, default=5, help="Number of workflow runs (default 5)")
    args = parser.parse_args()

    results = run_stress_test(args.runs)
    print_report(results)
    return 0 if all(r.status == "success" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
