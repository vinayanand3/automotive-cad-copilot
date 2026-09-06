I built a CAD assistant that turns engineering instructions into editable FreeCAD models and checks design constraints.

The demo uses a synthetic automotive sensor bracket:

- Create a parametric bracket with separate vehicle and sensor mounting patterns.
- Change the base-hole spacing from 40 to 50 mm while preserving the sensor interface.
- Request a narrower bracket and get a specific explanation when the hole edge distance becomes too small.
- Export the native model, STEP, an inspection drawing, and a validation report.

The stack is Codex, Python, FreeCAD's API, and a local job bridge. The resulting model has editable sketches, pads, pockets and a fillet.

All ten scripted design scenarios returned the expected result. Successful models also passed STEP reimport, native reopen, and parameter-edit checks. The video is an edited walkthrough of actual outputs.

This is a CAD automation prototype for one component family. Structural validation and manufacturing release are outside its scope.

I'm interested in opportunities that combine mechanical engineering, CAD automation and practical AI tools.

Code and examples: https://github.com/vinayanand3/automotive-cad-copilot

#CADAutomation #MechanicalEngineering #FreeCAD #Python #AutomotiveEngineering
