# Demo and reproducibility

The supplied MP4 is a 75-second edited artifact walkthrough, not an uncut screen recording. It uses real FreeCAD renders, the generated drawing, actual validation values and native feature names extracted from FCStd. The feature-history panel is a presentation of native file contents, not a fabricated FreeCAD screenshot. No narration or AI-generated CAD imagery is used.

Run `python scripts/make_demo.py` with Pillow, ffmpeg and pdftoppm installed to regenerate it. Default fonts are macOS Arial; pass `--font` and `--bold-font` on other systems.

For a live recording, use the project skill and these requests in sequence:

1. Create the supplied sensor-bracket preset. Show the native model and validation report.
2. Change base-hole spacing to 50 mm while keeping the sensor interface unchanged.
3. Make the bracket 60 mm wide.

Show the native feature tree, the changed mounting pattern, the 1.7 mm edge-distance rejection, the retained successful revision, and the drawing. Disclose cuts or speed changes. Record retries and manual interventions rather than presenting an edited sequence as a one-shot run.

The complete ten fixed engineering prompts are in `scripts/benchmark.py`. For independent conversational evaluation, run each in a fresh Codex session with the supplied baseline. Record the prompt, model identity, expected outcome, first result, retries, elapsed wall time and interventions. Keep those results separate from the scripted CLI benchmark.

For a manual comparison, time a person creating the same model, making the same revision, checking the same constraints, and producing the same exports. Include failures and corrections in both conditions. Do not infer savings from CAD execution time alone.
