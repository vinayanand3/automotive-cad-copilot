"""Strict input contract and geometric preflight. All lengths normalize to mm."""

import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE_MM = 0.01


class SpecError(ValueError):
    def __init__(self, message, code="invalid_spec"):
        super().__init__(message)
        self.code = code


def read_json(path):
    try:
        return json.loads(
            Path(path).read_text(),
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)),
        )
    except (ValueError, OSError) as exc:
        raise SpecError(f"Cannot read JSON: {exc}", "malformed_input") from exc


def keys(obj, required, where):
    if not isinstance(obj, dict):
        raise SpecError(f"{where} must be an object")
    missing, extra = set(required) - obj.keys(), obj.keys() - set(required)
    if missing:
        raise SpecError(
            f"Missing {where}: {', '.join(sorted(missing))}", "needs_clarification"
        )
    if extra:
        raise SpecError(f"Unknown {where}: {', '.join(sorted(extra))}")


def number(v, label, positive=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise SpecError(f"{label} must be a finite number")
    if positive and v <= 0:
        raise SpecError(f"{label} must be positive")
    return float(v)


def normalize(raw):
    s = copy.deepcopy(raw)
    keys(
        s,
        [
            "schema_version",
            "units",
            "bracket",
            "base_holes",
            "sensor_holes",
            "sensor",
            "obstacles",
            "envelope",
            "requirements",
            "material",
        ],
        "spec",
    )
    if type(s["schema_version"]) is not int or s["schema_version"] != 1:
        raise SpecError("schema_version must be 1")
    if s["units"] not in ("mm", "in"):
        raise SpecError("units must be mm or in")
    scale = 25.4 if s["units"] == "in" else 1
    groups = {
        "bracket": ["width", "depth", "height", "thickness", "corner_radius"],
        "base_holes": ["spacing", "y", "diameter"],
        "sensor_holes": ["spacing", "z", "diameter"],
        "requirements": ["min_edge_distance", "min_clearance"],
    }
    for group, fields in groups.items():
        keys(s[group], fields, group)
        for field in fields:
            s[group][field] = scale * number(s[group][field], f"{group}.{field}", True)
    if not isinstance(s["obstacles"], list):
        raise SpecError("obstacles must be an array")
    names = set()
    for label, box in [("sensor", s["sensor"]), ("envelope", s["envelope"])] + [
        ("obstacle", b) for b in s["obstacles"]
    ]:
        keys(box, ["origin", "size"] + (["name"] if label == "obstacle" else []), label)
        if label == "obstacle":
            name = box["name"]
            if not isinstance(name, str) or not name or name in names:
                raise SpecError("Obstacle names must be unique nonempty strings")
            names.add(name)
        for field in ("origin", "size"):
            if not isinstance(box[field], list) or len(box[field]) != 3:
                raise SpecError(f"{label}.{field} must have three numbers")
            box[field] = [
                scale * number(v, f"{label}.{field}", field == "size")
                for v in box[field]
            ]
    keys(s["material"], ["name", "density_kg_m3"], "material")
    if not isinstance(s["material"]["name"], str) or not s["material"]["name"]:
        raise SpecError("material.name must be a nonempty string")
    s["material"]["density_kg_m3"] = number(
        s["material"]["density_kg_m3"], "density", True
    )
    s["units"] = "mm"
    return s


def merge_patch(base, patch):
    if not isinstance(patch, dict):
        raise SpecError("Revision patch must be an object")
    if "units" in patch or "schema_version" in patch:
        raise SpecError(
            "Revision patches use mm and cannot change units or schema_version"
        )

    def merge(a, b):
        out = copy.deepcopy(a)
        for k, v in b.items():
            if k not in a:
                raise SpecError(f"Unknown revision field: {k}")
            out[k] = (
                merge(a[k], v)
                if isinstance(a[k], dict) and isinstance(v, dict)
                else copy.deepcopy(v)
            )
        return out

    return normalize(merge(base, patch))


def check(name, passed, actual=None, required=None, detail=""):
    return {
        "name": name,
        "passed": bool(passed),
        "actual": actual,
        "required": required,
        "detail": detail,
    }


def preflight(s):
    b, h, sh, r = s["bracket"], s["base_holes"], s["sensor_holes"], s["requirements"]
    w, d, z, t, f = (
        b[k] for k in ("width", "depth", "height", "thickness", "corner_radius")
    )
    checks = [check("bracket_proportions", t < min(d, z), t, f"< {min(d,z)}")]
    checks.append(
        check(
            "corner_radius",
            f < min(d - t, z - t) and f <= t,
            f,
            f"<= thickness {t} and < internal legs",
        )
    )
    for name, holes, position, limit in [
        ("base", h, h["y"], d),
        ("sensor", sh, sh["z"], z),
    ]:
        radius = holes["diameter"] / 2
        edge = min(
            (w - holes["spacing"]) / 2 - radius,
            position - t - f - radius,
            limit - position - radius,
        )
        checks.append(
            check(
                f"{name}_edge_distance",
                edge >= r["min_edge_distance"],
                edge,
                r["min_edge_distance"],
                "Distance from hole rim to outer boundary or inner fillet tangent.",
            )
        )
        gap = holes["spacing"] - holes["diameter"]
        checks.append(
            check(
                f"{name}_hole_separation",
                gap >= r["min_edge_distance"],
                gap,
                r["min_edge_distance"],
            )
        )
    # Sensor contact is deliberately on the rear mounting face y=0.
    so, ss = s["sensor"]["origin"], s["sensor"]["size"]
    contact = abs(so[1] + ss[1]) <= 1e-7
    checks.append(
        check(
            "sensor_mounting_contact",
            contact,
            so[1] + ss[1],
            0,
            "Sensor front face must meet rear bracket face y=0.",
        )
    )
    for x in (-sh["spacing"] / 2, sh["spacing"] / 2):
        rr = sh["diameter"] / 2
        fit = (
            so[0] + rr <= x <= so[0] + ss[0] - rr
            and so[2] + rr <= sh["z"] <= so[2] + ss[2] - rr
        )
        checks.append(
            check(
                f"sensor_interface_{x:g}",
                fit,
                [x, sh["z"]],
                "Hole contained in sensor mounting face",
            )
        )
    return checks
