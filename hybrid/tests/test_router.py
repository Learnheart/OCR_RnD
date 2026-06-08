"""Test router + serializer + import API/validate (không cần GPU/LM Studio)."""

from __future__ import annotations

from idp.schemas import Block, DocumentResult, PageResult
from idp.serialize.markdown import block_to_md, document_to_md


def test_serialize_table_prefers_html():
    b = Block(type="table", html="<table><tr><td>x</td></tr></table>")
    assert block_to_md(b) == "<table><tr><td>x</td></tr></table>"


def test_serialize_formula_wraps_latex():
    b = Block(type="formula", latex="E = mc^2")
    assert block_to_md(b) == "$$\nE = mc^2\n$$"


def test_serialize_formula_keeps_existing_dollar():
    b = Block(type="formula", latex="$E=mc^2$")
    assert block_to_md(b) == "$E=mc^2$"


def test_serialize_title_heading():
    assert block_to_md(Block(type="title", text="Tiêu đề")) == "# Tiêu đề"


def test_document_to_md_reading_order():
    doc = DocumentResult(
        document_id="d",
        pages=[
            PageResult(
                page=0,
                blocks=[
                    Block(type="text", text="second", reading_order=1),
                    Block(type="title", text="first", reading_order=0),
                ],
            )
        ],
    )
    md = document_to_md(doc)
    assert md.index("first") < md.index("second")


def test_api_and_validate_import():
    # đảm bảo module import được (không khởi tạo server)
    from idp.api import app as api_app
    from idp.validate.gate import validate

    assert api_app.app is not None
    d = DocumentResult(document_id="x")
    assert validate(d) is d
