"""Desktop-only TechDraw drawing and evidence exports."""

import json
import time
from pathlib import Path
from xml.sax.saxutils import escape
import FreeCAD as App
import FreeCADGui as Gui
import TechDrawGui
from .spec import ROOT
from .geometry import roundtrip_step


def make_drawing(doc, spec, out):
    page = doc.addObject("TechDraw::DrawPage", "Drawing")
    template = doc.addObject("TechDraw::DrawSVGTemplate", "DrawingTemplate")
    b = spec["bracket"]
    scale = min(1.0, 90 / b["width"], 46 / b["depth"], 60 / b["height"])
    template_text = (ROOT / "assets" / "drawing-template.svg").read_text()
    material = spec["material"]["name"]
    if len(material) > 35:
        material = material[:32] + "..."
    template_text = template_text.replace("__MATERIAL__", escape(material))
    template_text = template_text.replace(
        "__SCALE__", f"A4 / ORTHO x{scale:.2f} / ISO x{0.75*scale:.2f}"
    )
    template_path = out / "drawing-template.svg"
    template_path.write_text(template_text)
    template.Template = str(template_path)
    page.Template = template
    for name, direction, x, y in [
        ("Front", (0, -1, 0), 72, 125),
        ("Top", (0, 0, 1), 72, 52),
        ("Side", (1, 0, 0), 178, 125),
        ("Iso", (1, 1, 1), 235, 68),
    ]:
        view = doc.addObject("TechDraw::DrawViewPart", name)
        view.Source = [doc.Bracket]
        view.Direction = App.Vector(*direction)
        view.ScaleType = "Custom"
        view.Scale = scale
        page.addView(view)
        view.X, view.Y = x, y
        if name == "Side":
            view.XDirection = App.Vector(0, 1, 0)
        if name == "Iso":
            view.XDirection = App.Vector(-1, 1, 0)
            view.ScaleType = "Custom"
            view.Scale = 0.75 * scale
    doc.recompute()
    deadline = time.monotonic() + 10
    while not all(
        doc.getObject(n).getVisibleVertexes() for n in ("Front", "Top", "Side", "Iso")
    ):
        Gui.updateGui()
        if time.monotonic() > deadline:
            raise RuntimeError("TechDraw projection timed out")
        time.sleep(0.01)

    # Use native TechDraw dimensions referring to projected geometry vertices.
    def dimension(view, typ, name, axis, target, x, y):
        # TechDraw projection indices and selection names are zero based.
        points = []
        for i in range(0, 200):
            try:
                v = view.getVertexByIndex(i)
                if v is None:
                    break
                if hasattr(v, "Point"):
                    v = v.Point
                points.append((i, v))
            except Exception:
                break
        pairs = []
        for ia, a in points:
            for ib, b in points:
                if ib <= ia:
                    continue
                dist = abs((a.x - b.x) if axis == 0 else (a.y - b.y))
                if abs(dist - target) < 0.01:
                    # Prefer a common baseline, resulting in cleaner extensions.
                    cross = abs((a.y - b.y) if axis == 0 else (a.x - b.x))
                    pairs.append((cross, ia, ib))
        if not pairs:
            raise RuntimeError(
                f"Cannot resolve drawing dimension {name} ({target} mm): {points}"
            )
        _, ia, ib = min(pairs)
        dim = doc.addObject("TechDraw::DrawViewDimension", name)
        dim.Type = typ
        dim.References2D = [(view, (f"Vertex{ia}", f"Vertex{ib}"))]
        page.addView(dim)
        dim.X, dim.Y = x, y
        dim.FormatSpec = "%.2f"
        return dim

    b = spec["bracket"]
    dimension(doc.Front, "DistanceX", "OverallWidth", 0, b["width"], 0, 39)
    dimension(doc.Front, "DistanceY", "OverallHeight", 1, b["height"], -52, 0)
    dimension(doc.Top, "DistanceY", "OverallDepth", 1, b["depth"], -52, 0)
    # Exact hole diameters and center locations are included in the coordinate table.
    h, sh = spec["base_holes"], spec["sensor_holes"]
    note = doc.addObject("TechDraw::DrawViewAnnotation", "HoleTable")
    note.Text = [
        "HOLE COORDINATES / mm",
        f"Base: 2 x DIA {h['diameter']:g} THRU",
        f"X = +/-{h['spacing']/2:g}; Y = {h['y']:g}",
        f"Sensor: 2 x DIA {sh['diameter']:g} THRU",
        f"X = +/-{sh['spacing']/2:g}; Z = {sh['z']:g}",
        f"Plate thickness {b['thickness']:g}; internal R {b['corner_radius']:g}",
        "Datum: X center; rear Y=0; bottom Z=0",
    ]
    note.TextSize = 3
    page.addView(note)
    note.X, note.Y = 218, 172
    doc.recompute()
    Gui.activeDocument().getObject(page.Name).show()
    Gui.updateGui()
    TechDrawGui.exportPageAsPdf(page, str(out / "drawing.pdf"))
    TechDrawGui.exportPageAsSvg(page, str(out / "drawing.svg"))
    Gui.activeDocument().getObject(page.Name).hide()
    Gui.activateView("Gui::View3DInventor", True)
    return page


