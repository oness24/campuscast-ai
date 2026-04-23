#!/usr/bin/env python3
"""Deploy (create or update) a workflow JSON to a local n8n instance via REST API.

Mirrors the pattern used in ~/Desktop/AI/zabbix/deploy_cs_poller_containment.py.

Usage:
    export N8N_API_KEY='n8n_api_...'   # create one in n8n Settings → API
    python tools/deploy_to_n8n.py workflow/campuscast-mvp.workflow.json

The script creates the workflow if no workflow with the same name exists,
otherwise updates the existing one in place.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

N8N_BASE = os.environ.get("N8N_BASE", "http://localhost:5678/api/v1")


def require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"ERROR: environment variable {name} is not set.", file=sys.stderr)
        print("Create an API key in n8n → Settings → API, then:", file=sys.stderr)
        print(f"  export {name}='n8n_api_...'", file=sys.stderr)
        sys.exit(1)
    return v


def n8n_request(method: str, path: str, api_key: str, body: dict | None = None) -> dict:
    url = f"{N8N_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", api_key)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        raise SystemExit(f"HTTP {e.code} on {method} {path}: {body_text[:500]}")


def find_workflow_by_name(api_key: str, name: str) -> dict | None:
    resp = n8n_request("GET", "/workflows", api_key)
    for wf in resp.get("data", []):
        if wf.get("name") == name:
            return wf
    return None


def sanitize_for_create(wf: dict) -> dict:
    for field in ("id", "active", "createdAt", "updatedAt", "versionId", "triggerCount", "tags"):
        wf.pop(field, None)
    wf.setdefault("settings", {"executionOrder": "v1"})
    return wf


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    wf_path = sys.argv[1]
    with open(wf_path) as f:
        workflow = json.load(f)

    api_key = require_env("N8N_API_KEY")
    name = workflow.get("name") or os.path.basename(wf_path)
    workflow["name"] = name

    existing = find_workflow_by_name(api_key, name)
    payload = sanitize_for_create(workflow)

    if existing:
        wf_id = existing["id"]
        print(f"Updating existing workflow '{name}' (id={wf_id}) ...")
        result = n8n_request("PUT", f"/workflows/{wf_id}", api_key, payload)
        action = "updated"
    else:
        print(f"Creating new workflow '{name}' ...")
        result = n8n_request("POST", "/workflows", api_key, payload)
        action = "created"

    wf_id = result.get("id") or (existing or {}).get("id", "?")
    print(f"OK — {action} workflow id={wf_id}")
    print(f"Open it: http://localhost:5678/workflow/{wf_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
