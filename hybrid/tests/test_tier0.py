"""M1 DoD — Tier 0 parse 1 PDF số → blocks có bbox + Markdown đúng thứ tự."""

from __future__ import annotations

import fitz

from idp.classify.router import is_digital_born, route
from idp.ingest.loader import load
from idp.pipeline import Pipeline
from idp.serialize.markdown import document_to_md


def _make_pdf(path: str) -> None:
    # Dùng ASCII: font base-14 (Helvetica) của PyMuPDF không encode được dấu
    # tiếng Việt khi TẠO pdf — đây là giới hạn font test, không phải engine.
    doc = fitz.open()
    page = doc.new_page()  # A4 mặc định
    page.insert_text((72, 72), "Financial Report 2026", fontsize=16)
    page.insert_text((72, 120), "First content line.", fontsize=11)
    page.insert_text((72, 150), "Second content line.", fontsize=11)
    doc.save(path)
    doc.close()


def test_tier0_blocks_have_bbox_and_text(tmp_path):
    pdf = tmp_path / "doc.pdf"
    _make_pdf(str(pdf))

    with load(str(pdf)) as ld:
        assert len(ld.pages) == 1
        page = ld.pages[0]
        # PDF số → digital-born → Tier 0
        assert is_digital_born(page)
        assert route(page) == "0"

        from idp.extract.tier0_direct import Tier0DirectEngine

        blocks = Tier0DirectEngine().parse(page)
        assert blocks, "phải có ít nhất 1 block"
        for b in blocks:
            assert b.bbox is not None, "Tier 0 mọi block phải có bbox"
            assert b.text
        # reading order tăng dần
        orders = [b.reading_order for b in blocks]
        assert orders == sorted(orders)


def test_tier0_pipeline_to_markdown(tmp_path):
    pdf = tmp_path / "doc.pdf"
    _make_pdf(str(pdf))

    pipe = Pipeline()
    doc = pipe.process_file(str(pdf))
    assert doc.tier == "0"
    assert doc.engines_used == ["tier0-pymupdf"]

    md = document_to_md(doc)
    assert "Financial Report 2026" in md
    assert "First content line" in md
    # thứ tự: tiêu đề trước nội dung
    assert md.index("Financial Report") < md.index("First content")
