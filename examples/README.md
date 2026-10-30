# Example SWC files

## `tiny.swc`

Minimal branching morphology (5 nodes) in **nanometers**, matching common exports from tools like neuromorphic / navis.

| Field | Meaning |
| --- | --- |
| `x`, `y`, `z` | Position in **nm** |
| `radius` | Node radius in **nm** (used as tube radius in VTK) |
| `parent` | `-1` for root |

### STL scale in viewers

SWC2MESH does **not** rescale coordinates. STL files use the same numeric units as the SWC. If your viewer expects millimeters, either:

- Scale the mesh after export (e.g. factor `1e-6` from nm → mm), or
- Pre-scale SWC coordinates before conversion.

The GUI window title remains **“SWC to STL Converter”**; output files use the `.stl` extension.
