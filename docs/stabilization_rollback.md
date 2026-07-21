# TradeScor Stabilization Rollback Instructions

Generated as part of Phase 1 (Freeze the current build and create a safe
recovery baseline). This document describes how to restore the application
to the exact state captured in this baseline. **These steps have not been
executed** — they are validated to the extent the referenced files/branches
exist, but the rollback itself was not run.

## Reference points

- Safety branch: `tradescor-stabilization-baseline`
- Safety tag: `tradescor-before-stabilization-v1`
- Baseline commit: see `git log tradescor-before-stabilization-v1` (first
  commit in the repository — the entire pre-stabilization codebase)
- Database backup location: `data/stabilization/backups/`
- Artifact/checksum backup location: `data/stabilization/backups/` (same
  tree, includes `data/ml/`, `config/`, `data/strategy_setup_proof/`,
  `data/browser_acceptance/`, `data/strategy_feasibility/`,
  `data/forex_audits/`, `data/volatility75_acceptance/`)
- Checksum manifest: `data/stabilization/checksums/artifact_checksums.json`
- ML artifact integrity record: `data/stabilization/reports/ml_artifact_integrity.json`
- Baseline manifest: `data/stabilization/baseline/baseline_manifest.json`

## How to restore the code

```bash
cd "ict_flask_scanner"
git status   # confirm you understand what you are about to discard
git switch tradescor-stabilization-baseline
# or, to restore exactly the tagged commit on a new branch:
git switch -c recovery-from-baseline tradescor-before-stabilization-v1
```

Do not run `git reset --hard`, `git clean -fd`, `git checkout -- .`, or
`git restore .` against a branch with uncommitted work you want to keep —
switch to a new branch first if in doubt.

## How to restore databases

The following databases are backed up under `data/stabilization/backups/data/`:

- `derived_paper_testing.db`
- `derived_replay.db`
- `strategy_gate_diagnostics.db`
- `smc_acceptance.db`

To restore one, stop any running backend process first, then:

```bash
cp "data/stabilization/backups/data/<name>.db" "data/<name>.db"
```

## How to restore ML / config / report artifacts

Every file under `data/stabilization/backups/` mirrors its original relative
path. To restore any single file:

```bash
cp "data/stabilization/backups/<relative_path>" "<relative_path>"
```

To restore the full backed-up tree:

```bash
cp -R data/stabilization/backups/data/. data/
cp -R data/stabilization/backups/config/. config/
```

## How to verify restored checksums

```bash
python3 - <<'PY'
import json, hashlib
manifest = json.load(open("data/stabilization/checksums/artifact_checksums.json"))
mismatches = []
for row in manifest["files"]:
    digest = hashlib.sha256()
    with open(row["original_path"], "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != row["sha256"]:
        mismatches.append(row["original_path"])
print("mismatches:", mismatches or "none")
PY
```

For the frozen ML dataset specifically, also confirm:

```bash
python3 -c "import json; print(json.load(open('data/ml/datasets/ml-r75-f4c52d93c7a8dc3e95f1/manifest.json'))['checksum'])"
# must print: 737b02ea7c98fa68131920cc0fb6f5b438a8504dc2898aea14c1ce4c0b178b23
```

## How to restart the backend

```bash
cd "ict_flask_scanner"
python3 app.py
# Flask serves on http://127.0.0.1:5000 by default (no PORT env override in this baseline)
```

## How to rebuild the frontend

```bash
cd "ict_flask_scanner/frontend"
npm install       # only if node_modules is missing/stale
npx tsc -b
npx vite build    # writes frontend/dist, served by the Flask app
# or, for local dev with hot reload:
npm run dev       # vite dev server on :5173, proxies /api to :5000
```

## Rollback is safe when

- `git status` on the target branch is clean before you switch away from work you want to keep.
- Any database file you are about to overwrite is itself backed up first if it has changed since this baseline.
- You have confirmed you are restoring into the same `ict_flask_scanner/` directory this baseline was captured from (not the unrelated placeholder scripts one level up).
