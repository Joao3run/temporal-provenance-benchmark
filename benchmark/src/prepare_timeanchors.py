#!/usr/bin/env python3
"""Verify and prepare the pre-registered subset of the TimeAnchors dataset.

The script deliberately never changes the original ZIP. It creates a small working
copy with the documentation and analysed summaries selected in 08_validacao_externa_timeanchors.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

PUBLISHED_MD5 = "3f657b6283e197f2713a5f55aef70347"
ROOT_FILES = {"LabLog.csv", "README.txt"}
SUMMARY_NAMES = {
    "cache_summary.csv",
    "event_logs_summary.csv",
    "history_downloads_summary.csv",
    "history_urls_visits_summary.csv",
}


def digest(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def selected_member(name: str) -> bool:
    parts = Path(name).parts
    return (
        Path(name).name in ROOT_FILES
        or ("Analyzed_Data" in parts and Path(name).name in SUMMARY_NAMES)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", type=Path, help="downloaded TimeAnchors.zip")
    parser.add_argument("output", type=Path, help="new, empty working directory")
    args = parser.parse_args()

    if not args.zip.is_file():
        parser.error(f"ZIP not found: {args.zip}")
    actual_md5 = digest(args.zip, "md5")
    if actual_md5 != PUBLISHED_MD5:
        print(
            f"MD5 mismatch: expected {PUBLISHED_MD5}, got {actual_md5}. "
            "No extraction performed.",
            file=sys.stderr,
        )
        return 2
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output directory must not contain files")
    args.output.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(args.zip) as archive:
        bad_member = archive.testzip()
        if bad_member:
            print(f"ZIP integrity failure in {bad_member}; no extraction performed.", file=sys.stderr)
            return 3
        members = [item for item in archive.namelist() if selected_member(item)]
        if not members:
            print("No pre-registered members found; no extraction performed.", file=sys.stderr)
            return 4
        for member in members:
            target = args.output / member
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)

    manifest = {
        "source_zip": str(args.zip.resolve()),
        "published_md5": PUBLISHED_MD5,
        "observed_md5": actual_md5,
        "observed_sha256": digest(args.zip, "sha256"),
        "selection_rule": "root documentation plus pre-registered Analyzed_Data CSV summaries per VM, including time-service summaries when available",
        "members": sorted(str(path.relative_to(args.output)) for path in args.output.rglob("*") if path.is_file()),
    }
    (args.output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(members)} files in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
