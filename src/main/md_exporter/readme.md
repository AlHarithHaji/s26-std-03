# md_exporter — Markdown export for the Disassembly Wizard

`md_exporter` is the **MD generation phase** of the Disassembly Wizard (URS FR
14.0): it takes the `Guide` produced by the load phase
([`disassembly_loader`](../disassembly_loader/readme.md)) and renders it as a
human-readable Markdown document — with a table of contents, a Bill of
Materials table, numbered per-step instructions, native images, highlighted
safety notes, and optional splitting into linked pages.

Position in the Wizard's pipeline:

```
Builder JSON --[disassembly_loader]--> Guide --[md_exporter]--> guide.md (+pages)
```

No external dependencies: Markdown is plain text, the standard library is
enough. Python 3.10+.

---

## Quick start

### From code (how the Wizard's export panel calls it)

```python
from disassembly_loader import build_guide
from md_exporter import MDExporter, ExportOptions

guide = build_guide("model.json", include_bom=True)
files = MDExporter().export(guide, "out/guide.md")            # one file
files = MDExporter().export(                                   # paginated
    guide, "out/guide.md", ExportOptions(steps_per_page=5)
)
```

`export()` returns the list of paths written, in reading order.

### From code — plain function (what the GUI's `app.py` calls)

For callers that want a uniform `export_to_X(...)` call per format instead of
instantiating a class, `export_to_md` is a thin wrapper over `MDExporter`:

```python
from md_exporter import export_to_md

files = export_to_md("model.json", "out/guide.md")                     # from a path
files = export_to_md(guide, "out/guide.md")                            # from an already-built Guide
files = export_to_md("model.json", "out/guide.md",
                      depth=my_depth_spec, include_bom=True,
                      options=ExportOptions(steps_per_page=5))
```

`json_path` accepts either a model path (in which case `depth` and
`include_bom` are forwarded to `build_guide`) or a `Guide` already built
elsewhere (in which case `depth`/`include_bom` are ignored — there is nothing
left to build). `output_path` is required: there is no auto-generated
default. `include_bom` here controls whether the Bill of Materials is
*computed*; whether it is *rendered* is still `options.include_bom`. The
return value and behavior are identical to calling `MDExporter().export(...)`
directly — `export_to_md` never does anything the class doesn't already do.

### From the command line

```bash
python -m md_exporter model.json guide.md
python -m md_exporter model.json guide.md --steps-per-page 5
python -m md_exporter model.json guide.md --depth keep_main --no-images
python -m md_exporter --help
```

Exit codes: `0` success, `1` unparsable model, `2` bad arguments.

---

## Options (`ExportOptions`)

| Option | Default | Effect | URS |
|---|---|---|---|
| `include_toc` | `True` | table of contents with anchor links to each step | — |
| `include_warnings` | `True` | validation findings section (severity, rule, node ids) | FR 2.2/2.3 |
| `include_bom` | `True` | Bill of Materials table (needs a Guide built with `include_bom=True`) | FR 1.3/9.1 |
| `include_images` | `True` | native `![](...)` image links | FR 4.1 |
| `steps_per_page` | `None` | `None` = one file; `N` = split into pages of N steps | FR 19.0 |

