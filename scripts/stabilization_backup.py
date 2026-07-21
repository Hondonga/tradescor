"""One-shot Phase 1 stabilization backup: copies the artifact categories the
milestone requires into data/stabilization/backups/ (preserving original
relative paths), and records path/size/SHA-256 for every copied file into
data/stabilization/checksums/artifact_checksums.json.

Read-only with respect to the originals: copies only, never moves or edits.
Safe to re-run.
"""
from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = ROOT / "data" / "stabilization" / "backups"
CHECKSUM_FILE = ROOT / "data" / "stabilization" / "checksums" / "artifact_checksums.json"

# Explicit files (not whole directories) to back up.
FILES = [
    "data/derived_paper_testing.db",
    "data/derived_replay.db",
    "data/strategy_gate_diagnostics.db",
    "data/smc_acceptance.db",
]

# Whole directories to back up recursively.
DIRECTORIES = [
    "data/strategy_setup_proof",
    "data/browser_acceptance",
    "data/ml",
    "data/strategy_feasibility",
    "data/forex_audits",
    "data/volatility75_acceptance",
    "config",
]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_sources() -> list[Path]:
    sources: list[Path] = []
    for rel in FILES:
        path = ROOT / rel
        if path.exists():
            sources.append(path)
    for rel in DIRECTORIES:
        base = ROOT / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                sources.append(path)
    return sources


def main() -> None:
    sources = collect_sources()
    records = []
    for source in sources:
        rel = source.relative_to(ROOT)
        dest = BACKUP_ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        records.append(
            {
                "original_path": str(rel),
                "backup_path": str(dest.relative_to(ROOT)),
                "size_bytes": source.stat().st_size,
                "sha256": sha256_of(source),
            }
        )
    CHECKSUM_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKSUM_FILE.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "file_count": len(records),
                "total_bytes": sum(r["size_bytes"] for r in records),
                "files": records,
            },
            indent=2,
        )
    )
    print(f"Backed up {len(records)} files ({sum(r['size_bytes'] for r in records)} bytes) -> {CHECKSUM_FILE}")


if __name__ == "__main__":
    main()
