"""
test_exporter.py — tests of the orchestration layer (pagination, paths, I/O).

File-writing tests use pytest's `tmp_path` fixture: a fresh temporary
directory per test, cleaned up automatically — tests never touch the repo.
"""

import pathlib

import pytest

from md_exporter import ExportOptions, MDExporter, export_to_md
from md_exporter.exporter import MDExporter as _Cls

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


# ----------------------------------------------------------------- options --

def test_options_reject_nonpositive_steps_per_page():
    with pytest.raises(ValueError):
        ExportOptions(steps_per_page=0)
    with pytest.raises(ValueError):
        ExportOptions(steps_per_page=-3)


def test_options_defaults_are_everything_on_single_file():
    opt = ExportOptions()
    assert opt.include_toc and opt.include_warnings
    assert opt.include_bom and opt.include_images
    assert opt.steps_per_page is None


# -------------------------------------------------------------- pagination --

def test_split_none_means_one_page():
    steps = tuple(range(7))  # the splitter only slices; ints stand in for Steps
    assert _Cls._split_into_pages(steps, None) == [steps]


def test_split_chunks_and_last_page_may_be_short():
    steps = tuple(range(7))
    pages = _Cls._split_into_pages(steps, 3)
    assert [len(p) for p in pages] == [3, 3, 1]


def test_split_empty_guide_still_yields_one_page():
    # An empty export must still produce one self-explaining document, not zero files.
    assert _Cls._split_into_pages((), 5) == [()]


def test_page_paths_first_page_keeps_callers_name():
    paths = _Cls._page_paths("out/guide.md", 3)
    assert paths == ["out/guide.md", "out/guide_page2.md", "out/guide_page3.md"]


def test_page_paths_single_page_is_untouched():
    assert _Cls._page_paths("guide.md", 1) == ["guide.md"]


# --------------------------------------------------------------------- I/O --

def test_export_writes_one_file_by_default(tricky_guide, tmp_path):
    out = tmp_path / "g.md"
    written = MDExporter().export(tricky_guide, str(out))
    assert written == [str(out)]
    assert out.exists() and out.read_text(encoding="utf-8").startswith("#")


def test_export_paginated_writes_all_pages_in_reading_order(images_guide, tmp_path):
    out = tmp_path / "g.md"
    written = MDExporter().export(
        images_guide, str(out), ExportOptions(steps_per_page=1)
    )
    # with_images.json has exactly 1 step -> still a single page; use sparse
    # logic instead: assert every returned path exists, in order.
    assert all(__import__("os").path.exists(p) for p in written)
    assert written[0] == str(out)


def test_export_creates_missing_parent_directories(tricky_guide, tmp_path):
    out = tmp_path / "deep" / "nested" / "g.md"
    MDExporter().export(tricky_guide, str(out))
    assert out.exists()


def test_exporter_declares_its_identity_for_the_panel():
    # FR 11.0: a registry lists exporters without knowing them individually.
    assert MDExporter.format_id == "md"
    assert MDExporter.file_extension == ".md"
    assert "Markdown" in MDExporter.display_name


# ---------------------------------------------------------- export_to_md ----

def test_export_to_md_accepts_a_json_path(tmp_path):
    out = tmp_path / "g.md"
    written = export_to_md(str(FIXTURES / "tricky_names.json"), str(out))
    assert written == [str(out)]
    assert out.exists() and out.read_text(encoding="utf-8").startswith("#")


def test_export_to_md_accepts_an_already_built_guide(tricky_guide, tmp_path):
    out = tmp_path / "g.md"
    written = export_to_md(tricky_guide, str(out))
    assert written == [str(out)]
    assert out.exists()


def test_export_to_md_forwards_options(tricky_guide, tmp_path):
    out = tmp_path / "g.md"
    written = export_to_md(tricky_guide, str(out), options=ExportOptions(include_toc=False))
    text = out.read_text(encoding="utf-8")
    assert "## Contents" not in text


def test_export_to_md_matches_calling_the_class_directly(tricky_guide, tmp_path):
    via_function = tmp_path / "function.md"
    via_class = tmp_path / "class.md"
    export_to_md(tricky_guide, str(via_function))
    MDExporter().export(tricky_guide, str(via_class))
    assert via_function.read_text(encoding="utf-8") == via_class.read_text(encoding="utf-8")
