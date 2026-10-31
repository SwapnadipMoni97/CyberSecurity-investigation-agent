from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from src.data.repository import get_events


def search_evidence(question: str, alert_id: str | None, hours: int) -> list[dict[str, Any]]:
    events = get_events()
    if not events:
        return []

    parsed = [datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) for e in events]
    latest = max(parsed)
    earliest = latest - timedelta(hours=hours)
    terms = {t.casefold() for t in re.findall(r"[\w@.-]+", question) if len(t) > 2}
    excluded = {"investigate", "investigation", "suspicious", "activity", "related", "events"}
    terms -= excluded
    selected: list[tuple[int, dict[str, Any]]] = []
    for event, timestamp in zip(events, parsed):
        if not alert_id and timestamp < earliest:
            continue
        searchable = " ".join([
            event.get("event_id", ""), event.get("source", ""), event.get("event_type", ""),
            event.get("actor", "") or "", event.get("action", "") or "",
            event.get("resource", "") or "", json_text(event.get("details", {})),
            json_text(event.get("raw", {})),
        ]).casefold()
        score = sum(1 for term in terms if term in searchable)
        if alert_id and alert_id.casefold() in searchable:
            score += 20
        # Keep the full time-bounded sequence for a coherent incident timeline.
        selected.append((score, event))

    if alert_id:
        anchors = [event for score, event in selected if score > 0]
        if not anchors:
            return []
        anchor_ids = {e["event_id"] for e in anchors}
        anchor_times = [datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) for e in anchors]
        actors = {e.get("actor") for e in anchors if e.get("actor")}
        ips = {e.get("ip_address") for e in anchors if e.get("ip_address")}
        # Expand an alert's anchor events to related activity across products.
        # Same-actor or same-IP matches are useful leads, not proof of identity.
        return [
            event for _, event in selected
            if min(abs((datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")) - t).total_seconds())
                   for t in anchor_times) <= hours * 3600
            and (event.get("event_id") in anchor_ids
                 or (event.get("actor") and event.get("actor") in actors)
                 or (event.get("ip_address") and event.get("ip_address") in ips))
        ]
    matched = [event for score, event in selected if score > 0]
    return matched or [event for _, event in selected]


def json_text(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)
