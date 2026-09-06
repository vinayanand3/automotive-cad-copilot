"""Checks measured from Open CASCADE solids, never from screenshots."""

import FreeCAD as App
import Part
from .spec import check, preflight, TOLERANCE_MM


def bbox(shape):
    b = shape.BoundBox
    return {
        "origin": [b.XMin, b.YMin, b.ZMin],
        "size": [b.XLength, b.YLength, b.ZLength],
    }


def cylinder_holes(shape, direction):
    found = []
    for face in shape.Faces:
        surface = face.Surface
        if not isinstance(surface, Part.Cylinder):
            continue
        axis = surface.Axis
        if abs(abs(axis.dot(App.Vector(*direction))) - 1) > 1e-6:
            continue
        c = surface.Center
        # Base cylinders are parallel Z; sensor cylinders are parallel Y.
        pair = (c.x, c.y) if direction[2] else (c.x, c.z)
        value = [round(pair[0], 8), round(pair[1], 8), round(surface.Radius * 2, 8)]
        if value not in found:
            found.append(value)
    return sorted(found)


def validate(doc, s):
    shape = doc.Bracket.Shape
    checks = preflight(s)
    valid = not shape.isNull() and shape.isValid() and len(shape.Solids) == 1
    checks.append(check("valid_single_solid", valid, len(shape.Solids), 1))
    if not valid:
        return checks, {}
    measured = {
        "bounding_box": bbox(shape),
        "volume_mm3": shape.Volume,
        "mass_g": shape.Volume * s["material"]["density_kg_m3"] / 1e6,
        "base_holes": cylinder_holes(shape, (0, 0, 1)),
        "sensor_holes": cylinder_holes(shape, (0, 1, 0)),
        "clearances_mm": {},
    }
    b = s["bracket"]
    for actual, key in zip(
        measured["bounding_box"]["size"], ("width", "depth", "height")
    ):
        checks.append(
            check(
                f"measured_{key}", abs(actual - b[key]) <= TOLERANCE_MM, actual, b[key]
            )
        )
    for name, ordinate in (("base", "y"), ("sensor", "z")):
        h = s[name + "_holes"]
        expected = [
            [sign * h["spacing"] / 2, h[ordinate], h["diameter"]] for sign in (-1, 1)
        ]
        actual = measured[name + "_holes"]
        ok = len(actual) == 2 and all(
            abs(a - e) <= TOLERANCE_MM
            for aa, ee in zip(actual, expected)
            for a, e in zip(aa, ee)
        )
        checks.append(check(f"measured_{name}_holes", ok, actual, expected))
        if len(actual) == 2:
            lim = b["depth"] if name == "base" else b["height"]
            edge = min(
                min(
                    b["width"] / 2 - abs(x) - diam / 2,
                    pos - b["thickness"] - b["corner_radius"] - diam / 2,
                    lim - pos - diam / 2,
                )
                for x, pos, diam in actual
            )
            checks.append(
                check(
                    f"measured_{name}_edge_distance",
                    edge >= s["requirements"]["min_edge_distance"] - 1e-7,
                    edge,
                    s["requirements"]["min_edge_distance"],
                )
            )
    # Planar faces expose actual plate thickness, fillet cylinders expose actual radius.
    for axis, name in ((2, "base"), (1, "upright")):
        positions = []
        for face in shape.Faces:
            if isinstance(face.Surface, Part.Plane):
                normal = face.normalAt(0, 0)
                if abs(abs((normal.x, normal.y, normal.z)[axis]) - 1) < 1e-6:
                    positions.append(
                        (face.CenterOfMass.x, face.CenterOfMass.y, face.CenterOfMass.z)[
                            axis
                        ]
                    )
        ok = any(abs(p - b["thickness"]) <= TOLERANCE_MM for p in positions) and any(
            abs(p) <= TOLERANCE_MM for p in positions
        )
        checks.append(
            check(
                f"measured_{name}_thickness",
                ok,
                sorted(set(round(p, 6) for p in positions)),
                b["thickness"],
            )
        )
    radii = [
        f.Surface.Radius
        for f in shape.Faces
        if isinstance(f.Surface, Part.Cylinder)
        and abs(abs(f.Surface.Axis.x) - 1) < 1e-6
    ]
    checks.append(
        check(
            "measured_corner_radius",
            any(abs(v - b["corner_radius"]) <= TOLERANCE_MM for v in radii),
            radii,
            b["corner_radius"],
        )
    )
    for name in ("BaseSketch", "UprightSketch", "BaseHoleSketch", "SensorHoleSketch"):
        sk = doc.getObject(name)
        checks.append(
            check(
                f"fully_constrained_{name}",
                sk.FullyConstrained,
                sk.FullyConstrained,
                True,
            )
        )
    sensor = doc.Sensor.Shape
    overlap = shape.common(sensor).Volume
    contact_distance = shape.distToShape(sensor)[0]
    checks.append(
        check("sensor_no_interference", overlap <= 1e-6, overlap, "<= 0.000001 mm3")
    )
    checks.append(
        check(
            "sensor_intended_contact",
            contact_distance <= TOLERANCE_MM,
            contact_distance,
            0,
        )
    )
    measured["clearances_mm"]["sensor_mounting_contact"] = contact_distance
    env = s["envelope"]
    for label, objshape in (("bracket", shape), ("sensor", sensor)):
        bounds = bbox(objshape)
        inside = all(
            o >= lo - TOLERANCE_MM and o + size <= lo + span + TOLERANCE_MM
            for o, size, lo, span in zip(
                bounds["origin"], bounds["size"], env["origin"], env["size"]
            )
        )
        checks.append(check(f"{label}_inside_envelope", inside, bounds, env))
    for i, obstacle in enumerate(s["obstacles"]):
        obs = doc.getObject(f"Obstacle{i}").Shape
        for label, solid in (("bracket", shape), ("sensor", sensor)):
            volume = solid.common(obs).Volume
            distance = solid.distToShape(obs)[0]
            key = f"{label}_to_{obstacle['name']}"
            measured["clearances_mm"][key] = distance
            checks.append(
                check(
                    key + "_no_interference", volume <= 1e-6, volume, "<= 0.000001 mm3"
                )
            )
            checks.append(
                check(
                    key + "_clearance",
                    distance >= s["requirements"]["min_clearance"] - 1e-7,
                    distance,
                    s["requirements"]["min_clearance"],
                )
            )
    return checks, measured


