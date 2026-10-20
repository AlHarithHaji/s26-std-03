"""
test_renderer.py — tests of the document content.

The renderer is pure (Guide in, string out), so these tests never touch the
filesystem: they call render_document and assert on the returned text. Each
test corresponds to a row of the point-5 matrix (see TESTING.md).
"""

import pathlib

import pytest

from disassembly_loader import build_guide
from md_exporter import ExportOptions
from md_exporter.renderer import PageInfo, render_document

SINGLE = PageInfo()  # page 1 of 1, no navigation


def _render(guide, options=None, page=SINGLE, steps=None):
    """Tiny helper: render with sane defaults, full step tuple by default."""
    return render_document(
        guide, guide.steps if steps is None else steps,
        options or ExportOptions(), page,
    )


# ------------------------------------------------------------- sections ----

def test_default_render_contains_all_sections(tricky_guide):
    text = _render(tricky_guide)
    assert "# Disassembly Guide" in text
    assert "## Contents" in text
    assert "## Bill of Materials" in text
    assert "## Step 1" in text


def test_options_remove_their_sections(tricky_guide):
    text = _render(
        tricky_guide,
        ExportOptions(include_toc=False, include_bom=False, include_warnings=False),
    )
    assert "## Contents" not in text
    assert "## Bill of Materials" not in text
    assert "Validation warnings" not in text
    assert "## Step 1" in text  # steps are never optional


def test_every_step_gets_anchor_heading_and_toc_link(sparse_guide):
    text = _render(sparse_guide)
    for step in sparse_guide.steps:
        assert f'<a id="step-{step.index}"></a>' in text
        assert f"(#step-{step.index})" in text  # the TOC link


# ------------------------------------------------------------- escaping ----

def test_markdown_metacharacters_are_escaped_everywhere(tricky_guide):
    text = _render(tricky_guide)
    # Node names contain '*carefully*' and '[both]': raw emphasis/link syntax
    # must not survive in the output.
    assert "\\*carefully\\*" in text
    assert "\\[both\\]" in text
    assert "*carefully*" not in text.replace("\\*carefully\\*", "")


def test_the_string_None_never_appears(sparse_guide):
    # Missing data renders as placeholders, never as Python's None.
    assert "None" not in _render(sparse_guide)


def test_missing_bom_attributes_render_as_em_dash(sparse_guide):
    text = _render(sparse_guide)
    assert "| Half A | — | — | — |" in text


# ---------------------------------------------------------------- images ---

def test_images_render_as_native_links_when_enabled(images_guide):
    text = _render(images_guide)
    assert "![Gadget](img/gadget.png)" in text
    assert "(https://example.org/tab.jpg)" in text


def test_no_images_option_removes_every_link(images_guide):
    assert "![" not in _render(images_guide, ExportOptions(include_images=False))


# ------------------------------------------------------------ empty guide --

def test_empty_guide_explains_itself(empty_guide):
    text = _render(empty_guide)
    assert "No disassembly steps could be generated" in text
    assert "Validation warnings" in text  # the reason is right above


# ------------------------------------------------------------- pagination --

def test_single_file_has_no_navigation(tricky_guide):
    text = _render(tricky_guide)
    assert "Next page" not in text and "Previous page" not in text


def test_paginated_pages_link_prev_and_next(images_guide):
    page2 = PageInfo(page_number=2, page_count=3,
                     prev_path="g.md", next_path="g_page3.md")
    text = _render(images_guide, page=page2, steps=images_guide.steps)
    assert "[← Previous page](g.md)" in text
    assert "[Next page →](g_page3.md)" in text
    assert "*Page 2 of 3*" in text


def test_global_sections_appear_only_on_page_one(images_guide):
    page2 = PageInfo(page_number=2, page_count=2, prev_path="g.md")
    text = _render(images_guide, page=page2)
    assert "Bill of Materials" not in text
    assert "Total weight" not in text


def test_last_step_of_a_page_links_into_the_next_file(tmp_path):
    # End-to-end check of the cross-page anchor fix (defect #1 in TESTING.md):
    # needs a model with >1 step, rendered through the real exporter.
    from md_exporter import MDExporter
    fixtures = pathlib.Path(__file__).parent / "fixtures"
    guide = build_guide(str(fixtures / "tricky_names.json"), include_bom=True)
    if len(guide.steps) < 2:
        pytest.skip("fixture has a single step; cross-page link not exercised")
    out = tmp_path / "g.md"
    MDExporter().export(guide, str(out), ExportOptions(steps_per_page=1))
    first_page = out.read_text(encoding="utf-8")
    assert "(g_page2.md#step-2)" in first_page


# ------------------------------------------------------------- smoke test --

def test_smoke_on_one_real_model():
    """
    The only test tied to the loader's real examples (see conftest docstring):
    a whole-pipeline sanity check on Bialetti. If the loader team renames
    their example files this test skips rather than failing the suite.
    """
    real = (pathlib.Path(__file__).parents[2]
            / "disassembly_loader" / "Practical_examples" / "BialettiGioia.json")
    if not real.exists():
        pytest.skip("real example model not present")
    guide = build_guide(str(real), include_bom=True)
    text = _render(guide)
    assert text.count("## Step ") == len(guide.steps)
    assert "Bill of Materials" in text
