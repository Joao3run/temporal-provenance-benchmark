#!/usr/bin/env python3
"""Compara ordenação ingênua e ordenação orientada por proveniência."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RESULTS = ROOT / "results"
UTC = timezone.utc


def parse_naive(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_with_provenance(record: dict, manifest: dict) -> tuple[datetime | None, bool]:
    component = manifest["components"][record["component"]]
    if manifest["provenance"] != "complete" or not component["timezone"]:
        return None, False
    value = record["timestamp"]
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(component["timezone"]))
    normalized = parsed.astimezone(UTC) - timedelta(seconds=component["clock_offset_seconds"])
    return normalized, True


def order_map(records: list[dict], key: str) -> dict[str, int]:
    ordered = sorted(records, key=lambda row: row[key])
    return {row["event_id"]: index for index, row in enumerate(ordered)}


def score(order: dict[str, int], oracle: dict[str, int], decided: set[str]) -> tuple[float, float, float, int]:
    total = correct = false_certainty = decided_pairs = 0
    for left, right in combinations(sorted(decided), 2):
        decided_pairs += 1
        same = (order[left] < order[right]) == (oracle[left] < oracle[right])
        correct += int(same)
        false_certainty += int(not same)
    all_pairs = len(oracle) * (len(oracle) - 1) // 2
    accuracy = correct / decided_pairs if decided_pairs else 0.0
    false_rate = false_certainty / decided_pairs if decided_pairs else 0.0
    coverage = decided_pairs / all_pairs if all_pairs else 0.0
    return accuracy, false_rate, coverage, decided_pairs


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    scenarios = json.loads((DATA / "scenarios.json").read_text(encoding="utf-8"))
    rows = []
    for scenario in scenarios:
        sid = scenario["id"]
        raw = [json.loads(line) for line in (RAW / f"{sid}.jsonl").read_text(encoding="utf-8").splitlines()]
        oracle_rows = [json.loads(line) for line in (DATA / f"{sid}_oracle.jsonl").read_text(encoding="utf-8").splitlines()]
        oracle = {row["event_id"]: row["sequence"] for row in oracle_rows}
        manifest = json.loads((DATA / f"{sid}_manifest.json").read_text(encoding="utf-8"))

        naive_rows = [{**row, "normalized": parse_naive(row["timestamp"])} for row in raw]
        naive_order = order_map(naive_rows, "normalized")
        naive_accuracy, naive_false, naive_coverage, _ = score(naive_order, oracle, set(naive_order))

        fpt_rows = []
        for row in raw:
            normalized, decidable = parse_with_provenance(row, manifest)
            if decidable:
                fpt_rows.append({**row, "normalized": normalized})
        fpt_order = order_map(fpt_rows, "normalized") if fpt_rows else {}
        fpt_accuracy, fpt_false, fpt_coverage, decided_pairs = score(fpt_order, oracle, set(fpt_order))
        rows.append(
            {
                **scenario,
                "naive_pair_accuracy": round(naive_accuracy, 4),
                "naive_false_certainty": round(naive_false, 4),
                "naive_coverage": round(naive_coverage, 4),
                "fpt_pair_accuracy": round(fpt_accuracy, 4),
                "fpt_false_certainty": round(fpt_false, 4),
                "fpt_coverage": round(fpt_coverage, 4),
                "fpt_decided_pairs": decided_pairs,
            }
        )
    fields = list(rows[0])
    with (RESULTS / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} scenario rows to {RESULTS / 'metrics.csv'}")


if __name__ == "__main__":
    main()