def roundtrip_step(shape, path):
    shape.exportStep(str(path))
    imported = Part.Shape()
    imported.read(str(path))
    a, b = bbox(shape), bbox(imported)
    delta = max(
        abs(x - y) for key in ("origin", "size") for x, y in zip(a[key], b[key])
    )
    volume_error = abs(imported.Volume - shape.Volume)
    return check(
        "step_roundtrip",
        imported.isValid()
        and len(imported.Solids) == len(shape.Solids)
        and delta <= TOLERANCE_MM
        and volume_error <= max(0.001, shape.Volume * 1e-6),
        {
            "solid_count": len(imported.Solids),
            "max_bbox_error_mm": delta,
            "volume_error_mm3": volume_error,
        },
        "same solids, bbox <= 0.01 mm, volume <= max(0.001 mm3, 1 ppm)",
    )


def native_roundtrip(path, spec):
    """Reopen from disk, exercise native parameter expressions, discard edits."""
    doc = App.openDocument(str(path))
    checks, _ = validate(doc, spec)
    original_ok = all(c["passed"] for c in checks)
    initial_sensor = cylinder_holes(doc.Bracket.Shape, (0, 1, 0))
    width = spec["bracket"]["width"] + 2
    spacing = spec["base_holes"]["spacing"] + 2
    doc.Parameters.Width = width
    doc.Parameters.BaseSpacing = spacing
    doc.recompute()
    actual = cylinder_holes(doc.Bracket.Shape, (0, 0, 1))
    ok = (
        doc.Bracket.Shape.isValid()
        and len(doc.Bracket.Shape.Solids) == 1
        and abs(doc.Bracket.Shape.BoundBox.XLength - width) <= TOLERANCE_MM
    )
    ok = (
        ok
        and len(actual) == 2
        and abs(actual[1][0] - actual[0][0] - spacing) <= TOLERANCE_MM
    )
    ok = ok and cylinder_holes(doc.Bracket.Shape, (0, 1, 0)) == initial_sensor
    states = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
    ok = ok and not states
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    return doc, [
        check("native_reopen", original_ok, original_ok, True),
        check(
            "native_edit_recompute",
            ok,
            {"width_mm": width, "base_spacing_mm": spacing, "errors": states},
            "valid recompute and sensor holes unchanged; edits discarded",
        ),
    ]
