"""Optional: verify PyQt5 and Gui module import (skipped without display on some CI)."""

from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(
    os.environ.get("SWC2MESH_SKIP_GUI_TEST") == "1",
    reason="GUI import test disabled",
)
def test_gui_module_imports():
    pytest.importorskip("PyQt5.QtWidgets")
    import Gui  # noqa: F401
