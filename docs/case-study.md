# From engineering instructions to editable CAD

## Problem

A sensor bracket has two interfaces: the vehicle mounting pattern and the sensor mounting pattern. A change to one should preserve the other, and the result must still fit its packaging space. This project automates that small but complete engineering workflow.

## What I built

A Codex project skill translates instructions into a validated specification or revision patch. A dependency-free Python CLI sends jobs to a FreeCAD desktop bridge. Native sketches, pads, pockets and a concave fillet produce an editable model. Open CASCADE geometry checks validate the result. The workflow exports FCStd, STEP, a TechDraw inspection drawing, images, and a report.

The design is a synthetic machined aluminum bracket concept. It uses an 80 x 40 x 50 mm envelope, 6 mm thickness and an R3 corner. The base and sensor interfaces have independent parameters.

## Demonstration

1. Create the supplied bracket and its sensor/obstacle fixture.
2. Change the base-hole spacing from 40 to 50 mm while retaining the sensor interface.
3. Request a 60 mm width. The assistant rejects it because the side edge distance becomes 1.7 mm against a required 5 mm.
4. Inspect the last successful native model, drawing and validation report.

The model preserves fully constrained sketches and named dimensions. A native-file test closes and reopens the file, changes width and base spacing, recomputes, and verifies that the sensor hole geometry remains unchanged. Those test edits are discarded.

## Evidence

Tested on FreeCAD 1.1.3, its bundled Python 3.11, and macOS Apple Silicon.

- 19 Python contract and queue tests passed.
- All 10 scripted design scenarios returned their expected result: six valid models and four deliberate rejections.
- Each successful benchmark model passed STEP reimport comparisons, native reopen validation and native parameter-edit recomputation.
- A separate workflow test passed revision preservation, rejected-change retention, native validation, re-export, real timeout retention and successful build after timeout.
- Successful benchmark runs took 1.81 to 1.93 seconds, including the CLI, queue, model, checks and exports. FreeCAD startup and conversational interpretation are excluded.

Baseline measurements: 39,873.12 mm3 volume, 107.66 g estimated mass at the supplied 2700 kg/m3 density, and 8.25 mm minimum bracket-to-obstacle distance.

See [the measured benchmark](../artifacts/benchmark/summary.md) and [example validation report](../artifacts/examples/baseline/report.md). No manual modeling baseline was timed, so this project makes no percentage time-saving claim. The fixed prompt replay is a scripted CLI evaluation, not a blind independent evaluation of an AI agent.

## Engineering decisions

Geometry operations go through FreeCAD's API. Computer use inspects the native result. This keeps dimensions and clearances tied to solid geometry rather than pixel measurements.

Datum placements avoid dependencies on generated faces. Fillet edge selection uses geometry rather than a hard-coded index. Every revision has separate artifacts. Failures do not replace the last good revision, and the assistant does not silently relax requirements.

Visual PDF review caught issues that output-existence checks could not: asynchronous projection, relative dimension coordinates and overlapping views. The corrected exported drawing was rendered and inspected.

## Boundaries and next steps

The project demonstrates one reusable bracket family. The drawing is an inspection aid marked not for manufacture. It does not certify strength, fatigue, vibration, fastener design, tool access, surface finish or GD&T.

Next evaluation work: have another engineer reproduce the task, collect a manual baseline, and run the ten prompts in independent Codex sessions with interaction logs. Expansion to a second component family or an industry CAD adapter should follow that evidence.
