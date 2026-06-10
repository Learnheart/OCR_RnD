"""F3 quality tests: formula LaTeX wrapping, list bullets, table passthrough,
table-HTML cleanup, and graceful formula-engine-missing degrade.

These exercise pure helpers only — no PaddleOCR models are loaded (they are
imported lazily inside the engine methods), so the suite stays fast/offline.
"""

import numpy as np

from idp_trad.extract.paddle_engine import (
    PaddleStructureEngine,
    _clean_latex,
    _clean_table_html,
    _crop_region,
    _extract_table_html,
)
from idp_trad.schemas import Block, DocumentResult, PageResult
from idp_trad.serialize.markdown import block_to_md, document_to_md


# --- (1) formula Block with latex → wrapped in $$…$$, no double $ ---
def test_formula_block_display_wrapped():
    md = block_to_md(Block(type="formula", latex="\\frac{a}{b}"))
    assert md == "$$\n\\frac{a}{b}\n$$"
    # no accidental double wrapping
    assert md.count("$$") == 2


def test_formula_already_delimited_not_double_wrapped():
    assert block_to_md(Block(type="formula", latex="$$x=1$$")) == "$$x=1$$"
    assert block_to_md(Block(type="formula", latex="$x=1$")) == "$x=1$"
    assert block_to_md(Block(type="formula", latex="\\[x=1\\]")) == "\\[x=1\\]"


def test_formula_falls_back_to_text():
    # no latex, only OCR text → still wrapped as display math
    assert block_to_md(Block(type="formula", text="E=mc^2")) == "$$\nE=mc^2\n$$"


# --- (2) list Block → bulleted output ---
def test_list_multiline_becomes_bullets():
    b = Block(type="list", text="apples\nbananas\ncherries")
    assert block_to_md(b) == "- apples\n- bananas\n- cherries"


def test_list_inline_bullets_split():
    b = Block(type="list", text="apples • bananas • cherries")
    assert block_to_md(b) == "- apples\n- bananas\n- cherries"


def test_list_single_item_stays_plain():
    # no confident split → keep plain text (protect the edit-distance score)
    assert block_to_md(Block(type="list", text="just one line")) == "just one line"


def test_list_strips_leading_glyphs():
    b = Block(type="list", text="- a\n* b\n• c")
    assert block_to_md(b) == "- a\n- b\n- c"


# --- (3) table Block html passes through inside markdown ---
def test_table_html_passthrough_in_document():
    html = "<table><tr><td>x</td></tr></table>"
    doc = DocumentResult(
        document_id="d",
        pages=[PageResult(blocks=[Block(type="table", html=html)])],
    )
    assert html in document_to_md(doc)


# --- (4) _extract_table_html cleans messy input to one well-formed table ---
def test_extract_table_html_strips_attrs_keeps_structure():
    messy = (
        "<html><body>"
        '<table border="1" style="width:100%" class="t">'
        '<tr id="r1"><td style="color:red">a</td>'
        '<td colspan="2" class="c">b</td></tr>'
        "</table></body></html>"
    )
    out = _extract_table_html({"html": messy})
    assert out.startswith("<table>")
    assert out.endswith("</table>")
    assert out.count("<table") == 1
    # cosmetic attrs gone…
    assert "style=" not in out
    assert "class=" not in out
    assert "border=" not in out
    assert ' id=' not in out
    # …but structural attrs + every cell preserved
    assert 'colspan="2"' in out
    assert "<td>a</td>" in out
    assert out.count("<td") == 2


def test_clean_table_html_keeps_rowspan():
    raw = '<table><tr><td rowspan="2" style="x">m</td></tr></table>'
    out = _clean_table_html(raw)
    assert 'rowspan="2"' in out
    assert "style=" not in out


# --- _clean_latex strips a single surrounding delimiter pair ---
def test_clean_latex_strips_delimiters():
    assert _clean_latex("$$ a^2 $$") == "a^2"
    assert _clean_latex("$x$") == "x"
    assert _clean_latex("\\[ y \\]") == "y"
    assert _clean_latex("a+b") == "a+b"


def test_crop_region_from_bbox():
    img = np.zeros((100, 100, 3), np.uint8)
    roi = _crop_region(img, {"bbox": [10, 20, 40, 60]})
    assert roi is not None
    assert roi.shape[:2] == (40, 30)
    assert _crop_region(img, {"bbox": [10, 10]}) is None
    assert _crop_region(None, {"bbox": [0, 0, 1, 1]}) is None


# --- (5) formula-engine-missing path → degrade, no crash, no paddle load ---
def test_formula_engine_missing_degrades(monkeypatch):
    eng = PaddleStructureEngine(enable_formula=True)
    # Force the lazy loader to behave as if the model/dep is unavailable.
    monkeypatch.setattr(eng, "_formula_engine", lambda: None)
    blocks: list[Block] = []
    region = {
        "type": "equation",
        "bbox": [0, 0, 10, 10],
        "img": np.zeros((10, 10, 3), np.uint8),
        "res": [{"text": "x+y", "text_region": [[0, 0], [10, 0], [10, 5], [0, 5]]}],
    }
    eng._append_formula(blocks, region, np.zeros((20, 20, 3), np.uint8), None)
    assert len(blocks) == 1
    fb = blocks[0]
    assert fb.type == "formula"
    # degraded to OCR text; latex falls back to the same text (never dropped)
    assert fb.text == "x+y"
    assert fb.latex == "x+y"
    assert eng._formula_engine_name == "none"


def test_recognize_formula_guarded_returns_none_when_no_engine(monkeypatch):
    eng = PaddleStructureEngine()
    monkeypatch.setattr(eng, "_formula_engine", lambda: None)
    assert eng._recognize_formula(np.zeros((5, 5, 3), np.uint8)) is None
