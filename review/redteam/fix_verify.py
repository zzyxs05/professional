#!/usr/bin/env python3
"""Fix verification runner for Findings F-01 / F-02 / F-03 / F-05.

For each case: verify sample sha256, run `cli.py analyze <sample> --no-evidence`,
parse the report, and check the case's defect condition (baseline phase) or
acceptance condition (regression phase).

Usage:
  python fix_verify.py --tool-root <apkaudit repo> --phase baseline
  python fix_verify.py --tool-root <apkaudit repo> --phase regression

Phases:
  baseline   - Finding reproduction check. PASS means the defect is still
               reproducible (this is what we report as 'reproduced').
  regression - Post-fix acceptance check. PASS means the fix meets the
               expected behaviour. Before the counterpart's fix this will
               mostly FAIL; that is the honest state (nothing is 'approved').

Rules:
  - read-only against the counterpart's repo; runs use --no-evidence.
  - every printed conclusion carries rule-pack version + timestamp.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

SAMPLES = {
    "F-01": {
        "file": "a13.apk",
        "sha256": "6d431e92d124466c299aa1fb17b9b498de47690b0c3fa6a17398d6850d359091",
        "rule": "R-NET-01",
        "defect": lambda notes, status, missing: not any("checkServerTrusted" in n for n in notes),
        "accept": lambda notes, status, missing: any("checkServerTrusted" in n for n in notes),
        "expect_text": "R-NET-01 notes must contain a checkServerTrusted entry",
    },
    "F-02": {
        "file": "a02.apk",
        "sha256": "cc1a7084243073914e3f236ca601b1ca94087bf6085291e8efbe29981390fb18",
        "rule": "R-MAN-02",
        "defect": lambda notes, status, missing: not any("RECORD_AUDIO" in n for n in notes),
        "accept": lambda notes, status, missing: any("RECORD_AUDIO" in n for n in notes),
        "expect_text": "R-MAN-02 notes must contain RECORD_AUDIO (uses-permission-sdk-23)",
    },
    "F-03": {
        "file": "a04.apk",
        "sha256": "c0fb952800ec19478072a42d233d46addb1b29cb1ad1b49a85649332e28523b0",
        "rule": "R-MAN-05",
        "defect": lambda notes, status, missing: status == "已确认",
        "accept": lambda notes, status, missing: status != "已确认" or any("enabled" in n or "disabled" in n for n in notes),
        "expect_text": "enabled=false receiver must not stay plain '已确认' (downgrade or note the disabled flag)",
    },
    "F-05": {
        "file": "v2_crossmethod.apk",
        "sha256": "3464015c37b913c544ffc4c210c8f39d22be5d97666e03b1d851e8add7290e93",
        "rule": "R-PERM-01",
        "defect": lambda notes, status, missing: status == "待复核" and not missing and not any("链" in n for n in notes),
        "accept": lambda notes, status, missing: status == "已确认" or bool(missing) or any("链" in n for n in notes),
        "expect_text": "Runnable cross-method chain: either upgraded to 已确认, or missing_evidence/notes declare the unresolved chain",
    },
}


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_case(tool_root: str, sample: str, env: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, "cli.py", "analyze", sample, "--no-evidence"],
        cwd=tool_root, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = proc.stdout + proc.stderr
    m = re.search(r"\[run\]\s+(RUN-[0-9a-zA-Z\-]+)", out)
    run_id = m.group(1) if m else ""
    m2 = re.search(r"\[toolchain\]\s+(.*)", out)
    toolchain = m2.group(1).strip() if m2 else ""
    temp = env.get("TEMP") or tempfile.gettempdir()
    reports = glob.glob(os.path.join(temp, "apkaudit_trial_*", run_id, "report.json"))
    if not reports:
        return {"run_id": run_id, "error": "report.json not found", "raw_tail": out[-500:]}
    with open(sorted(reports)[-1], encoding="utf-8") as f:
        d = json.load(f)
    return {
        "run_id": run_id,
        "toolchain": toolchain,
        "rule_pack": d.get("versions", {}).get("rule_pack"),
        "channel_b_model": d.get("versions", {}).get("channel_b_model"),
        "conclusions": [
            {
                "criterion_id": c.get("criterion_id"),
                "status": c.get("status"),
                "location": c.get("location"),
                "notes": c.get("notes"),
                "missing_evidence": c.get("missing_evidence"),
            }
            for c in d.get("conclusions", [])
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool-root", required=True)
    ap.add_argument("--phase", choices=["baseline", "regression"], required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    sample_dir = os.path.join(here, "samples")
    env = dict(os.environ, PYTHONUTF8="1")
    result = {
        "phase": args.phase,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool_root": os.path.abspath(args.tool_root),
        "note": "All runs use --no-evidence. Nothing is written into the counterpart's evidence/.",
        "cases": [],
    }

    for fid, spec in SAMPLES.items():
        path = os.path.join(sample_dir, spec["file"])
        actual = sha256_of(path) if os.path.exists(path) else None
        entry = {
            "finding": fid,
            "sample": spec["file"],
            "expected_sha256": spec["sha256"],
            "actual_sha256": actual,
            "sha256_ok": actual == spec["sha256"],
            "expectation": spec["expect_text"],
        }
        if not entry["sha256_ok"]:
            entry["verdict"] = "SHA256_MISMATCH"
            result["cases"].append(entry)
            print(f"[{fid}] SHA256 MISMATCH - skip run")
            continue
        print(f"[{fid}] running...", flush=True)
        run = run_case(args.tool_root, path, env)
        entry["run"] = run
        if "error" in run:
            entry["verdict"] = "RUN_ERROR"
        else:
            concl = {c["criterion_id"]: c for c in run["conclusions"]}
            c = concl.get(spec["rule"], {})
            notes = c.get("notes") or []
            status = c.get("status")
            missing = c.get("missing_evidence") or []
            entry["observed"] = {"rule": spec["rule"], "status": status, "notes": notes, "missing_evidence": missing}
            cond = spec["defect"] if args.phase == "baseline" else spec["accept"]
            ok = bool(cond(notes, status, missing))
            entry["verdict"] = ("REPRODUCED" if ok else "NOT_REPRODUCED") if args.phase == "baseline" \
                else ("PASS" if ok else "FAIL")
        result["cases"].append(entry)
        print(f"[{fid}] {entry['verdict']}")

    out = args.out or os.path.join(here, f"fix_verification_result_{args.phase}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("saved:", out)
    ok = sum(1 for c in result["cases"] if c["verdict"] in ("REPRODUCED", "PASS"))
    print(f"summary: {ok}/{len(result['cases'])} ok (phase={args.phase})")


if __name__ == "__main__":
    main()
