#!/usr/bin/env python3
"""Generate scene-timed macOS speech, or mux the checked-in track anywhere."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "artifacts/demo"


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate", action="store_true", help="Requires macOS say")
    parser.add_argument("--voice", default="Samantha")
    args = parser.parse_args()
    scenes = json.loads((ROOT / "assets/narration.json").read_text())
    track = DEMO / "narration.m4a"
    video = DEMO / "automotive-cad-copilot.mp4"
    with tempfile.TemporaryDirectory(prefix="cad-narration-") as tmp:
        tmp = Path(tmp)
        if args.regenerate:
            clips = []
            for i, scene in enumerate(scenes):
                script = tmp / f"{i}.txt"
                script.write_text(scene["text"])
                raw = tmp / f"{i}.aiff"
                run("say", "-v", args.voice, "-r", "155", "-f", script, "-o", raw)
                duration = float(
                    subprocess.check_output(
                        [
                            "ffprobe",
                            "-v",
                            "error",
                            "-show_entries",
                            "format=duration",
                            "-of",
                            "default=noprint_wrappers=1:nokey=1",
                            str(raw),
                        ]
                    )
                )
                available = scene["duration"] - 1.0
                speed = max(1.0, duration / available)
                if speed > 1.2:
                    raise ValueError(f"Scene {i + 1} needs shorter narration")
                clip = tmp / f"{i}.wav"
                run(
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    raw,
                    "-af",
                    f"atempo={speed},adelay=500:all=1,apad",
                    "-t",
                    scene["duration"],
                    "-ar",
                    "48000",
                    "-ac",
                    "1",
                    clip,
                )
                clips.append(clip)
                print(
                    f"Scene {i + 1}: speech {duration:.2f}s, slot {scene['duration']}s, speed {speed:.3f}"
                )
            listing = tmp / "audio.txt"
            listing.write_text("".join(f"file '{p}'\n" for p in clips))
            run(
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                listing,
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar",
                "48000",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                track,
            )
        if not track.exists():
            parser.error("Missing narration.m4a; use --regenerate on macOS first")
        output = DEMO / "narrated.tmp.mp4"
        try:
            run(
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                video,
                "-i",
                track,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                output,
            )
            output.replace(video)
        finally:
            output.unlink(missing_ok=True)
    print(video)


if __name__ == "__main__":
    main()
