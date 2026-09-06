import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from cadcopilot.spec import (
    ROOT,
    SpecError,
    normalize,
    merge_patch,
    preflight,
    read_json,
)
from cadcopilot.storage import Store, JobError, atomic_json
from cadcopilot.cli import main
from contextlib import redirect_stdout
from io import StringIO


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.spec = normalize(read_json(ROOT / "examples/sensor-bracket.json"))

    def test_baseline_and_five_variants(self):
        for patch in (
            {},
            {"bracket": {"width": 84}},
            {"bracket": {"depth": 44}},
            {"bracket": {"height": 54}},
            {"bracket": {"thickness": 7}},
            {"base_holes": {"spacing": 50}},
        ):
            with self.subTest(patch=patch):
                self.assertTrue(
                    all(c["passed"] for c in preflight(merge_patch(self.spec, patch)))
                )

    def test_preserves_sensor_interface(self):
        rev = merge_patch(self.spec, {"base_holes": {"spacing": 50}})
        self.assertEqual(rev["sensor_holes"], self.spec["sensor_holes"])
        self.assertEqual(rev["sensor"], self.spec["sensor"])
        self.assertEqual(self.spec["base_holes"]["spacing"], 40)

    def test_conflicting_width(self):
        rev = merge_patch(
            self.spec, {"base_holes": {"spacing": 50}, "bracket": {"width": 60}}
        )
        failed = [c for c in preflight(rev) if not c["passed"]]
        self.assertEqual(failed[0]["name"], "base_edge_distance")
        self.assertAlmostEqual(failed[0]["actual"], 1.7)

    def test_invalid_radius(self):
        rev = merge_patch(self.spec, {"bracket": {"corner_radius": 100}})
        self.assertFalse(
            next(c for c in preflight(rev) if c["name"] == "corner_radius")["passed"]
        )

    def test_missing_field_requests_clarification(self):
        del self.spec["base_holes"]["diameter"]
        with self.assertRaises(SpecError) as cm:
            normalize(self.spec)
        self.assertEqual(cm.exception.code, "needs_clarification")

    def test_unknown_fields_rejected(self):
        with self.assertRaises(SpecError):
            merge_patch(self.spec, {"bracket": {"widht": 2}})

    def test_units_cannot_change_in_patch(self):
        with self.assertRaises(SpecError):
            merge_patch(self.spec, {"units": "in"})

    def test_inches_conversion(self):
        inches = copy.deepcopy(self.spec)
        inches["units"] = "in"
        for group in ("bracket", "base_holes", "sensor_holes", "requirements"):
            for k in inches[group]:
                inches[group][k] /= 25.4
        for box in [inches["sensor"], inches["envelope"]] + inches["obstacles"]:
            for k in ("origin", "size"):
                box[k] = [v / 25.4 for v in box[k]]
        result = normalize(inches)
        self.assertAlmostEqual(result["bracket"]["width"], 80)
        self.assertAlmostEqual(result["sensor"]["origin"][1], -18)
        self.assertEqual(result["material"], self.spec["material"])

    def test_nonfinite_bool_and_negative(self):
        for value in (float("nan"), float("inf"), True, -1, 0, "80"):
            with self.subTest(value=value), self.assertRaises(SpecError):
                merge_patch(self.spec, {"bracket": {"width": value}})

    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"width":')
            with self.assertRaises(SpecError) as cm:
                read_json(path)
            self.assertEqual(cm.exception.code, "malformed_input")

    def test_obstacle_contract(self):
        with self.assertRaises(SpecError):
            merge_patch(self.spec, {"obstacles": [self.spec["obstacles"][0]] * 2})

    def test_sensor_must_contact_mount(self):
        rev = merge_patch(self.spec, {"sensor": {"origin": [-18, -19, 20]}})
        self.assertFalse(
            next(c for c in preflight(rev) if c["name"] == "sensor_mounting_contact")[
                "passed"
            ]
        )


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)

    def test_unavailable(self):
        with self.assertRaises(JobError) as cm:
            self.store.enqueue("build")
        self.assertEqual(cm.exception.code, "freecad_unavailable")

    def test_stale_heartbeat(self):
        atomic_json(self.store.root / "heartbeat.json", {"time": time.time() - 11})
        with self.assertRaises(JobError):
            self.store.enqueue("build")

    def test_busy(self):
        atomic_json(
            self.store.root / "heartbeat.json", {"time": time.time(), "busy": True}
        )
        with self.assertRaises(JobError) as cm:
            self.store.enqueue("build")
        self.assertEqual(cm.exception.code, "bridge_busy")

    def test_timeout_retains_last_success(self):
        old = "a" * 32
        atomic_json(self.store.root / "latest.json", {"revision_id": old})
        atomic_json(self.store.root / "heartbeat.json", {"time": time.time()})
        job = self.store.enqueue("build", timeout=0.01)
        with self.assertRaises(JobError) as cm:
            self.store.wait(job)
        self.assertEqual(cm.exception.code, "job_timeout")
        self.assertTrue((self.store.root / "cancelled" / f"{job['id']}.json").exists())
        self.assertEqual(self.store.latest(), old)

    def test_atomic_result(self):
        atomic_json(self.store.root / "heartbeat.json", {"time": time.time()})
        job = self.store.enqueue("validate")
        atomic_json(
            self.store.root / "results" / f"{job['id']}.json", {"status": "success"}
        )
        self.assertEqual(self.store.wait(job)["status"], "success")
        self.assertEqual(list(self.store.root.rglob("*.tmp")), [])

    def test_path_traversal(self):
        with self.assertRaises(JobError):
            self.store.revision("../../etc")

    def test_cli_structured_failure(self):
        out = StringIO()
        with redirect_stdout(out):
            code = main(
                ["--workspace", self.tmp.name, "build", "--preset", "sensor-bracket"]
            )
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())["code"], "freecad_unavailable")


if __name__ == "__main__":
    unittest.main()
