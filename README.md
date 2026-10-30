# SWC2MESH

Convert [SWC](http://www.neuronland.org/NLMorphologyConverter/html/SWCFileFormat.html) neuron morphology files to binary STL meshes for 3D printing and visualization.

The repository name is **SWC2MESH**; the desktop GUI window title is **SWC to STL Converter** (legacy). Output files are `.stl`.

## Features

- Batch conversion of all `.swc` files in a folder
- Tubular meshing with per-node radii, optional decimation, cleaning, and smoothing (VTK)
- PyQt5 GUI for directory pickers and parameters
- Parallel processing via Python `multiprocessing`

## Requirements

- Python **3.9–3.12**
- [VTK](https://vtk.org/) **9.3.x** and **PyQt5** 5.15+ (see `requirements.txt`)

### Licensing note (PyQt5)

This project is released under the **MIT License** (see `LICENSE`). **PyQt5** is under **GPL v3** (or a commercial Qt license). Running from source with a normal PyPI `PyQt5` install is typical for lab use; **redistributing frozen binaries** that bundle PyQt5 may require GPL compliance or a commercial Qt license. See `THIRD_PARTY_NOTICES`. A future **PySide6 (LGPL)** port would simplify binary redistribution.

## Install and run (source)

```bash
git clone https://github.com/kaare-/SWC2MESH.git
cd SWC2MESH
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pytest          # for tests
python Gui.py
```

Place `processing.py` next to `Gui.py` (default layout). Example input: `examples/tiny.swc`.

## SWC units and STL scale

Many SWC exports use **nanometers** for coordinates and radii. SWC2MESH writes those values **unchanged** into STL. If your viewer assumes millimeters, scale the result (e.g. nm → mm: multiply viewer import scale by `1e-6`) or rescale the SWC before conversion. Details: [examples/README.md](examples/README.md).

## Tests

```bash
pytest -q
```

CI runs the same tests on Ubuntu, macOS, and Windows (VTK pipeline only; no display required).

Optional GUI import check (requires display or platform plugins): `pytest tests/test_gui_import.py` if present.

## Frozen builds (PyInstaller)

Specs: `SWC2STLApp.spec` (macOS `.app` bundle), `SWC2STL.spec`, `Gui.spec`.

```bash
pip install pyinstaller
pyinstaller SWC2STLApp.spec
```

**macOS:** CI release artifacts are **unsigned**. For wide distribution, sign with a **Developer ID** and notarize. After download, users may need to clear quarantine (`xattr -dr com.apple.quarantine …`) and ensure execute bits on the `.app` bundle.

**Linux / Windows:** Release zips are built in GitHub Actions on tag push (see [Releases](https://github.com/kaare-/SWC2MESH/releases)).

## Version

**0.1.0** — first open-source release (source-first; optional CI binaries).

## Citation

If you use SWC2MESH in research, please link to this repository: `https://github.com/kaare-/SWC2MESH`.
