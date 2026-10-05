#!/usr/bin/env python3
"""Gera logs sintéticos e um oráculo separado para o benchmark temporal."""

from __future__ import annotations

import itertools
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
UTC = timezone.utc
BASE = datetime(2026, 1, 15, 15, 0, 0, tzinfo=UTC)

COMPONENTS = {
    "client": {"zone": "UTC", "semantics": "user_action"},
    "api": {"zone": "America/Sao_Paulo", "semantics": "request_received"},
    "queue": {"zone": "UTC", "semantics": "message_enqueued"},
    "worker": {"zone": "America/New_York", "semantics": "message_processed"},
    "database": {"zone": "UTC", "semantics": "record_persisted"},
    "collector": {"zone": "UTC", "semantics": "log_ingested"},
}

CLOCK_PROFILES = {
    "synced": {},
    "api_plus_300s": {"api": 300},
    "worker_minus_120s": {"worker": -120},
}


def iso_for_source(instant: datetime, component: str, raw_format: str, offset_seconds: int) -> str:
    displayed = instant + timedelta(seconds=offset_seconds)
    localized = displayed.astimezone(ZoneInfo(COMPONENTS[component]["zone"]))
    if raw_format == "utc_explicit":
        return displayed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return localized.replace(tzinfo=None).isoformat(timespec="milliseconds")


def scenario_records(scenario: dict) -> tuple[list[dict], list[dict], dict]:
    raw, oracle = [], []
    queue_delay = timedelta(seconds=scenario["queue_delay_seconds"])
    offsets = CLOCK_PROFILES[scenario["clock_profile"]]
    sequence = 0

    for index in range(12):
        trace_id = f"tx-{index:03d}"
        start = BASE + timedelta(seconds=index * 180)
        events = [
            ("client", start),
            ("api", start + timedelta(milliseconds=100)),
            ("queue", start + timedelta(milliseconds=200)),
            ("worker", start + queue_delay + timedelta(milliseconds=300)),
            ("database", start + queue_delay + timedelta(milliseconds=400)),
            ("collector", start + queue_delay + timedelta(milliseconds=500)),
        ]
        for component, occurred_at in events:
            sequence += 1
            offset = offsets.get(component, 0)
            event_id = f"{scenario['id']}:{trace_id}:{component}"
            raw.append(
                {
                    "event_id": event_id,
                    "trace_id": trace_id,
                    "component": component,
                    "timestamp": iso_for_source(occurred_at, component, scenario["raw_format"], offset),
                    "message": f"{COMPONENTS[component]['semantics']} for {trace_id}",
                }
            )
            oracle.append(
                {
                    "event_id": event_id,
                    "sequence": sequence,
                    "occurred_at_utc": occurred_at.isoformat(),
                }
            )

    complete = scenario["provenance"] == "complete"
    manifest = {
        "scenario_id": scenario["id"],
        "raw_format": scenario["raw_format"],
        "provenance": scenario["provenance"],
        "components": {
            name: {
                "timezone": definition["zone"] if complete else None,
                "clock_offset_seconds": offsets.get(name, 0) if complete else None,
                "semantics": definition["semantics"],
                "uncertainty_seconds": 0.5 if complete else None,
            }
            for name, definition in COMPONENTS.items()
        },
    }
    return raw, oracle, manifest


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_checksums() -> None:
    entries = []
    for path in sorted(DATA.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            entries.append(f"{digest}  {path.relative_to(ROOT)}")
    (DATA / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    scenarios = []
    for number, (clock, raw_format, delay, provenance) in enumerate(
        itertools.product(CLOCK_PROFILES, ("utc_explicit", "local_naive"), (0, 90), ("complete", "incomplete")),
        start=1,
    ):
        scenario = {
            "id": f"S{number:02d}",
            "clock_profile": clock,
            "raw_format": raw_format,
            "queue_delay_seconds": delay,
            "provenance": provenance,
        }
        raw, oracle, manifest = scenario_records(scenario)
        write_jsonl(RAW / f"{scenario['id']}.jsonl", raw)
        write_jsonl(DATA / f"{scenario['id']}_oracle.jsonl", oracle)
        (DATA / f"{scenario['id']}_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )
        scenarios.append(scenario)
    (DATA / "scenarios.json").write_text(json.dumps(scenarios, indent=2), encoding="utf-8")
    write_checksums()
    print(f"Generated {len(scenarios)} scenarios in {DATA}")


if __name__ == "__main__":
    main()
