# Sensor bracket validation

Synthetic automotive packaging example. Geometric checks only.

Status: **success**
Revision: `5423d021a4ba43b4a5071692d9d93600`

Numerical tolerance: 0.01 mm. This is not a manufacturing tolerance.

| Check | Result | Measured | Requirement |
|---|---|---|---|
| bracket_proportions | PASS | 6.0 | < 40.0 |
| corner_radius | PASS | 3.0 | <= thickness 6.0 and < internal legs |
| base_edge_distance | PASS | 10.7 | 5.0 |
| base_hole_separation | PASS | 43.4 | 5.0 |
| sensor_edge_distance | PASS | 15.75 | 5.0 |
| sensor_hole_separation | PASS | 19.5 | 5.0 |
| sensor_mounting_contact | PASS | 0.0 | 0 |
| sensor_interface_-12 | PASS | [-12.0, 32.0] | Hole contained in sensor mounting face |
| sensor_interface_12 | PASS | [12.0, 32.0] | Hole contained in sensor mounting face |
| valid_single_solid | PASS | 1 | 1 |
| measured_width | PASS | 80.0 | 80.0 |
| measured_depth | PASS | 40.0 | 40.0 |
| measured_height | PASS | 50.0 | 50.0 |
| measured_base_holes | PASS | [[-25.0, 26.0, 6.6], [25.0, 26.0, 6.6]] | [[-25.0, 26.0, 6.6], [25.0, 26.0, 6.6]] |
| measured_base_edge_distance | PASS | 10.7 | 5.0 |
| measured_sensor_holes | PASS | [[-12.0, 32.0, 4.5], [12.0, 32.0, 4.5]] | [[-12.0, 32.0, 4.5], [12.0, 32.0, 4.5]] |
| measured_sensor_edge_distance | PASS | 15.75 | 5.0 |
| measured_base_thickness | PASS | [0.0, 6.0, 50.0] | 6.0 |
| measured_upright_thickness | PASS | [0.0, 6.0, 40.0] | 6.0 |
| measured_corner_radius | PASS | [3.0] | 3.0 |
| fully_constrained_BaseSketch | PASS | True | True |
| fully_constrained_UprightSketch | PASS | True | True |
| fully_constrained_BaseHoleSketch | PASS | True | True |
| fully_constrained_SensorHoleSketch | PASS | True | True |
| sensor_no_interference | PASS | 0.0 | <= 0.000001 mm3 |
| sensor_intended_contact | PASS | 0.0 | 0 |
| bracket_inside_envelope | PASS | {'origin': [-40.0, 0.0, 0.0], 'size': [80.0, 40.0, 50.0]} | {'origin': [-50.0, -25.0, -1.0], 'size': [115.0, 75.0, 65.0]} |
| sensor_inside_envelope | PASS | {'origin': [-18.0, -18.0, 20.0], 'size': [36.0, 18.0, 24.0]} | {'origin': [-50.0, -25.0, -1.0], 'size': [115.0, 75.0, 65.0]} |
| bracket_to_harness_keepout_no_interference | PASS | 0.0 | <= 0.000001 mm3 |
| bracket_to_harness_keepout_clearance | PASS | 8.246211251235321 | 3.0 |
| sensor_to_harness_keepout_no_interference | PASS | 0.0 | <= 0.000001 mm3 |
| sensor_to_harness_keepout_clearance | PASS | 31.04834939252005 | 3.0 |
| step_roundtrip | PASS | {'solid_count': 1, 'max_bbox_error_mm': 0.0, 'volume_error_mm3': 0.0} | same solids, bbox <= 0.01 mm, volume <= max(0.001 mm3, 1 ppm) |
| native_reopen | PASS | True | True |
| native_edit_recompute | PASS | {'width_mm': 82.0, 'base_spacing_mm': 52.0, 'errors': []} | valid recompute and sensor holes unchanged; edits discarded |

## Resolved parameters

```json
{
  "schema_version": 1,
  "units": "mm",
  "bracket": {
    "width": 80.0,
    "depth": 40.0,
    "height": 50.0,
    "thickness": 6.0,
    "corner_radius": 3.0
  },
  "base_holes": {
    "spacing": 50.0,
    "y": 26.0,
    "diameter": 6.6
  },
  "sensor_holes": {
    "spacing": 24.0,
    "z": 32.0,
    "diameter": 4.5
  },
  "sensor": {
    "origin": [
      -18.0,
      -18.0,
      20.0
    ],
    "size": [
      36.0,
      18.0,
      24.0
    ]
  },
  "obstacles": [
    {
      "name": "harness_keepout",
      "origin": [
        48.0,
        8.0,
        10.0
      ],
      "size": [
        12.0,
        22.0,
        35.0
      ]
    }
  ],
  "envelope": {
    "origin": [
      -50.0,
      -25.0,
      -1.0
    ],
    "size": [
      115.0,
      75.0,
      65.0
    ]
  },
  "requirements": {
    "min_edge_distance": 5.0,
    "min_clearance": 3.0
  },
  "material": {
    "name": "6061-T6 aluminum (illustrative)",
    "density_kg_m3": 2700.0
  }
}
```

## Limits

No strength, fatigue, vibration, fastener, tooling-access or GD&T certification. Requirements are project-specific. Sensor contact at y=0 is intentional; obstacle contacts are not.
