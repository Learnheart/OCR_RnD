"""F1 trace renderers — artifacts + report. No PaddleOCR / engine needed."""

import json

import numpy as np

from idp_trad.schemas import BBox, Block
from idp_trad.trace.artifacts import dump_page, render_layout_overlay
from idp_trad.trace.models import (
    Artifact,
    DocumentTrace,
    PageTraceRecord,
    StepRecord,
)
from idp_trad.trace.report import render_report, write_report


def _img(h=40, w=50):
    return np.ones((h, w, 3), dtype=np.uint8) * 255


def _blocks():
    return [
        Block(type="title", text="Hello", reading_order=0, bbox=BBox(quad=[2, 2, 20, 10])),
        Block(type="text", text="World", reading_order=1, bbox=BBox(quad=[5, 15, 45, 35])),
    ]


# --- (1) happy path ---------------------------------------------------------


def test_dump_page_happy(tmp_path):
    by_step = dump_page(
        tmp_path,
        original=_img(),
        preprocessed=_img(),
        blocks=_blocks(),
        last_meta={"path_used": "structure", "fallback_used": False, "regions": []},
    )
    # files exist
    assert (tmp_path / "original.png").exists()
    assert (tmp_path / "preprocessed.png").exists()
    assert (tmp_path / "structure_raw.json").exists()
    assert (tmp_path / "layout_overlay.png").exists()
    crops = list((tmp_path / "crops").glob("*.png"))
    assert len(crops) == 2

    # step -> artifact mapping
    assert {a.kind for a in by_step["ingest"]} == {"original_image"}
    assert {a.kind for a in by_step["preprocess"]} == {"preprocessed_image"}
    assert {a.kind for a in by_step["extract"]} == {"structure_raw"}
    ro_kinds = {a.kind for a in by_step["reading_order"]}
    assert "layout_overlay" in ro_kinds and "block_crop" in ro_kinds

    # structure_raw.json is the dumped meta
    meta = json.loads((tmp_path / "structure_raw.json").read_text(encoding="utf-8"))
    assert meta["path_used"] == "structure"


def test_render_layout_overlay_does_not_mutate():
    img = _img()
    before = img.copy()
    out = render_layout_overlay(img, _blocks())
    assert out.shape == img.shape
    assert np.array_equal(img, before)  # input untouched
    assert not np.array_equal(out, img)  # something was drawn


# --- (2) edge cases ---------------------------------------------------------


def test_dump_page_no_bbox_and_empty(tmp_path):
    # block with no bbox + empty blocks list → no crash, no crops
    blocks = [Block(type="text", text="x", reading_order=0, bbox=None)]
    by_step = dump_page(
        tmp_path, original=_img(), preprocessed=_img(), blocks=blocks, last_meta={}
    )
    assert "block_crop" not in {a.kind for a in by_step.get("reading_order", [])}

    d2 = tmp_path / "empty"
    d2.mkdir()
    by_step2 = dump_page(d2, original=None, preprocessed=None, blocks=[], last_meta={})
    # only structure_raw can be written when there are no images
    assert "ingest" not in by_step2 and "preprocess" not in by_step2
    assert (d2 / "structure_raw.json").exists()


def test_dump_page_never_raises_on_bad_bbox(tmp_path):
    # out-of-bounds bbox must be clamped/skipped, not fatal
    b = Block(type="text", reading_order=0, bbox=BBox(quad=[999, 999, 1200, 1200]))
    by_step = dump_page(tmp_path, original=None, preprocessed=_img(), blocks=[b], last_meta={})
    # overlay still produced; the bad crop is simply skipped
    assert (tmp_path / "layout_overlay.png").exists()
    assert "block_crop" not in {a.kind for a in by_step.get("reading_order", [])}


# --- (3) report -------------------------------------------------------------


def _doc_trace(fallback: bool):
    extract = StepRecord(
        step="extract",
        latency_s=0.5,
        summary={
            "path_used": "fallback" if fallback else "structure",
            "fallback_used": fallback,
            "fallback_reason": "struct empty" if fallback else None,
            "struct_chars": 0 if fallback else 120,
            "n_regions": 1,
            "regions": [
                {
                    "reading_order": 0,
                    "type": "text",
                    "bbox": [1, 2, 3, 4],
                    "text_preview": "hi",
                }
            ],
        },
        artifacts=[Artifact(kind="layout_overlay", path="page_000/layout_overlay.png")],
    )
    page = PageTraceRecord(
        page=0, engine="paddle", total_latency_s=1.0, n_blocks=1, steps=[extract]
    )
    return DocumentTrace(document_id="doc1", source_path="x.png", pages=[page])


def test_report_fallback_callout():
    md = render_report(_doc_trace(fallback=True))
    assert "⚠ FALLBACK: struct empty" in md
    assert "fallback pages: 1" in md
    # regions table + artifact link rendered
    assert "Regions" in md and "[1, 2, 3, 4]" in md
    assert "(page_000/layout_overlay.png)" in md


def test_report_no_fallback_shows_path():
    md = render_report(_doc_trace(fallback=False))
    assert "⚠ FALLBACK" not in md
    assert "path: structure" in md


def test_write_report(tmp_path):
    out = write_report(_doc_trace(fallback=True), tmp_path / "report.md")
    assert out.exists()
    assert "Trace report" in out.read_text(encoding="utf-8")
