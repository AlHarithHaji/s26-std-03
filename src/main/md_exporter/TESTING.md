# md_exporter — systematic test report (work-plan point 5)

Manual/systematic validation of the exporter before automating it with pytest
(point 6). Every case below was run from the repository root with the CLI
(`python -m md_exporter ...`); the synthetic models live in `tests/fixtures/`
and are reused by the automated suite.

## Test matrix and outcomes

| # | Case | Input | Checks | Outcome |
|---|------|-------|--------|---------|
| T1 | Real model, clean | `BialettiGioia.json` | full render, 7 steps, BoM 18 rows, no warnings section | PASS |
| T2 | Real model, largest | `Air_fryer_Philips_HD9252.json` | 16 steps, 1 warning rendered | PASS |
| T3 | Real model, teammate's | `Oranfresh_gruppo_spremitura.json` | 8 steps, `mass_balance` warning with node ids | PASS |
| T4 | Pagination (FR 19.0) | air fryer, `--steps-per-page 5` | 4 files; prev/next chain; cross-file continuation link `..._page2.md#step-6` | PASS |
| T5 | Depth cut (FR 3.0) | bialetti, `--depth keep_main` | `kept whole — contains N parts` markers; 📦 legend in BoM | PASS |
| T6 | Markdown escaping (D3) | `fixtures/tricky_names.json` | names with `* _ [ ] # < \\ \`` render literally in title, BoM cells and step headings | PASS |
| T7 | All optional fields absent | `fixtures/sparse.json` | placeholders `—` in BoM; the string `None` never appears | PASS |
| T8 | Empty guide (FR 2.3 best-effort) | `fixtures/root_only.json` | document explains itself: 🛑 ERROR warning + "No disassembly steps could be generated" note; not an empty file | PASS |
| T9 | Images (FR 4.1) | `fixtures/with_images.json` | 3 native `![](...)` links (product, action, output; path and URL); `--no-images` → 0 links | PASS |

## Synthetic fixtures (tests/fixtures/)

- **tricky_names.json** — every node name contains Markdown metacharacters;
  proves the output-encoding layer (md_utils).
- **sparse.json** — no weights/materials/colors/tools/images anywhere; proves
  None-robustness of the renderer.
- **root_only.json** — a single isolated component, no operations; proves the
  empty-guide path produces a self-explaining document.
- **with_images.json** — image_path on product, action and output (local path
  and URL); proves FR 4.1 rendering and the --no-images switch.

## Defects found during development (and fixed)

1. **Cross-page dead anchor** (found at point 3): the continuation link of the
   last step of a page pointed to `#step-N` inside the same file, but step N
   lives on the next page. Fixed: the link now targets `<next_page>.md#step-N`.
   Lesson: only *running* the paginated case exposed it.
2. **Raw traceback from the CLI** (found at point 4): `--steps-per-page 0` was
   correctly rejected by ExportOptions but surfaced as a Python traceback.
   Fixed: the CLI translates the ValueError into `error: ...` + exit code 2.
3. **Fixture bug, not exporter bug** (found at point 5): the synthetic models
   first used `from_id`/`to_id` on arrow shapes, while the loader's adapter
   expects `from_shape_id`/`to_shape_id`. The exporter was innocent; the
   fixtures were corrected. Kept on record because it documents the actual
   arrow-key contract of the input format.

## Known observations (not defects)

- Some source models store material/color as numeric ids (e.g. Oranfresh
  material "3"): the loader deliberately does not resolve ids to names, so the
  exporter prints what it receives. Resolving belongs upstream if ever needed.
- The loader substitutes `(empty model)` as product name when no root can be
  identified (T8): the exporter renders it as received.
