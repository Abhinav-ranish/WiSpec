"""Minimal Home Assistant REST client (stdlib only).

Set ``HA_URL`` (e.g. http://homeassistant.local:8123) and ``HA_TOKEN`` (a
long-lived access token from your HA profile) in the environment. Keep the
token out of the repo.
"""

from __future__ import annotations

import json
import os
import urllib.request

from wispec.automation.intents import ServiceCall


class HomeAssistant:
    def __init__(self, url: str | None = None, token: str | None = None, dry_run: bool = False):
        self.url = (url or os.environ.get("HA_URL", "http://homeassistant.local:8123")).rstrip("/")
        self.token = token or os.environ.get("HA_TOKEN")
        self.dry_run = dry_run or not self.token

    def call(self, c: ServiceCall) -> dict:
        body = {"entity_id": c.entity_id, **c.data}
        if self.dry_run:
            return {"dry_run": True, "endpoint": f"/api/services/{c.domain}/{c.service}", "body": body}
        req = urllib.request.Request(
            f"{self.url}/api/services/{c.domain}/{c.service}",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return {"status": r.status, "states": json.loads(r.read() or b"[]")}
