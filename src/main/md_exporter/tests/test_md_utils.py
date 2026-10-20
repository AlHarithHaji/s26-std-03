"""
test_md_utils.py — unit tests of the Markdown building blocks.

These are the classic small unit tests: pure functions, tiny inputs, obvious
truths. If one of these fails, the defect is in md_utils itself, not in the
document structure — which is exactly the diagnostic value of testing each
layer separately.
"""

from md_exporter import md_utils as md


# ---------------------------------------------------------------- escaping --

def test_escape_md_neutralizes_emphasis_and_links():
    assert md.escape_md("a *b* _c_ [d]") == r"a \*b\* \_c\_ \[d\]"


def test_escape_md_neutralizes_heading_html_backtick_backslash():
    assert md.escape_md(r"#x <y> `z` \w") == r"\#x \<y> \`z\` \\w"


def test_escape_md_handles_none_and_empty():
    assert md.escape_md(None) == ""
    assert md.escape_md("") == ""


def test_escape_md_flattens_embedded_newlines():
    # Observed in real models: manual word-wrap leaves a literal '\n' inside
    # a node's text, which would otherwise split a numbered list item.
    assert md.escape_md("Insert a nylon \nspudger underneath") == (
        "Insert a nylon spudger underneath"
    )


def test_escape_cell_also_escapes_pipes_and_flattens_newlines():
    # '|' would split the table cell; a newline would break the row.
    assert md.escape_cell("a|b\nc") == r"a\|b c"


# ------------------------------------------------------------------ blocks --

def test_anchor_and_heading_shapes():
    assert md.anchor("step-3") == '<a id="step-3"></a>'
    assert md.heading(2, "Title") == "## Title"


def test_heading_level_is_clamped_to_valid_range():
    assert md.heading(0, "x") == "# x"
    assert md.heading(9, "x") == "###### x"


def test_table_produces_header_separator_and_rows():
    lines = md.table(["A", "B"], [["1", "2"], ["3", "4"]])
    assert lines[0] == "| A | B |"
    assert lines[1].count("---") == 2
    assert lines[2] == "| 1 | 2 |"
    assert len(lines) == 4


def test_image_link_keeps_path_untouched_and_escapes_alt():
    # Path must pass through verbatim (reference-only policy, FR 4.1);
    # alt text is node-derived, hence escaped.
    assert md.image("a*b", "img/x y.png") == r"![a\*b](img/x y.png)"


# ------------------------------------------------------------------ weight --

def test_format_weight_drops_trailing_point_zero():
    assert md.format_weight(260.0, "g") == "260 g"


def test_format_weight_keeps_real_decimals():
    assert md.format_weight(2.5, "kg") == "2.5 kg"


def test_format_weight_unknown_is_em_dash():
    assert md.format_weight(None, "g") == "—"
