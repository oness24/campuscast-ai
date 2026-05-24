#!/usr/bin/env python3
"""
Create n8n credentials (Telegram + SMTP) and Variables for Etapa 2.
Prints the credential IDs needed for the workflow JSON.

Usage:
    export TG_BOT_TOKEN='7890123456:AAFxyz...'
    export TG_CHAT_ID='-1001234567890'
    export GMAIL_APP_PASSWORD='abcdefghijklmnop'
    python tools/setup_n8n_etapa2.py
"""
from __future__ import annotations

import json
import os
import sys

import requests

BASE = "http://127.0.0.1:5678"
EMAIL = "contego704@gmail.com"
PASSWORD = "143030@Contego#"
SHEET_ID = "1DQ1hYUafUCFAGBlfEjy0cBKKGTKhOdTDVlqXzBbHqKk"


BROWSER_ID = "campuscast-setup-cli"


def login() -> requests.Session:
    s = requests.Session()
    s.headers.update({"browser-id": BROWSER_ID})
    r = s.post(
        f"{BASE}/rest/login",
        json={"emailOrLdapLoginId": EMAIL, "password": PASSWORD},
        timeout=10,
    )
    r.raise_for_status()
    # Force the cookie to be sent over plain HTTP (it has Secure flag but we're on localhost)
    for cookie in s.cookies:
        cookie.secure = False
    return s


def n8n(method: str, path: str, s: requests.Session, body: dict | None = None) -> dict:
    r = s.request(method, f"{BASE}/rest{path}", json=body, timeout=15)
    if not r.ok:
        raise SystemExit(f"HTTP {r.status_code} on {method} {path}: {r.text[:300]}")
    d = r.json() if r.text else {}
    return d.get("data", d)


def find_credential(s: requests.Session, name: str) -> str | None:
    creds = n8n("GET", "/credentials", s)
    for c in (creds if isinstance(creds, list) else []):
        if c.get("name") == name:
            return c["id"]
    return None


def create_or_find_credential(
    s: requests.Session, name: str, cred_type: str, cred_data: dict
) -> str:
    existing = find_credential(s, name)
    if existing:
        print(f"  [exists] credential '{name}' id={existing}")
        return existing
    result = n8n("POST", "/credentials", s, {"name": name, "type": cred_type, "data": cred_data})
    cred_id = result.get("id")
    print(f"  [created] credential '{name}' id={cred_id}")
    return cred_id


def set_variable(s: requests.Session, key: str, value: str) -> None:
    try:
        variables = n8n("GET", "/variables", s)
        for v in (variables if isinstance(variables, list) else []):
            if v.get("key") == key:
                n8n("PATCH", f"/variables/{v['id']}", s, {"value": value})
                print(f"  [updated] variable {key}={value!r}")
                return
        n8n("POST", "/variables", s, {"key": key, "value": value})
        print(f"  [created] variable {key}={value!r}")
    except SystemExit as e:
        if "license" in str(e).lower() or "403" in str(e):
            print(f"  [skip] variable {key} — n8n community plan lacks Variables feature")
        else:
            raise


def main() -> None:
    tg_token = os.environ.get("TG_BOT_TOKEN", "")
    tg_chat = os.environ.get("TG_CHAT_ID", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    email_to = os.environ.get("CAMPUSCAST_EMAIL_TO", "onesmus.simiyu@pucpr.edu.br")

    missing = [
        k for k, v in [
            ("TG_BOT_TOKEN", tg_token),
            ("TG_CHAT_ID", tg_chat),
            ("GMAIL_APP_PASSWORD", gmail_pass),
        ]
        if not v
    ]
    if missing:
        print(f"ERROR: set environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    print("Logging in to n8n...")
    s = login()

    print("\nCreating credentials...")
    tg_id = create_or_find_credential(
        s,
        "CampusCast Telegram Bot",
        "telegramApi",
        {"accessToken": tg_token},
    )
    smtp_id = create_or_find_credential(
        s,
        "CampusCast Gmail SMTP",
        "smtp",
        {
            "host": "smtp.gmail.com",
            "port": 587,
            "user": EMAIL,
            "password": gmail_pass,
            "secure": False,
            "allowUnauthorizedCerts": False,
        },
    )

    print("\nCreating n8n Variables...")
    set_variable(s, "CAMPUSCAST_CITY", "Curitiba")
    set_variable(s, "CAMPUSCAST_EMAIL_TO", email_to)
    set_variable(s, "CAMPUSCAST_TG_CHAT_ID", tg_chat)
    set_variable(s, "CAMPUSCAST_SHEET_ID", SHEET_ID)

    print(f"\nDone. Copy these IDs into the workflow JSON:")
    print(f"  TELEGRAM_CRED_ID = {tg_id!r}")
    print(f"  SMTP_CRED_ID     = {smtp_id!r}")


if __name__ == "__main__":
    main()
