"""Serializer: Block[] → Markdown matches the OmniDocBench contract."""

from idp_trad.schemas import Block, DocumentResult, PageResult
from idp_trad.serialize.markdown import block_to_md, document_to_md


def test_title_becomes_heading():
    assert block_to_md(Block(type="title", text="Intro")) == "# Intro"


def test_text_plain():
    assert block_to_md(Block(type="text", text="hello world")) == "hello world"


def test_table_uses_html():
    b = Block(type="table", html="<table><tr><td>x</td></tr></table>", text="x")
    assert block_to_md(b) == "<table><tr><td>x</td></tr></table>"


def test_formula_wrapped_once():
    assert block_to_md(Block(type="formula", latex="a^2")) == "$$\na^2\n$$"
    # already-delimited latex is not double-wrapped
    assert block_to_md(Block(type="formula", latex="$a^2$")) == "$a^2$"


def test_empty_formula_drops():
    assert block_to_md(Block(type="formula", latex="")) == ""


def test_document_orders_by_reading_order():
    page = PageResult(blocks=[
        Block(type="text", text="second", reading_order=1),
        Block(type="title", text="first", reading_order=0),
    ])
    doc = DocumentResult(document_id="d", pages=[page])
    md = document_to_md(doc)
    assert md.index("# first") < md.index("second")


def test_blank_document():
    doc = DocumentResult(document_id="d", pages=[PageResult(blocks=[])])
    assert document_to_md(doc).strip() == ""
