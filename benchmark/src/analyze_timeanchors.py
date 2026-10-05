#!/usr/bin/env python3
"""Produce a conservative external-validation report for the TimeAnchors subset.

It does not attempt to reconstruct every user event. Instead, it checks whether
the selected provenance records reveal documented clock changes and whether a
strict chronological conclusion should be made or withheld for each VM.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="prepared TimeAnchors working copy")
    parser.add_argument("output", type=Path, help="empty output directory")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output directory must be empty")
    args.output.mkdir(parents=True, exist_ok=True)

    lablog = read_csv(args.input / "LabLog.csv")
    actions: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in lablog:
        source = row["Data source"].strip()
        action = row["Action"].strip().lower()
        if source.startswith("VM") and any(term in action for term in ("backdating", "resync", "sync time")):
            actions[source].append({
                "recorded_datetime": f"{row['Date'].strip()} {row['Time'].strip()}",
                "action": row["Action"].strip(),
                "note": row["Note"].strip(),
            })

    report: dict[str, object] = {
        "dataset": "Vanini et al., TimeAnchors v1.0",
        "source_manifest": json.loads((args.input / "MANIFEST.json").read_text(encoding="utf-8")),
        "method": "Conservative provenance check: documented clock intervention plus independent time-service record is treated as evidence of a clock anomaly; absence of the latter requires abstention from strict ordering.",
        "vms": {},
    }
    outcome_counts = defaultdict(int)
    for vm_dir in sorted(path for path in args.input.glob("VM*") if path.is_dir()):
        vm = vm_dir.name
        event_path = vm_dir / "Analyzed_Data" / "event_logs_summary.csv"
        time_events: list[dict[str, str]] = []
        if event_path.exists():
            for row in read_csv(event_path):
                payload = row.get("Payload", "")
                if row.get("EventId") in {"261", "265", "266"}:
                    time_events.append({
                        "event_id": row.get("EventId", ""),
                        "time_created": row.get("TimeCreated", ""),
                        "payload": payload,
                    })
        documented = actions.get(vm, [])
        has_backdating = any("backdating" in event["action"].lower() for event in documented)
        has_set_time = any(event["event_id"] == "261" for event in time_events)
        has_time_source = any(event["event_id"] == "265" for event in time_events)
        if has_backdating and has_set_time and has_time_source:
            outcome = "anomalia identificada; ordem estrita exige normalização documentada"
        elif has_backdating:
            outcome = "abstenção justificada: alteração documentada sem âncora independente selecionada"
        else:
            outcome = "sem anomalia manual documentada nesta seleção; não inferir precisão além da semântica do artefato"
        outcome_counts[outcome] += 1
        report["vms"][vm] = {
            "documented_clock_actions": documented,
            "time_service_records_selected": len(time_events),
            "has_set_time_record": has_set_time,
            "has_time_source_reference": has_time_source,
            "conclusion": outcome,
        }

    report["summary"] = {
        "vm_count": len(report["vms"]),
        "outcomes": dict(outcome_counts),
        "claim_limit": "This validates the protocol's ability to disclose clock-change evidence and to abstain when provenance is incomplete. It does not estimate error frequency in criminal cases or validate every timestamp in the dataset.",
    }
    (args.output / "external_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Resultado da validação externa — TimeAnchors",
        "",
        "O relatório foi produzido a partir da seleção pré-registrada, depois de verificação do MD5 publicado. O ZIP bruto não foi alterado.",
        "",
        "| VM | Ação temporal documentada | Registro `SET_TIME` | Referência de fonte de tempo | Conclusão do protocolo |",
        "|---|---|---:|---:|---|",
    ]
    for vm, item in report["vms"].items():
        action_text = "; ".join(action["action"] for action in item["documented_clock_actions"]) or "—"
        lines.append(
            f"| {vm} | {action_text} | {'sim' if item['has_set_time_record'] else 'não'} | {'sim' if item['has_time_source_reference'] else 'não'} | {item['conclusion']} |"
        )
    lines.extend([
        "",
        "## Interpretação",
        "",
        "O resultado não declara que todo timestamp das VMs é falso. Ele demonstra, em artefatos controlados, que uma linha do tempo pode conter mudança de relógio materialmente relevante e que a conclusão adequada depende de documentação de fonte, semântica e sincronização. Onde a alteração documentada não é acompanhada, na seleção, de âncora independente, o protocolo não produz ordem cronológica estrita.",
        "",
        "## Limites",
        "",
        "O conjunto é controlado, concentrado em Windows/Chrome, e a análise seleciona CSVs derivados por ferramentas indicadas pelos autores. Não representa casos penais brasileiros nem autoriza estimativa de prevalência de relógios incorretos.",
    ])
    (args.output / "external_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
