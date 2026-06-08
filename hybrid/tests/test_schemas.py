"""M0 DoD — contract schemas import & validate được."""

from __future__ import annotations

from idp.schemas import BBox, Block, DocumentResult, PageResult


def test_bbox_as_xyxy_4():
    b = BBox(quad=[10, 20, 30, 40], page=1)
    assert b.as_xyxy() == (10, 20, 30, 40)


def test_bbox_as_xyxy_8_quad():
    # 4 điểm (8 số) → bao đóng
    b = BBox(quad=[10, 20, 30, 18, 32, 40, 8, 42])
    assert b.as_xyxy() == (8, 18, 32, 42)


def test_block_defaults_and_optional_bbox():
    # Tier B VLM: block không bbox vẫn hợp lệ
    blk = Block(type="text", text="xin chào")
    assert blk.bbox is None
    assert blk.confidence == 1.0
    assert blk.reading_order == 0


def test_table_block():
    blk = Block(type="table", html="<table><tr><td>a</td></tr></table>", reading_order=2)
    assert blk.type == "table"
    assert blk.html.startswith("<table")


def test_document_result_roundtrip():
    doc = DocumentResult(
        document_id="DOC-1",
        tier="B",
        engines_used=["qwen3-vl-8b@lmstudio"],
        pages=[
            PageResult(
                page=0,
                image_uri="x.png",
                blocks=[Block(type="title", text="Tiêu đề", reading_order=0)],
            )
        ],
    )
    dumped = doc.model_dump()
    again = DocumentResult.model_validate(dumped)
    assert again.document_id == "DOC-1"
    assert again.pages[0].blocks[0].text == "Tiêu đề"
    assert again.tier == "B"


def test_document_result_json():
    doc = DocumentResult(document_id="DOC-2")
    s = doc.model_dump_json()
    assert "DOC-2" in s
