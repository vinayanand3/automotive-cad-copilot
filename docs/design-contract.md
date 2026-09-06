# Design contract

All fixtures are synthetic. This is a machined L-bracket concept with an internal corner radius, not a bent sheet-metal part. No customer, employer or OEM geometry is used.

## Coordinates and inputs

X is centered across the bracket width. Y runs from the rear mounting face at zero to the front edge of the base. Z runs from the underside at zero to the top of the upright. The base occupies Z=0..thickness; the upright occupies Y=0..thickness. The sensor sits behind the upright, with its front face on Y=0.

`examples/sensor-bracket.json` is the complete required JSON contract. `schema_version` is 1. Full specifications accept `mm` or `in`; all lengths, origins and box sizes normalize to mm. Material density is always kg/m3. Unknown keys, booleans as numbers, nonfinite values and incomplete specifications are rejected.

| Group | Meaning |
|---|---|
| bracket | width, base depth, total height, common thickness, internal corner radius |
| base_holes | two through holes at X=+/-spacing/2, Y=y, parallel to Z |
| sensor_holes | two through holes at X=+/-spacing/2, Z=z, parallel to Y |
| sensor | rectangular placeholder origin and size; intended mounting contact at Y=0 |
| obstacles | named axis-aligned forbidden boxes, each with origin and size |
| envelope | axis-aligned allowed box for the bracket and sensor |
| requirements | minimum hole rim edge distance and minimum obstacle clearance |
| material | illustrative name and density for a geometric mass estimate |

Patches merge object fields and replace arrays. They are always expressed in mm and cannot change schema version or units. Revising a base mounting pattern does not implicitly change the sensor interface.

## Requirements

The demo requires a 5 mm minimum hole rim edge distance and 3 mm obstacle clearance. Edge distance includes the clearance to the internal fillet tangent. These values are demonstration requirements, not automotive standards. The radius is limited to the plate thickness and must fit both internal legs. Hole separation must leave at least the configured edge-distance amount of material.

The 80 x 40 x 50 mm preset uses 6 mm thickness, an R3 internal corner, 40 mm base-hole spacing with 6.6 mm holes, and 24 mm sensor-hole spacing with 4.5 mm holes. These hole sizes are explicit illustrative inputs, not a fastener selection recommendation.

Changing base spacing to 50 mm remains feasible. Narrowing that revision to 60 mm leaves `(60 - 50)/2 - 6.6/2 = 1.7 mm` at each side. It must fail the 5 mm requirement. A minimum width of 66.6 mm satisfies this side-edge condition, subject to all other checks.

## Geometry validation

Checks use the generated Open CASCADE solid: validity and solid count; bounding dimensions; cylindrical hole centers and diameters; planar thickness locations; internal fillet radius; fully constrained sketches; sensor contact and overlap; bounding-box inclusion in the envelope; and both intersection volume and minimum distance for each obstacle pair.

A 0.01 mm numerical comparison tolerance is used for dimensions. Intersection volume tolerance is 0.000001 mm3. STEP roundtrip requires the same solid count, bounds within 0.01 mm, and volume error no larger than max(0.001 mm3, one part per million). These are numerical tests, not drawing manufacturing tolerances.

Sensor-to-bracket mounting contact is intended and verified separately. Sensor and bracket clearance to obstacles is mandatory. Obstacles are reference geometry and need not lie within the allowed envelope.

## Revision behavior

Each job has an immutable ID and separate output directory. Successful build/revise jobs update the latest pointer only after checks and exports finish. Rejected designs and timed-out jobs never promote their artifacts. Preflight rejection produces a structured result without creating a CAD revision.

`validate` reopens and checks the saved native model. `export` rebuilds from the stored specification into a new output directory, preserving source artifacts. Manual native edits can be inspected with `validate`; they are not imported back into the stored specification and are not included in subsequent spec-driven revisions or exports.

## Boundaries

The sensor is a fit placeholder, with no internal electronics or modeled threads. The project does not determine load capacity, fatigue life, vibration response, fastener preload, tool access, surface finish or GD&T. The drawing is an inspection aid marked not for manufacture. Manufacturing release needs engineering work beyond these checks.
