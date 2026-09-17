#!/usr/bin/env python3
"""Build a non-destructive chronological catalog of robot evidence videos."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path


VIDEO_SUFFIXES = {".mp4", ".mov", ".webm"}
VIEW_NAMES = {"top", "left", "right", "camera-0", "camera-1"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "video"


def experiment_key(path: Path) -> tuple[str, str]:
    text = str(path)
    name = path.stem
    if "baseline-repeat" in path.parts:
        return ("baseline-repeat:" + name, name)
    if "/data/runs/task-0003/" in text:
        _, after = text.split("/data/runs/task-0003/", 1)
        run = after.split("/", 1)[0]
        return ("experiment:" + run, run)
    if "/TASK-0001/artifacts/folding" in text:
        return ("experiment:author-baseline", "author-baseline")
    for marker in ("/recordings/", "/data/runs/", "/TASK-0002/artifacts/"):
        if marker in text:
            _, after = text.split(marker, 1)
            run = after.split("/", 1)[0]
            return ("experiment:" + run, run)
    return (str(path.parent), path.parent.name)


def view_name(path: Path) -> str:
    parts = list(path.parts)
    for part in reversed(parts):
        match = re.search(r"observation\.images\.([a-z]+)_rgb", part)
        if match:
            return match.group(1)
    stem = path.stem.lower()
    if stem in VIEW_NAMES:
        return stem
    if stem.startswith("folding-"):
        return stem.removeprefix("folding-")
    return slug(stem)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reset-ids", action="store_true",
                        help="Reassign the catalog from EV-0001; use only before publishing IDs")
    args = parser.parse_args()

    candidates: list[Path] = []
    excluded: list[dict[str, str]] = []
    for root in args.root:
        for path in root.resolve().rglob("*"):
            if (path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
                    and "vendor" not in path.parts and "tests" not in path.parts
                    and args.output.resolve() not in path.parents):
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(path)],
                    capture_output=True, text=True)
                if probe.returncode or not probe.stdout.strip():
                    excluded.append({"source": str(path), "reason": "not a decodable video"})
                else:
                    candidates.append(path)

    # Prefer paths in the standalone project when a migrated rollback copy is identical.
    by_hash: dict[str, Path] = {}
    duplicate_sources: defaultdict[str, list[str]] = defaultdict(list)
    for path in sorted(candidates, key=lambda p: ("xlerobot-folding" not in str(p), str(p))):
        digest = sha256(path)
        duplicate_sources[digest].append(str(path))
        by_hash.setdefault(digest, path)

    groups: defaultdict[str, list[tuple[str, Path]]] = defaultdict(list)
    labels: dict[str, str] = {}
    for digest, path in by_hash.items():
        key, label = experiment_key(path)
        groups[key].append((digest, path))
        labels[key] = label

    ordered = sorted(groups, key=lambda key: (
        min(path.stat().st_mtime_ns for _, path in groups[key]), key))
    args.output.mkdir(parents=True, exist_ok=True)
    for path in args.output.glob("EV-*__*"):
        if path.is_symlink():
            path.unlink()
    previous_ids: dict[str, str] = {}
    previous_manifest = args.output / "index.csv"
    if previous_manifest.is_file() and not args.reset_ids:
        with previous_manifest.open(newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("event_key") and row.get("evidence_id"):
                    previous_ids.setdefault(row["event_key"], row["evidence_id"])
    next_id = 1 + max((int(value.split("-")[1]) for value in previous_ids.values()), default=0)
    assigned: dict[str, str] = {}
    rows = []
    for key in ordered:
        evidence_id = previous_ids.get(key)
        if evidence_id is None:
            evidence_id = f"EV-{next_id:04d}"
            next_id += 1
        assigned[key] = evidence_id
        used_names: defaultdict[str, int] = defaultdict(int)
        for digest, source in sorted(groups[key], key=lambda item: str(item[1])):
            view = view_name(source)
            used_names[view] += 1
            suffix = f"-{used_names[view]}" if used_names[view] > 1 else ""
            destination = args.output / (
                f"{evidence_id}__{slug(labels[key])}__{view}{suffix}{source.suffix.lower()}")
            if destination.is_symlink() or destination.exists():
                destination.unlink()
            destination.symlink_to(source)
            timestamp = datetime.fromtimestamp(source.stat().st_mtime).astimezone().isoformat()
            rows.append({
                "evidence_id": evidence_id,
                "event_key": key,
                "recorded_at": timestamp,
                "experiment": labels[key],
                "view": view,
                "catalog_file": destination.name,
                "source": str(source),
                "sha256": digest,
                "bytes": source.stat().st_size,
                "duplicate_sources": " | ".join(duplicate_sources[digest]),
            })

    manifest = args.output / "index.csv"
    with manifest.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["evidence_id"])
        writer.writeheader()
        writer.writerows(rows)
    timeline = args.output / "timeline.md"
    with timeline.open("w") as stream:
        stream.write("# Robot video evidence timeline\n\n")
        for key in ordered:
            event_rows = [row for row in rows if row["event_key"] == key]
            views = ", ".join(row["view"] for row in event_rows)
            stamp = min(row["recorded_at"] for row in event_rows)
            stream.write(f"- `{assigned[key]}` — {stamp} — **{labels[key]}** — {views}\n")
    excluded_manifest = args.output / "excluded.csv"
    with excluded_manifest.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["source", "reason"])
        writer.writeheader()
        writer.writerows(excluded)
    print(f"Cataloged {len(rows)} unique videos across {len(ordered)} chronological events")
    print(f"Excluded {len(excluded)} invalid video files")
    print(manifest)


if __name__ == "__main__":
    main()
