#!/usr/bin/env python3
"""Replay ten fixed design scenarios through the real bridge. No LLM is called."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cadcopilot.spec import normalize, read_json, merge_patch
from cadcopilot.storage import atomic_json

SCENARIOS = [
    ("baseline", "Create the supplied sensor bracket.", {}, "success", None),
    (
        "width84",
        "Make the bracket 84 mm wide.",
        {"bracket": {"width": 84}},
        "success",
        None,
    ),
    (
        "depth44",
        "Increase base depth to 44 mm.",
        {"bracket": {"depth": 44}},
        "success",
        None,
    ),
    (
        "height54",
        "Increase height to 54 mm.",
        {"bracket": {"height": 54}},
        "success",
        None,
    ),
    (
        "thickness7",
        "Use 7 mm plate thickness.",
        {"bracket": {"thickness": 7}},
        "success",
        None,
    ),
    (
        "spacing50",
        "Change base-hole spacing to 50 mm; preserve sensor interface.",
        {"base_holes": {"spacing": 50}},
        "success",
        None,
    ),
    (
        "too_narrow",
        "Use 60 mm width and 50 mm base-hole spacing.",
        {"base_holes": {"spacing": 50}, "bracket": {"width": 60}},
        "rejected",
        "base_edge_distance",
    ),
    (
        "radius100",
        "Set the internal corner radius to 100 mm.",
        {"bracket": {"corner_radius": 100}},
        "rejected",
        "corner_radius",
    ),
    (
        "interference",
        "Place the harness keepout through the base.",
        {
            "obstacles": [
                {"name": "harness_keepout", "origin": [30, 15, 2], "size": [12, 10, 15]}
            ]
        },
        "rejected",
        "bracket_to_harness_keepout_no_interference",
    ),
    (
        "clearance",
        "Put the harness keepout 1 mm from the base.",
        {
            "obstacles": [
                {"name": "harness_keepout", "origin": [41, 15, 0], "size": [12, 10, 15]}
            ]
        },
        "rejected",
        "bracket_to_harness_keepout_clearance",
    ),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, default=ROOT / ".cadcopilot")
    p.add_argument("--output", type=Path, default=ROOT / "artifacts/benchmark")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    baseline = normalize(read_json(ROOT / "examples/sensor-bracket.json"))
    rows = []
    for name, prompt, patch, expected, check in SCENARIOS:
        path = args.output / (name + ".json")
        atomic_json(path, merge_patch(baseline, patch))
        start = time.monotonic()
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "cadcopilot",
                "--workspace",
                str(args.workspace),
                "build",
                "--spec",
                str(path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=140,
        )
        try:
            result = json.loads(proc.stdout)
        except ValueError:
            result = {"status": "error", "errors": [proc.stderr or proc.stdout]}
        matched = result["status"] == expected and (
            check is None or check in result.get("errors", [])
        )
        row = {
            "scenario": name,
            "prompt": prompt,
            "expected": expected,
            "observed": result["status"],
            "passed": matched,
            "first_attempt_success": matched,
            "eventual_success": matched,
            "elapsed_seconds": round(time.monotonic() - start, 3),
            "retries": 0,
            "manual_interventions": 0,
            "revision_id": result.get("revision_id"),
            "errors": result.get("errors", []),
        }
        rows.append(row)
        atomic_json(args.output / (name + "-result.json"), result)
        print(
            name,
            result["status"],
            row["elapsed_seconds"],
            "PASS" if matched else "FAIL",
            flush=True,
        )
    summary = {
        "benchmark_type": "scripted CLI replay of fixed engineering prompts; not an independent conversational-agent evaluation",
        "scenario_count": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "first_attempt_success_rate": sum(r["first_attempt_success"] for r in rows)
        / len(rows),
        "eventual_success_rate": sum(r["eventual_success"] for r in rows) / len(rows),
        "manual_baseline_seconds": None,
        "scenarios": rows,
    }
    atomic_json(args.output / "summary.json", summary)
    text = [
        "# CAD workflow benchmark",
        "",
        summary["benchmark_type"],
        "",
        "Times include CLI, queue, CAD execution and exports. They exclude natural-language interpretation and FreeCAD startup. No manual timing baseline has been collected.",
        "",
        "| Scenario | Expected | Observed | Seconds | Pass |",
        "|---|---|---|---:|---|",
    ]
    text += [
        f"| {r['scenario']} | {r['expected']} | {r['observed']} | {r['elapsed_seconds']} | {r['passed']} |"
        for r in rows
    ]
    (args.output / "summary.md").write_text("\n".join(text) + "\n")
    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
