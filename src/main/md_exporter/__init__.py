"""
md_exporter — Markdown export phase of the Disassembly Wizard (URS FR 14.0).

One of the Wizard's pluggable output generators (the "ExportMethod" family,
FR 11.0). Takes the Guide built by the load phase
(`disassembly_loader.build_guide`) and renders it as a Markdown document.

Position in the pipeline:

    Builder JSON --[disassembly_loader]--> Guide --[md_exporter]--> .md file(s)

A few rules this package sticks to:
- Consumes the IR only, never the graph — only `disassembly_loader`'s public
  API (build_guide + IR dataclasses) gets imported, so its internals
  (adapter/validation/linearizer) can change without breaking this package.
- No external dependencies: Markdown is plain text, the standard library
  covers it.
- Read-only on input (NFR 2.1): only writes to the output path(s) the caller
  gives it.
- Pluggable (FR 11.0): the class exposes format_id/display_name/file_extension
  so an export panel can list it next to PDFExporter, TXTExporter, etc., but
  callers (e.g. app.py) actually invoke it through `export_to_md`, the
  uniform export_to_X(...) wrapper — not by calling MDExporter directly.

Public API:
    MDExporter    — the exporter class (exporter.py)
    ExportOptions — configuration for one export run
    export_to_md  — functional wrapper over MDExporter, for callers (e.g.
                    app.py) that want a uniform export_to_X(...) call
"""

from .exporter import ExportOptions, MDExporter, export_to_md  # noqa: F401