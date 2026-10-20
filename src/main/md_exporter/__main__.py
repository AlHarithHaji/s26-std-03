"""
__main__.py — command-line interface of the MD exporter.

Makes the exporter usable without writing Python:

    python -m md_exporter model.json guide.md
    python -m md_exporter model.json guide.md --steps-per-page 5
    python -m md_exporter model.json guide.md --depth keep_main --no-images

The GUI (part 1 of the project split) calls MDExporter programmatically, but
a one-line terminal export is handy during development and grading.
 `python -m md_exporter` is the same "run this package"
mechanism pip or pytest use, no new dependency or install step.

Exit codes: 0 = success, 2 = bad arguments (argparse), 1 = unparsable model.
"""

from __future__ import annotations

import argparse
import sys

from disassembly_loader import (
    DepthMode,
    DepthSpec,
    UnparsableModelError,
    build_guide,
)

from .exporter import ExportOptions, MDExporter


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m md_exporter",
        description="Export a Disassembly Builder JSON model to Markdown.",
    )
    parser.add_argument("model", help="path to the Builder JSON model (read-only)")
    parser.add_argument("output", help="path of the .md file to write")
    parser.add_argument(
        "--steps-per-page", type=int, default=None, metavar="N",
        help="split the guide into pages of N steps each (FR 19.0); "
             "default: everything in one file",
    )
    parser.add_argument(
        "--depth", choices=[m.value for m in DepthMode], default="full",
        help="disassembly depth (FR 3.0); default: full",
    )
    parser.add_argument(
        "--keep-nodes", type=int, nargs="+", default=[], metavar="ID",
        help="with --depth manual: ids of the sub-roots to keep whole",
    )
    #options are ON by default; flags switch individual sections OFF.
    parser.add_argument("--no-toc", action="store_true", help="omit the table of contents")
    parser.add_argument("--no-warnings", action="store_true", help="omit validation warnings")
    parser.add_argument("--no-bom", action="store_true", help="omit the Bill of Materials")
    parser.add_argument("--no-images", action="store_true", help="omit image links")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    try:
        depth = DepthSpec(
            mode=DepthMode(args.depth),
            keep_whole_ids=tuple(args.keep_nodes),
        )
        options = ExportOptions(
            include_toc=not args.no_toc,
            include_warnings=not args.no_warnings,
            include_bom=not args.no_bom,
            include_images=not args.no_images,
            steps_per_page=args.steps_per_page,
        )
    except ValueError as exc:
        #depthSpec/ExportOptions validate themselves (e.g. --keep-nodes
        #without --depth manual, or steps_per_page=0). Translate the
        #exception into a clean CLI error instead of a raw traceback;
        #exit code 2 = bad arguments, same convention argparse uses.
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        #BoM is always requested from the loader, whether it gets rendered
        #is options.include_bom's call. One extra traversal, and it keeps
        #"what data exists" separate from "what the user sees".
        guide = build_guide(args.model, depth=depth, include_bom=True)
    except UnparsableModelError as exc:
        # The one fatal case (FR 2.x): no graph at all in the file. Report on
        # stderr and exit non-zero so scripts/CI can detect the failure.
        print(f"error: cannot parse model: {exc}", file=sys.stderr)
        return 1

    written = MDExporter().export(guide, args.output, options)

    #Success report on stdout: what got written, plus a reminder that the
    #guide's validation findings are in the document itself (FR 2.2).
    for path in written:
        print(f"written: {path}")
    if guide.warnings:
        print(f"note: {len(guide.warnings)} validation warning(s) — "
              f"see the Validation warnings section in the document.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
