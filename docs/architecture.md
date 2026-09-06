# Architecture

Codex reads the project skill and translates a request to a complete JSON specification or minimal patch. The dependency-free CLI normalizes and checks it, then places a job in the workspace queue. The FreeCAD desktop bridge polls with a Qt timer and executes native CAD API calls on the GUI thread.

The queue uses atomic JSON writes, unique job IDs, a QLockFile owner lock, one job at a time, a heartbeat, and deadlines. The CLI reports stale/unavailable and busy bridges explicitly. A timeout writes a cancellation marker. The worker checks the deadline before committing results. Kernel operations cannot be interrupted safely in the middle; a timed-out operation can finish computation, but its outputs remain uncommitted. Restart recovery marks interrupted jobs as failed and requires explicit resubmission.

The builder creates named dimensional parameters, constrained sketches, two pads, a native concave fillet, and two pockets. Datum placements depend on parameters rather than generated face indices. The initial fillet edge is located geometrically. Native FreeCAD topology tracking handles subsequent parameter edits; native reopen/edit tests verify the supported variants.

The validator reads geometric faces and solids. TechDraw creates projected views, native overall dimensions and an explicit hole coordinate table. STEP export is immediately reimported and compared. PDF and image review are separate from geometry validation.

No hosted service, database, model API key or network listener is required. The local queue is a trusted project interface, not a multi-user service. A project skill is sufficient for the Codex workflow; an MCP wrapper or installable plugin could be added later without changing the geometry modules.