Options are a **frozen dataclass** (same pattern as the loader's `DepthSpec`):
the GUI builds one object from its widgets and hands it over; adding an option
never changes a method signature; values cannot drift mid-run.

---

## What the document looks like

Page 1 carries the global sections; further pages (paginated exports only)
carry a compact header and the navigation links:

```
# Disassembly Guide — <product>          # Disassembly Guide — <product> (page 2/3)
<product card: weight, depth, steps>     [← Previous page] | Page 2 of 3 | [Next page →]
## ⚠ Validation warnings   (option)      ## Step 4 — ...
## Bill of Materials       (option)      ...
## Contents                (option)
## Step 1 — <operation>
  Tools required: ...
  1. <action>  2. <action> ...
  ### Parts obtained
  ➡️ Continue disassembling <part> in [Step 2]
```

Rendering rules worth knowing:

- **One step = one diamond** (FR 10.0): grouping is inherited from the IR, the
  renderer never regroups.
- **Safety notes**: actions containing danger keywords (`ATTENZIONE`,
  `WARNING`, `CAUTION`, ...) are highlighted ⚠️ **bold** inside the numbered
  list — numbering stays unbroken, the eye is drawn to the risk.
- **Depth cuts** (FR 3.0): assemblies kept whole are marked
  `📦 kept whole — contains N parts` in steps and in the BoM.
- **Cross-page links**: the continuation link of the last step of a page
  targets the *next file* (`guide_page2.md#step-6`), not a dead local anchor.
- **Escaping**: all node-derived text is Markdown-escaped at render time
  (`md_utils.py`); a component named `Vite_M3*2` renders literally instead of
  turning into stray emphasis. Missing data renders as `—`, never as `None`.
- **Empty guides** (FR 2.3 best-effort on malformed models) still produce a
  document that explains itself, next to the warnings that tell why.

---

## Design rules (why it is built this way)

1. **Consume the IR, never the graph.** Only the loader's public API is
   imported (`build_guide` + the IR dataclasses). The IR is the contract;
   everything behind it may change without notice.
2. **Read-only input** (NFR 2.1): the exporter only ever writes to the output
   paths given by the caller.
3. **Pluggable** (FR 11.0): `MDExporter` declares `format_id`,
   `display_name`, `file_extension` as class attributes, so the export panel
   can register formats it has never heard of. Adding a format later = a class
   with the same surface.
4. **Orchestration ≠ rendering.** `exporter.py` decides *what gets written
   where* (files, pagination); `renderer.py` decides *what a step looks like*
   (pure: data in, string out — trivially testable); `md_utils.py` owns the
   Markdown syntax mechanics (escaping, anchors, tables). One module = one
   reason to change.

## Package layout

```
md_exporter/
├── __init__.py     public surface: MDExporter, ExportOptions, export_to_md
├── exporter.py     orchestration: options, pagination (FR 19.0), file I/O,
│                   export_to_md (plain-function wrapper for the GUI)
├── renderer.py     pure Guide -> Markdown text
├── md_utils.py     escaping, anchors, tables, weight formatting
├── __main__.py     command-line interface (python -m md_exporter)
├── TESTING.md      systematic test report (matrix, defects found & fixed)
├── examples/       sample rendered outputs
└── tests/          pytest suite (41 tests) + synthetic fixture models
```

## Running the tests

```bash
pip install pytest
python -m pytest md_exporter/tests/ -v      # from the repository root
```

The suite runs on the synthetic models in `tests/fixtures/` (owned by this
package), with a single skip-if-absent smoke test on a real loader example —
so changes to the loader's example files can never break this suite. See
`TESTING.md` for the full test matrix and the defects found during
development.

`tests/conftest.py` locates `disassembly_loader` automatically whether it
sits next to `md_exporter` (this sandbox layout) or nested under
`loader_se/` (the course repo layout) — no manual `PYTHONPATH` needed
either way.

## Known observations (inherited from the data, not defects)

- Some source models store material/color as numeric ids (e.g. material `3`):
  the loader deliberately does not resolve ids to names, so the exporter
  prints what it receives. Resolving belongs upstream.
- When no root can be identified, the loader names the product
  `(empty model)`; the exporter renders it as received.
- Schema 1.1 changed `Step.continues_as` from a single `Component | None` to
  a `tuple[Component, ...]` (output branching support). The renderer handles
  the tuple and renders one continuation line per entry, but the link target
  still assumes sequential `step.index + 1` ordering — correct for every
  model exercised by this suite, but not yet verified against a genuinely
  branched model (the loader's own docs say continuation targets should be
  matched by `node_id`, not by adjacency). No fixture currently exercises
  real branching; treat multi-branch link targets as unverified.
