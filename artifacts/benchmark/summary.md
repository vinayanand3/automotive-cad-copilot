# CAD workflow benchmark

scripted CLI replay of fixed engineering prompts; not an independent conversational-agent evaluation

Times include CLI, queue, CAD execution and exports. They exclude natural-language interpretation and FreeCAD startup. No manual timing baseline has been collected.

| Scenario | Expected | Observed | Seconds | Pass |
|---|---|---|---:|---|
| baseline | success | success | 1.903 | True |
| width84 | success | success | 1.814 | True |
| depth44 | success | success | 1.933 | True |
| height54 | success | success | 1.83 | True |
| thickness7 | success | success | 1.919 | True |
| spacing50 | success | success | 1.817 | True |
| too_narrow | rejected | rejected | 0.051 | True |
| radius100 | rejected | rejected | 0.049 | True |
| interference | rejected | rejected | 0.362 | True |
| clearance | rejected | rejected | 0.57 | True |
