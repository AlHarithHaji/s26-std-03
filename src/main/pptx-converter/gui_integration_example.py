"""Reference integration for the team's CustomTkinter export window.

This file is documentation-by-example; it is not started directly. Copy the
relevant import block and PPTX branch into the shared Futurdata GUI.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from tkinter import filedialog

# The requested directory name contains a hyphen. Add that directory itself to
# Python's search path, then import the public module by filename.
PPTX_CONVERTER_DIR = Path(__file__).resolve().parent
if str(PPTX_CONVERTER_DIR) not in sys.path:
    sys.path.insert(0, str(PPTX_CONVERTER_DIR))

from pptx_exporter import export_to_pptx  # noqa: E402


def export_pptx_from_gui(
    *,
    json_path: str,
    guide: Any,
    depth_spec: Any,
    include_bom: bool,
) -> str | None:
    """Ask for an output file and export the guide already built by the GUI."""

    output_path = filedialog.asksaveasfilename(
        title="Save PowerPoint presentation",
        defaultextension=".pptx",
        filetypes=[("PowerPoint Presentation", "*.pptx")],
    )
    if not output_path:
        return None

    # Passing ``guide`` avoids a second Loader run. ``json_path`` is retained so
    # relative image paths can still be resolved against the source directory.
    return export_to_pptx(
        json_path=json_path,
        guide=guide,
        depth=depth_spec,
        include_bom=include_bom,
        output_path=output_path,
    )