def export_all(doc, spec, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    step_check = roundtrip_step(doc.Bracket.Shape, out / "bracket.step")
    make_drawing(doc, spec, out)
    Gui.activeDocument().activeView().setCameraOrientation(
        App.Rotation(
            App.Vector(-1, 1, 0), App.Vector(0, 0, 1), App.Vector(1, 1, 1), "ZXY"
        ).Q
    )
    Gui.activeDocument().activeView().fitAll()
    Gui.activeDocument().activeView().saveImage(
        str(out / "assembly.png"), 1600, 1000, "White"
    )
    doc.Sensor.Visibility = False
    for obj in doc.Objects:
        if obj.Name.startswith("Obstacle"):
            obj.Visibility = False
    Gui.activeDocument().activeView().fitAll()
    Gui.activeDocument().activeView().saveImage(
        str(out / "bracket.png"), 1600, 1000, "White"
    )
    doc.Sensor.Visibility = True
    for obj in doc.Objects:
        if obj.Name.startswith("Obstacle"):
            obj.Visibility = True
    Gui.activeDocument().activeView().fitAll()
    doc.recompute()
    doc.saveAs(str(out / "bracket.FCStd"))
    paths = {
        name: str(out / file)
        for name, file in {
            "native": "bracket.FCStd",
            "step": "bracket.step",
            "drawing": "drawing.pdf",
            "drawing_svg": "drawing.svg",
            "assembly_image": "assembly.png",
            "bracket_image": "bracket.png",
        }.items()
    }
    for path in paths.values():
        if not Path(path).is_file() or Path(path).stat().st_size == 0:
            raise RuntimeError(f"Export missing or empty: {path}")
    return paths, step_check


def report(result, out):
    out = Path(out)
    rows = [
        "# Sensor bracket validation",
        "",
        "Synthetic automotive packaging example. Geometric checks only.",
        "",
        f"Status: **{result['status']}**",
        f"Revision: `{result['revision_id']}`",
        "",
        "Numerical tolerance: 0.01 mm. This is not a manufacturing tolerance.",
        "",
        "| Check | Result | Measured | Requirement |",
        "|---|---|---|---|",
    ]
    for c in result["checks"]:
        values = [
            c["name"],
            "PASS" if c["passed"] else "FAIL",
            str(c["actual"]),
            str(c["required"]),
        ]
        rows.append(
            "| "
            + " | ".join(v.replace("|", "/").replace("\n", " ") for v in values)
            + " |"
        )
    rows += [
        "",
        "## Resolved parameters",
        "",
        "```json",
        json.dumps(result["resolved_parameters"], indent=2),
        "```",
        "",
        "## Limits",
        "",
        "No strength, fatigue, vibration, fastener, tooling-access or GD&T certification. Requirements are project-specific. Sensor contact at y=0 is intentional; obstacle contacts are not.",
    ]
    (out / "report.md").write_text("\n".join(rows) + "\n")
