"""Contract models + image loader (no PaddleOCR needed)."""

import numpy as np
import pytest

from idp_trad.ingest.loader import IMAGE_EXTS, LoadedPage, load
from idp_trad.schemas import BBox, Block, DocumentResult


def test_bbox_xyxy_from_4():
    assert BBox(quad=[1, 2, 3, 4]).as_xyxy() == (1, 2, 3, 4)


def test_bbox_xyxy_from_8():
    # 4 points (clockwise) → enclosing box
    assert BBox(quad=[0, 0, 10, 0, 10, 5, 0, 5]).as_xyxy() == (0, 0, 10, 5)


def test_block_defaults():
    b = Block()
    assert b.type == "text" and b.confidence == 1.0 and b.reading_order == 0


def test_document_result_tier_default_A():
    assert DocumentResult(document_id="x").tier == "A"


def test_loadedpage_dims():
    img = np.zeros((30, 40, 3), dtype=np.uint8)
    p = LoadedPage(index=0, image=img, source_path="x")
    assert (p.width, p.height) == (40, 30)


def test_load_png(tmp_path):
    import cv2
    img = np.full((20, 25, 3), 255, dtype=np.uint8)
    f = tmp_path / "sample.png"
    cv2.imwrite(str(f), img)
    with load(f) as doc:
        assert len(doc.pages) == 1
        assert doc.pages[0].width == 25
        assert doc.document_id == "sample"


def test_load_unsupported(tmp_path):
    f = tmp_path / "x.docx"
    f.write_text("nope")
    with pytest.raises(ValueError):
        load(f)


def test_image_exts_cover_common():
    assert {".png", ".jpg", ".jpeg", ".tiff"} <= IMAGE_EXTS
