---
name: automotive-cad
description: Create, revise, validate, and export the synthetic sensor bracket in this Automotive CAD Copilot project using its FreeCAD bridge. Use for bracket design requests and packaging checks.
---

# Automotive CAD Copilot

Work from the repository root. Read `examples/sensor-bracket.json` for the complete input contract and `docs/design-contract.md` for coordinates and project requirements.

Use the existing Python CLI and native FreeCAD builder. For supported requests, translate natural language into specifications or minimal revision patches. Do not rewrite CAD generation code to satisfy a design request.

- `python3 -m cadcopilot status` checks bridge availability.
- `python3 -m cadcopilot build --preset sensor-bracket` creates the supplied synthetic fixture.
- `python3 -m cadcopilot build --spec <file.json>` creates a fully specified design.
- `python3 -m cadcopilot revise --revision <id> --patch <file.json>` creates a new revision. `latest` is supported, but resolve and retain explicit IDs for a multi-step workflow.
- `python3 -m cadcopilot validate --revision <id>` measures the saved model.
- `python3 -m cadcopilot export --revision <id>` regenerates the revision's supported artifacts from its stored specification.

If the bridge is unavailable, use `scripts/start-freecad.sh` with `FREECAD_BIN` set to the installed executable, or execute `freecad/StartCopilot.FCMacro` in FreeCAD. Wait for a fresh heartbeat. Do not claim success from a preflight-only result.

Lengths are mm; complete specifications may use `in`. Revision patches always use mm. Missing essential dimensions require clarification. The named preset explicitly supplies defaults; identify it in the response. "Make narrower" without a requested width requires a dimension, unless the user explicitly asks you to choose one. Preserve mounting interfaces and requirements unless their change is requested.

For the portfolio sequence: build the preset, revise using `examples/wider-spacing.json`, then attempt `examples/too-narrow.json` against that revised ID. The last step must be rejected because its hole rim edge distance is 1.7 mm against a required 5 mm. A feasible minimum width is 66.6 mm, but do not silently substitute it.

Read every returned check. Explain rejected constraints with actual and required values. Never relax a threshold, alter a sensor interface, or label an invalid revision successful to satisfy a prompt. Timeout and failed jobs preserve the last successful revision; inspect the result before retrying, with at most one automatic retry for a transient bridge error.

On success, link the native model, STEP, drawing, report, and image using returned paths. Inspect the assembly image, bracket image and drawing. Computer use may inspect the native feature tree. Geometry measurements determine geometric validity; visual inspection determines presentation quality.

This is a machined bracket concept, not a sheet-metal flat pattern. Structural safety, fatigue, vibration, fastener design, GD&T and production release are outside this template's checks. Report only measured timings and actual test outcomes.
