"""
conftest.py — shared pytest fixtures for the md_exporter test suite.

pytest auto-discovers this file: every `def` decorated with @pytest.fixture
becomes an injectable argument for any test in this directory. Building
guides here once, session-scoped, keeps the tests fast and keeps the
"how do I get a Guide" plumbing out of every single test.

The suite deliberately runs on the synthetic models in fixtures/ (which this
package owns) rather than on the loader's real example models: if the loader
team renames or edits their examples, this suite shouldn't break for reasons
that have nothing to do with the exporter. One smoke test on a real model is
the only exception (marked as such in test_renderer.py).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

# The loader lives as a sibling of md_exporter in the dev sandbox
# (PROJECT_ROOT/disassembly_loader) but nested one level deeper in the
# course repo (PROJECT_ROOT/loader_se/disassembly_loader). Add whichever one
# actually exists to sys.path so `import disassembly_loader` works either
# way, without touching the loader package itself.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
for _candidate in (PROJECT_ROOT, PROJECT_ROOT / "loader_se"):
    if (_candidate / "disassembly_loader").is_dir() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))
        break

from disassembly_loader import build_guide  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
REAL_MODELS = PROJECT_ROOT / "disassembly_loader" / "Practical_examples"
if not REAL_MODELS.exists():
    REAL_MODELS = PROJECT_ROOT / "loader_se" / "disassembly_loader" / "Practical_examples"


@pytest.fixture(scope="session")
def tricky_guide():
    """Guide whose every name contains Markdown metacharacters (tests escaping)."""
    return build_guide(str(FIXTURES / "tricky_names.json"), include_bom=True)


@pytest.fixture(scope="session")
def sparse_guide():
    """Guide with every optional field absent (tests None-robustness)."""
    return build_guide(str(FIXTURES / "sparse.json"), include_bom=True)


@pytest.fixture(scope="session")
def empty_guide():
    """Guide with zero steps (a single isolated component, FR 2.3 best-effort)."""
    return build_guide(str(FIXTURES / "root_only.json"), include_bom=True)


@pytest.fixture(scope="session")
def images_guide():
    """Guide with image_path on product, action and output (FR 4.1)."""
    return build_guide(str(FIXTURES / "with_images.json"), include_bom=True)
