import argparse
import json
import math
import sys
from pathlib import Path
from .spec import ROOT, SpecError, read_json, normalize, merge_patch, preflight
from .storage import Store, JobError


def parser():
    p = argparse.ArgumentParser(description="Codex-driven FreeCAD bracket automation")
    p.add_argument("--workspace", type=Path, default=ROOT / ".cadcopilot")
    p.add_argument("--timeout", type=float, default=120)
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    choice = b.add_mutually_exclusive_group(required=True)
    choice.add_argument("--spec", type=Path)
    choice.add_argument("--preset", choices=["sensor-bracket"])
    b.add_argument("--preflight-only", action="store_true")
    r = sub.add_parser("revise")
    r.add_argument("--revision", default="latest")
    r.add_argument("--patch", type=Path, required=True)
    r.add_argument("--preflight-only", action="store_true")
    for name in ("validate", "export"):
        q = sub.add_parser(name)
        q.add_argument("--revision", default="latest")
    sub.add_parser("status")
    return p


def execute(args):
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise SpecError("timeout must be a positive finite number")
    store = Store(args.workspace)
    if args.command == "status":
        return {
            "status": "info",
            "workspace": str(store.root),
            "bridge": store.heartbeat(),
        }
    source = None
    if args.command == "build":
        spec = normalize(
            read_json(args.spec or ROOT / "examples" / f"{args.preset}.json")
        )
    else:
        source = store.latest() if args.revision == "latest" else args.revision
        spec = store.load_spec(source)
        if args.command == "revise":
            spec = merge_patch(spec, read_json(args.patch))
    checks = preflight(spec)
    if not all(c["passed"] for c in checks):
        return {
            "status": "rejected",
            "revision_id": None,
            "source_revision": source,
            "resolved_parameters": spec,
            "checks": checks,
            "measured_values": {},
            "errors": [c["name"] for c in checks if not c["passed"]],
            "artifacts": {},
        }
    if getattr(args, "preflight_only", False):
        return {
            "status": "preflight_passed",
            "resolved_parameters": spec,
            "checks": checks,
            "detail": "Geometry has not been built or validated.",
        }
    return store.wait(store.enqueue(args.command, spec, source, args.timeout))


def main(argv=None):
    try:
        result = execute(parser().parse_args(argv))
    except (SpecError, JobError) as exc:
        result = {
            "status": "error",
            "code": exc.code,
            "errors": [str(exc)],
            "artifacts": {},
        }
    except OSError as exc:
        result = {
            "status": "error",
            "code": "io_error",
            "errors": [str(exc)],
            "artifacts": {},
        }
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["status"] in ("success", "info", "preflight_passed") else 2


if __name__ == "__main__":
    sys.exit(main())
