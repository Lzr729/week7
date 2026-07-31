from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "README.md",
    "data/八家公司统一口径核心指标_最终验收.xlsx",
    "data/八家公司统一口径公司指标.csv",
    "data/八家公司统一口径核心指标.json",
    "config/unified_caliber_v1_0.json",
    "audit/final_decisions_consolidated.json",
    "manifest.json",
    "CHECKSUMS.sha256",
}

FORBIDDEN_SUFFIXES = {".pdf", ".docx"}
FORBIDDEN_REPORTS = {"report/本周工作简报.md"}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main() -> int:
    errors = []
    files = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file() and p.relative_to(ROOT).as_posix() != "scripts/verify_submission.py"
    }

    missing = REQUIRED - files
    if missing:
        errors.append(f"missing files: {sorted(missing)}")

    forbidden_binary = [
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in FORBIDDEN_SUFFIXES
    ]
    if forbidden_binary:
        errors.append(f"PDF/DOCX should remain local only: {forbidden_binary}")

    forbidden_reports = sorted(files & FORBIDDEN_REPORTS)
    if forbidden_reports:
        errors.append(f"weekly report should not be in GitHub: {forbidden_reports}")

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "FINAL_APPROVED":
        errors.append("manifest status mismatch")
    if manifest["submission_mode"] != "DATA_ONLY":
        errors.append("submission mode mismatch")

    for item in manifest["files"]:
        path = ROOT / item["path"]
        if not path.exists():
            errors.append(f"manifest file missing: {item['path']}")
        elif sha256(path) != item["sha256"]:
            errors.append(f"hash mismatch: {item['path']}")

    with zipfile.ZipFile(ROOT / "data/八家公司统一口径核心指标_最终验收.xlsx") as zf:
        bad = zf.testzip()
        if bad:
            errors.append(f"corrupt XLSX member: {bad}")

    metrics = json.loads(
        (ROOT / "data/八家公司统一口径核心指标.json").read_text(encoding="utf-8")
    )
    if metrics["financing_round_total"] != 18:
        errors.append("round total mismatch")
    if metrics["company_level_confirmed_pevc_legal_party_record_sum"] != 16:
        errors.append("PEVC legal party count mismatch")

    if errors:
        print(json.dumps({"status": "FAILED", "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    print("FINAL_SUBMISSION_VALIDATION_PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
