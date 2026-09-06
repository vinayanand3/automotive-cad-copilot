#!/usr/bin/env python3
"""Create a 75-second edited artifact walkthrough from verified FreeCAD outputs.
Requires Pillow, ffmpeg and pdftoppm. No generated/fabricated CAD imagery.
"""
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1920, 1080
NAVY = "#102c3c"
TEAL = "#087f75"
MUTED = "#527080"
PAPER = "#f5f8fa"
AMBER = "#aa4a1a"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--font", default="/System/Library/Fonts/Supplemental/Arial.ttf"
    )
    parser.add_argument(
        "--bold-font", default="/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    )
    args = parser.parse_args()
    out = ROOT / "artifacts/demo"
    out.mkdir(parents=True, exist_ok=True)
    frames = out / "frames"
    frames.mkdir(exist_ok=True)
    baseline = ROOT / "artifacts/examples/baseline"
    revised = ROOT / "artifacts/examples/spacing50"
    result = json.loads((baseline / "result.json").read_text())
    benchmark = json.loads((ROOT / "artifacts/benchmark/summary.json").read_text())
    durations = [10, 12, 14, 13, 14, 12]

    def font(size, bold=False):
        return ImageFont.truetype(args.bold_font if bold else args.font, size)

    def text(draw, xy, value, size=32, color=NAVY, bold=False):
        draw.text(xy, value, font=font(size, bold), fill=color)

    def card(n, title, subtitle):
        im = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, 14), fill=TEAL)
        text(d, (70, 46), "AUTOMOTIVE CAD COPILOT", 25, TEAL, True)
        text(d, (70, 96), title, 56, NAVY, True)
        text(d, (72, 177), subtitle, 29, MUTED)
        d.line((70, 985, 1850, 985), fill="#d4e0e6", width=2)
        text(
            d,
            (70, 1006),
            "Edited artifact walkthrough / Actual FreeCAD outputs / Synthetic component",
            22,
            MUTED,
        )
        text(d, (1740, 1006), f"{n+1} / 6", 22, MUTED)
        return im, d

    def place(im, path, box):
        asset = Image.open(path).convert("RGB")
        asset.thumbnail((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
        im.paste(
            asset,
            (
                box[0] + (box[2] - box[0] - asset.width) // 2,
                box[1] + (box[3] - box[1] - asset.height) // 2,
            ),
        )

    def save(im, n):
        im.save(frames / f"{n:02d}.png")

    im, d = card(
        0,
        "Engineering instructions. Editable CAD.",
        "A focused FreeCAD + Python + Codex portfolio project",
    )
    place(im, baseline / "bracket.png", (790, 230, 1840, 940))
    text(d, (80, 285), "CREATE", 24, TEAL, True)
    text(d, (80, 331), "Sensor mounting bracket", 43, NAVY, True)
    text(d, (80, 398), "80 x 40 x 50 mm / 6 mm thickness", 28)
    text(d, (80, 480), "REVISE", 24, TEAL, True)
    text(d, (80, 526), "40 to 50 mm hole spacing", 38, NAVY, True)
    text(d, (80, 614), "CHECK", 24, TEAL, True)
    text(d, (80, 660), "Dimensions, fit and clearance", 36, NAVY, True)
    text(d, (80, 772), "One reusable component family.", 28, MUTED)
    text(d, (80, 814), "Native features remain editable.", 28, MUTED)
    save(im, 0)
    im, d = card(
        1,
        "The design has a feature history.",
        "Native objects read directly from the saved FCStd document",
    )
    with zipfile.ZipFile(baseline / "bracket.FCStd") as z:
        root = ET.fromstring(z.read("Document.xml"))
        body = next(
            o for o in root.findall("./ObjectData/Object") if o.get("name") == "Bracket"
        )
        names = [
            x.get("value")
            for x in body.findall("./Properties/Property[@name='Group']/LinkList/Link")
        ]
    d.rounded_rectangle((70, 244, 690, 936), radius=20, fill="white")
    text(d, (100, 268), "Parameters (mm)", 34, TEAL, True)
    for i, name in enumerate(names):
        text(d, (125, 330 + i * 49), name, 29)
    place(im, baseline / "assembly.png", (740, 252, 1850, 936))
    save(im, 1)
    im, d = card(
        2,
        "Change the mounting pattern. Preserve the interface.",
        "Request: Increase base-hole spacing from 40 to 50 mm.",
    )
    place(im, baseline / "bracket.png", (75, 310, 935, 880))
    place(im, revised / "bracket.png", (985, 310, 1845, 880))
    text(d, (145, 250), "BASELINE / 40 mm", 32, MUTED, True)
    text(d, (1055, 250), "REVISION / 50 mm", 32, TEAL, True)
    text(
        d,
        (185, 910),
        "Sensor holes unchanged: X +/-12 mm, Z 32 mm, diameter 4.5 mm",
        32,
        TEAL,
        True,
    )
    save(im, 2)
    im, d = card(
        3,
        "An impossible change gets a specific explanation.",
        "Request: Narrow the revised bracket to 60 mm.",
    )
    d.rounded_rectangle((75, 264, 1075, 902), radius=22, fill=NAVY)
    for y, line in [
        (304, "STATUS: REJECTED"),
        (394, "base_edge_distance"),
        (478, "actual:    1.7 mm"),
        (544, "required:  5.0 mm"),
        (660, "Last successful revision preserved."),
    ]:
        text(d, (120, y), line, 36, "#ffffff", y == 304)
    text(d, (1140, 320), "Why it fails", 42, AMBER, True)
    text(d, (1140, 408), "(60 - 50) / 2 - 6.6 / 2", 32)
    text(d, (1140, 466), "= 1.7 mm from hole rim to edge", 29)
    text(d, (1140, 590), "No silent threshold changes.", 29, MUTED)
    text(d, (1140, 641), "No overwritten good model.", 29, MUTED)
    text(d, (1140, 758), "66.6 mm meets this side-edge", 28, TEAL)
    text(d, (1140, 802), "condition; other checks still apply.", 28, TEAL)
    save(im, 3)
    im, d = card(
        4,
        "Geometry checks support the result.",
        "STEP roundtrip, native reopen and editable-parameter recompute all pass.",
    )
    subprocess.run(
        [
            "pdftoppm",
            "-scale-to",
            "1500",
            "-singlefile",
            "-png",
            str(baseline / "drawing.pdf"),
            str(out / "drawing"),
        ],
        check=True,
    )
    place(im, out / "drawing.png", (775, 247, 1850, 950))
    m = result["measured_values"]
    items = [
        ("Single valid solid", "Native sketches fully constrained"),
        (f"{m['volume_mm3']:,.1f} mm3", "Measured solid volume"),
        (f"{m['mass_g']:.2f} g", "Mass estimate at 2700 kg/m3"),
        (
            f"{m['clearances_mm']['bracket_to_harness_keepout']:.2f} mm",
            "Bracket-to-obstacle clearance",
        ),
    ]
    for i, (value, label) in enumerate(items):
        text(d, (85, 270 + i * 156), value, 40, TEAL, True)
        text(d, (85, 329 + i * 156), label, 28, MUTED)
    save(im, 4)
    im, d = card(
        5,
        "Built to be inspected and reproduced.",
        "FreeCAD 1.1.3 / macOS Apple Silicon / Python CLI + local Codex skill",
    )
    text(
        d,
        (80, 283),
        f"{benchmark['passed']} / {benchmark['scenario_count']}",
        110,
        TEAL,
        True,
    )
    text(d, (80, 425), "Scripted design scenarios passed", 35, NAVY, True)
    text(d, (80, 491), "6 valid models + 4 expected rejections", 29, MUTED)
    text(d, (80, 557), "19 contract and queue tests passed", 29, MUTED)
    text(d, (80, 646), "FCStd / STEP / drawing / images / reports", 29, NAVY, True)
    d.rounded_rectangle((1080, 262, 1850, 886), radius=22, fill=NAVY)
    text(d, (1120, 306), "What this demonstrates", 38, "white", True)
    for i, line in enumerate(
        [
            "Parametric design intent",
            "Deterministic CAD automation",
            "Measured geometry validation",
            "Revision and failure handling",
        ]
    ):
        text(d, (1120, 391 + i * 68), line, 30, "#d0e4e9")
    text(d, (1120, 728), "Not structural or production certification.", 25, "#a6c5cc")
    text(d, (80, 796), "github.com/vinayanand3/automotive-cad-copilot", 30, TEAL, True)
    text(
        d,
        (80, 856),
        "No manual time-saving claim. No blind agent benchmark claim.",
        25,
        MUTED,
    )
    save(im, 5)
    clips = []
    for i, duration in enumerate(durations):
        clip = out / f"clip-{i}.mp4"
        clips.append(clip)
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-loop",
                "1",
                "-i",
                str(frames / f"{i:02d}.png"),
                "-t",
                str(duration),
                "-vf",
                f"fade=t=in:st=0:d=0.3,fade=t=out:st={duration-0.3}:d=0.3",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "20",
                "-r",
                "30",
                "-pix_fmt",
                "yuv420p",
                str(clip),
            ],
            check=True,
        )
    listing = out / "clips.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in clips))
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(out / "automotive-cad-copilot.mp4"),
        ],
        check=True,
    )
    for p in clips:
        p.unlink()
    listing.unlink()
    print(out / "automotive-cad-copilot.mp4")


if __name__ == "__main__":
    main()
