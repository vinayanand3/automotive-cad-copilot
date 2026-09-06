"""Native FreeCAD features. Import only from FreeCAD's Python runtime."""

import FreeCAD as App
import Part
import Sketcher

PARAMETERS = {
    "Width": ("bracket", "width"),
    "Depth": ("bracket", "depth"),
    "Height": ("bracket", "height"),
    "Thickness": ("bracket", "thickness"),
    "CornerRadius": ("bracket", "corner_radius"),
    "BaseSpacing": ("base_holes", "spacing"),
    "BaseY": ("base_holes", "y"),
    "BaseDiameter": ("base_holes", "diameter"),
    "SensorSpacing": ("sensor_holes", "spacing"),
    "SensorZ": ("sensor_holes", "z"),
    "SensorDiameter": ("sensor_holes", "diameter"),
}


def recompute(doc):
    doc.recompute()
    bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
    if bad:
        raise RuntimeError("FreeCAD recompute failed: " + ", ".join(bad))


def dimension(sketch, constraint, expression=None):
    index = sketch.addConstraint(constraint)
    if expression:
        sketch.setExpression(f"Constraints[{index}]", expression)
    return index


def rectangle(body, name, width, depth, width_expr, depth_expr):
    sk = body.newObject("Sketcher::SketchObject", name)
    pts = [(-width / 2, 0), (width / 2, 0), (width / 2, depth), (-width / 2, depth)]
    for i in range(4):
        p, q = pts[i], pts[(i + 1) % 4]
        sk.addGeometry(Part.LineSegment(App.Vector(*p, 0), App.Vector(*q, 0)), False)
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
        sk.addConstraint(
            Sketcher.Constraint("Horizontal" if i % 2 == 0 else "Vertical", i)
        )
    dimension(sk, Sketcher.Constraint("Distance", 0, width), width_expr)
    dimension(sk, Sketcher.Constraint("Distance", 1, depth), depth_expr)
    dimension(
        sk, Sketcher.Constraint("DistanceX", 0, 1, -width / 2), f"-({width_expr})/2"
    )
    sk.addConstraint(Sketcher.Constraint("DistanceY", 0, 1, 0.0))
    return sk


def datum(body, name, z=0, sensor=False):
    plane = body.newObject("PartDesign::Plane", name)
    if sensor:
        plane.Placement = App.Placement(
            App.Vector(0, 0, 0), App.Rotation(App.Vector(1, 0, 0), 90)
        )
    else:
        plane.Placement.Base.z = z
        plane.setExpression("Placement.Base.z", "Parameters.Thickness")
    plane.Visibility = False
    return plane


def on_plane(sketch, plane):
    # Explicit datum Placement expression avoids references to generated faces.
    sketch.setExpression("Placement", plane.Name + ".Placement")


def holes(body, name, spacing, ordinate, diameter, prefix):
    sk = body.newObject("Sketcher::SketchObject", name)
    for sign in (-1, 1):
        i = sk.addGeometry(
            Part.Circle(
                App.Vector(sign * spacing / 2, ordinate, 0),
                App.Vector(0, 0, 1),
                diameter / 2,
            ),
            False,
        )
        dimension(
            sk,
            Sketcher.Constraint("Diameter", i, diameter),
            f"Parameters.{prefix}Diameter",
        )
        dimension(
            sk,
            Sketcher.Constraint("DistanceX", i, 3, sign * spacing / 2),
            f"{sign} * Parameters.{prefix}Spacing / 2",
        )
        dimension(
            sk,
            Sketcher.Constraint("DistanceY", i, 3, ordinate),
            f"Parameters.{('BaseY' if prefix == 'Base' else 'SensorZ')}",
        )
    return sk


def box_feature(doc, name, label, box, color, transparency):
    obj = doc.addObject("Part::Box", name)
    obj.Label = label
    obj.Length, obj.Width, obj.Height = box["size"]
    obj.Placement.Base = App.Vector(*box["origin"])
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.Transparency = transparency
    return obj


def build(spec, revision):
    doc = App.newDocument("Bracket_" + revision[:8])
    p = doc.addObject("App::FeaturePython", "Parameters")
    p.Label = "Design parameters (mm)"
    for name, (group, key) in PARAMETERS.items():
        p.addProperty("App::PropertyLength", name, "Bracket design")
        setattr(p, name, spec[group][key])
    body = doc.addObject("PartDesign::Body", "Bracket")
    body.Label = "Machined sensor bracket"
    b = spec["bracket"]
    base = rectangle(
        body,
        "BaseSketch",
        b["width"],
        b["depth"],
        "Parameters.Width",
        "Parameters.Depth",
    )
    pad = body.newObject("PartDesign::Pad", "BasePad")
    pad.Profile = base
    pad.setExpression("Length", "Parameters.Thickness")
    recompute(doc)
    top = datum(body, "BaseTopDatum", b["thickness"])
    upright = rectangle(
        body,
        "UprightSketch",
        b["width"],
        b["thickness"],
        "Parameters.Width",
        "Parameters.Thickness",
    )
    on_plane(upright, top)
    wall = body.newObject("PartDesign::Pad", "UprightPad")
    wall.Profile = upright
    wall.setExpression("Length", "Parameters.Height - Parameters.Thickness")
    recompute(doc)
    # Identify the single concave horizontal edge geometrically, not by a fixed index.
    t = b["thickness"]
    candidates = []
    for i, edge in enumerate(wall.Shape.Edges, 1):
        if len(edge.Vertexes) == 2 and all(
            abs(v.Point.y - t) < 1e-7 and abs(v.Point.z - t) < 1e-7
            for v in edge.Vertexes
        ):
            candidates.append(f"Edge{i}")
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one internal corner edge, found {candidates}")
    fillet = body.newObject("PartDesign::Fillet", "InternalCorner")
    fillet.Base = (wall, candidates)
    fillet.setExpression("Radius", "Parameters.CornerRadius")
    recompute(doc)
    h = spec["base_holes"]
    bh = holes(body, "BaseHoleSketch", h["spacing"], h["y"], h["diameter"], "Base")
    on_plane(bh, top)
    pocket = body.newObject("PartDesign::Pocket", "BaseHoles")
    pocket.Profile = bh
    pocket.setExpression("Length", "Parameters.Thickness")
    recompute(doc)
    rear = datum(body, "SensorMountDatum", sensor=True)
    h = spec["sensor_holes"]
    sh = holes(body, "SensorHoleSketch", h["spacing"], h["z"], h["diameter"], "Sensor")
    on_plane(sh, rear)
    sensor_pocket = body.newObject("PartDesign::Pocket", "SensorHoles")
    sensor_pocket.Profile = sh
    sensor_pocket.setExpression("Length", "Parameters.Thickness")
    recompute(doc)
    for obj in body.Group:
        obj.Visibility = False
    sensor_pocket.Visibility = True
    body.Visibility = True
    body.ViewObject.ShapeColor = (0.72, 0.79, 0.88)
    body.ViewObject.LineColor = (0.12, 0.19, 0.26)
    box_feature(
        doc,
        "Sensor",
        "Sensor placeholder (mounting contact intended)",
        spec["sensor"],
        (0.12, 0.36, 0.48),
        20,
    )
    for i, obstacle in enumerate(spec["obstacles"]):
        box_feature(
            doc, f"Obstacle{i}", obstacle["name"], obstacle, (0.95, 0.40, 0.18), 65
        )
    env = box_feature(
        doc, "Envelope", "Packaging envelope", spec["envelope"], (0.3, 0.7, 0.5), 90
    )
    env.Visibility = False
    recompute(doc)
    return doc
