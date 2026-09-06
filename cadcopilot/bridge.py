"""Sequential file-queue worker running on FreeCAD's GUI thread."""

import json
import os
import time
import traceback
import FreeCAD as App
from PySide import QtCore
from .storage import Store, atomic_json, identifier
from .spec import normalize, preflight
from .model import build
from .geometry import validate, native_roundtrip
from .exporter import export_all, report


class Bridge:
    def __init__(self, root):
        self.store = Store(root)
        self.busy = False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)
        # Only one FreeCAD instance may own a workspace queue.
        self.lock = QtCore.QLockFile(str(self.store.root / "bridge.lock"))
        if not self.lock.tryLock(0):
            raise RuntimeError("Another bridge owns this workspace")
        self.recover()
        self.timer.start(250)
        self.heartbeat()

    def heartbeat(self):
        atomic_json(
            self.store.root / "heartbeat.json",
            {
                "time": time.time(),
                "pid": os.getpid(),
                "busy": self.busy,
                "freecad_version": ".".join(App.Version()[:3]),
            },
        )

    def expired(self, job):
        return (
            time.time() > job["deadline"]
            or (self.store.root / "cancelled" / f"{job['id']}.json").exists()
        )

    def recover(self):
        for path in (self.store.root / "running").glob("*.json"):
            try:
                job = json.loads(path.read_text())
                identifier(job["id"])
                result_path = self.store.root / "results" / path.name
                if not result_path.exists():
                    atomic_json(
                        result_path,
                        {
                            "status": "error",
                            "code": "bridge_restarted",
                            "revision_id": job["id"],
                            "errors": [
                                "FreeCAD stopped during this job; resubmit explicitly."
                            ],
                            "artifacts": {},
                        },
                    )
                path.unlink()
            except Exception:
                path.rename(path.with_suffix(".invalid"))

    def tick(self):
        if self.busy:
            return
        self.heartbeat()
        pending = sorted(
            (self.store.root / "queue").glob("*.json"),
            key=lambda p: p.stat().st_mtime_ns,
        )
        if not pending:
            return
        path = pending[0]
        running = self.store.root / "running" / path.name
        path.rename(running)
        self.busy = True
        self.heartbeat()
        doc = None
        job = {}
        documents_before = set(App.listDocuments())
        started = time.monotonic()
        try:
            job = json.loads(running.read_text())
            identifier(job["id"])
            if path.stem != job["id"]:
                raise ValueError("Job ID mismatch")
            if job["operation"] not in ("build", "revise", "validate", "export"):
                raise ValueError("Unsupported operation")
            if self.expired(job):
                raise TimeoutError("Job expired before execution")
            spec = normalize(job["spec"])
            out = self.store.revision(job["id"])
            out.mkdir()
            checks = preflight(spec)
            if not all(c["passed"] for c in checks):
                raise ValueError("Specification failed preflight")
            atomic_json(out / "spec.json", spec)
            if job["operation"] in ("build", "revise"):
                doc = build(spec, job["id"])
            else:
                source = self.store.revision(job["source"]) / "bracket.FCStd"
                doc = App.openDocument(str(source))
                # Export regenerates drawing in a fresh document to avoid duplicate views.
                if job["operation"] == "export":
                    App.closeDocument(doc.Name)
                    doc = build(spec, job["id"])
            checks, measured = validate(doc, spec)
            ok = all(c["passed"] for c in checks)
            artifacts = {}
            if ok and job["operation"] != "validate":
                artifacts, step_check = export_all(doc, spec, out)
                checks.append(step_check)
                App.closeDocument(doc.Name)
                doc, native_checks = native_roundtrip(out / "bracket.FCStd", spec)
                checks.extend(native_checks)
                ok = all(c["passed"] for c in checks)
            if self.expired(job):
                raise TimeoutError(
                    "Job expired during CAD operations; outputs are uncommitted"
                )
            result = {
                "status": "success" if ok else "rejected",
                "revision_id": job["id"],
                "source_revision": job.get("source"),
                "operation": job["operation"],
                "resolved_parameters": spec,
                "checks": checks,
                "measured_values": measured,
                "errors": [c["name"] for c in checks if not c["passed"]],
                "artifacts": artifacts,
                "elapsed_seconds": time.monotonic() - started,
                "freecad_version": ".".join(App.Version()[:3]),
            }
            artifacts.update(
                {
                    "report": str(out / "report.md"),
                    "result": str(out / "result.json"),
                    "spec": str(out / "spec.json"),
                }
            )
            report(result, out)
            atomic_json(out / "result.json", result)
            if self.expired(job):
                raise TimeoutError("Job expired before commit")
            # Promote before notifying the CLI so an immediate latest revision is coherent.
            if ok and job["operation"] in ("build", "revise"):
                atomic_json(self.store.root / "latest.json", {"revision_id": job["id"]})
            atomic_json(self.store.root / "results" / path.name, result)
        except Exception as exc:
            result = {
                "status": "error",
                "code": "job_timeout" if isinstance(exc, TimeoutError) else "cad_error",
                "revision_id": path.stem,
                "errors": [str(exc)],
                "artifacts": {},
                "elapsed_seconds": time.monotonic() - started,
            }
            atomic_json(self.store.root / "results" / path.name, result)
            (self.store.root / "results" / f"{path.stem}.log").write_text(
                traceback.format_exc()
            )
            App.Console.PrintError(str(exc) + "\n")
        finally:
            # A builder may fail after creating a document but before returning it.
            # Close only documents created by this job, never a pre-existing user view.
            if result["status"] != "success" or job.get("operation") == "validate":
                for name in set(App.listDocuments()) - documents_before:
                    App.closeDocument(name)
            running.unlink(missing_ok=True)
            self.busy = False
            self.heartbeat()

    def stop(self):
        self.timer.stop()
        (self.store.root / "heartbeat.json").unlink(missing_ok=True)
        self.lock.unlock()


_bridge = None


def start(root):
    global _bridge
    if _bridge:
        _bridge.stop()
    _bridge = Bridge(root)
    App.Console.PrintMessage(f"CAD Copilot bridge ready: {root}\n")
    return _bridge
