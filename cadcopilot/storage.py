"""Atomic queue files and immutable per-job artifacts."""

import json
import os
import re
import time
import uuid
from pathlib import Path


class JobError(RuntimeError):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with tmp.open("x") as f:
            json.dump(value, f, indent=2, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def identifier(value):
    if not re.fullmatch(r"[a-f0-9]{32}", value):
        raise JobError("Invalid revision/job ID", "invalid_id")
    return value


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        for name in ("queue", "running", "results", "cancelled", "revisions"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def revision(self, rev):
        return self.root / "revisions" / identifier(rev)

    def heartbeat(self):
        try:
            return json.loads((self.root / "heartbeat.json").read_text())
        except (OSError, ValueError):
            return {}

    def enqueue(self, operation, spec=None, source=None, timeout=120):
        hb = self.heartbeat()
        if time.time() - hb.get("time", 0) > 10:
            raise JobError(
                "FreeCAD bridge is unavailable. Start freecad/StartCopilot.FCMacro in FreeCAD.",
                "freecad_unavailable",
            )
        if hb.get("busy"):
            raise JobError(
                "FreeCAD bridge is processing another job. Retry when it completes.",
                "bridge_busy",
            )
        job_id = uuid.uuid4().hex
        now = time.time()
        job = {
            "id": job_id,
            "operation": operation,
            "spec": spec,
            "source": source,
            "created_at": now,
            "deadline": now + timeout,
        }
        atomic_json(self.root / "queue" / f"{job_id}.json", job)
        return job

    def wait(self, job):
        path = self.root / "results" / f"{job['id']}.json"
        while time.time() <= job["deadline"]:
            if path.exists():
                return json.loads(path.read_text())
            time.sleep(0.1)
        atomic_json(
            self.root / "cancelled" / f"{job['id']}.json", {"time": time.time()}
        )
        # A result committed before expiry remains authoritative.
        if path.exists():
            return json.loads(path.read_text())
        raise JobError(
            f"Job {job['id']} timed out; last successful revision is unchanged.",
            "job_timeout",
        )

    def latest(self):
        try:
            return json.loads((self.root / "latest.json").read_text())["revision_id"]
        except (OSError, ValueError, KeyError) as exc:
            raise JobError("No successful revision exists", "missing_revision") from exc

    def load_spec(self, rev):
        try:
            return json.loads((self.revision(rev) / "spec.json").read_text())
        except (OSError, ValueError) as exc:
            raise JobError(
                f"Revision {rev} is unavailable", "missing_revision"
            ) from exc
