#!/usr/bin/env python3
"""Exercise revision retention, native validation, export and a real timeout."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cadcopilot.storage import atomic_json


def run(*args):
    p = subprocess.run(
        [sys.executable, "-m", "cadcopilot", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=140,
    )
    return json.loads(p.stdout)


def main():
    evidence = {}
    baseline = run("build", "--preset", "sensor-bracket")
    assert baseline["status"] == "success", baseline
    rev = run(
        "revise",
        "--revision",
        baseline["revision_id"],
        "--patch",
        "examples/wider-spacing.json",
    )
    assert rev["status"] == "success", rev
    assert (
        rev["measured_values"]["sensor_holes"]
        == baseline["measured_values"]["sensor_holes"]
    )
    assert (
        rev["resolved_parameters"]["sensor"]
        == baseline["resolved_parameters"]["sensor"]
    )
    rejected = run(
        "revise",
        "--revision",
        rev["revision_id"],
        "--patch",
        "examples/too-narrow.json",
    )
    assert (
        rejected["status"] == "rejected" and "base_edge_distance" in rejected["errors"]
    )
    latest = lambda: json.loads((ROOT / ".cadcopilot/latest.json").read_text())[
        "revision_id"
    ]
    assert latest() == rev["revision_id"]
    validation = run("validate", "--revision", rev["revision_id"])
    assert validation["status"] == "success", validation
    exported = run("export", "--revision", rev["revision_id"])
    assert exported["status"] == "success", exported
    assert latest() == rev["revision_id"]
    timed_out = run("--timeout", "0.001", "build", "--preset", "sensor-bracket")
    assert timed_out["code"] == "job_timeout", timed_out
    time.sleep(0.5)
    assert latest() == rev["revision_id"]
    recovery = run("build", "--preset", "sensor-bracket")
    assert recovery["status"] == "success", recovery
    evidence = {
        "status": "passed",
        "checks": [
            "revision_preserves_sensor_interface",
            "rejection_retains_latest",
            "native_validate",
            "export_preserves_source",
            "timeout_retains_latest",
            "build_after_timeout",
        ],
        "baseline": baseline,
        "revision": rev,
        "rejection": rejected,
        "timeout": timed_out,
        "recovery": recovery,
    }
    atomic_json(ROOT / "artifacts/workflow/result.json", evidence)
    print(json.dumps({"status": "passed", "checks": evidence["checks"]}, indent=2))


if __name__ == "__main__":
    main()
