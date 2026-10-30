"""Headless smoke tests: SWC → STL via processing.py (no PyQt display)."""

from __future__ import annotations

import os
from pathlib import Path

import vtk

import processing


REPO_ROOT = Path(__file__).resolve().parent.parent
TINY_SWC = REPO_ROOT / "examples" / "tiny.swc"


def _process_one(swc_path: Path, output_dir: Path) -> Path:
    args = (
        str(swc_path),
        str(output_dir),
        0.5,
        8,
        True,
        3,
        0.1,
    )
    logs = processing.process_swc_file(args)
    log_text = "\n".join(logs)
    assert "[ERROR]" not in log_text, log_text
    stl_path = output_dir / f"{swc_path.stem}.stl"
    assert stl_path.is_file(), f"Expected STL at {stl_path}\n{log_text}"
    return stl_path


def test_read_swc_tiny():
    data, err = processing.read_swc(str(TINY_SWC))
    assert err is None
    assert len(data) == 5
    assert data[0]["p"] == -1


def test_swc_to_stl_file_exists(tmp_path):
    stl_path = _process_one(TINY_SWC, tmp_path)
    assert stl_path.stat().st_size > 100


def test_stl_mesh_sanity(tmp_path):
    stl_path = _process_one(TINY_SWC, tmp_path)
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(stl_path))
    reader.Update()
    mesh = reader.GetOutput()
    assert mesh.GetNumberOfPoints() > 0
    assert mesh.GetNumberOfPolys() > 0


def test_create_vtk_from_swc_polylines():
    data, _ = processing.read_swc(str(TINY_SWC))
    poly = processing.create_vtk_from_swc(data)
    assert poly.GetNumberOfPoints() == 5
    assert poly.GetNumberOfLines() >= 1
