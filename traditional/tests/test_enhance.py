"""Conditional low-contrast enhancement (OpenCV only — no paddle models)."""

import cv2
import numpy as np

from idp_trad.preprocess.cv_preprocess import preprocess
from idp_trad.preprocess.enhance import (
    adaptive_binarize,
    apply_clahe,
    enhance_low_contrast,
    estimate_contrast,
)


def _low_contrast_page() -> np.ndarray:
    """Faded document: light-gray text on a slightly-lighter gray paper."""
    img = np.full((400, 400, 3), 180, dtype=np.uint8)  # gray paper
    for y in range(60, 340, 40):
        cv2.rectangle(img, (60, y), (340, y + 12), (150, 150, 150), -1)  # faint ink
    return img


def _high_contrast_page() -> np.ndarray:
    """Clean color magazine-ish page: saturated blocks + crisp black text on white."""
    img = np.full((400, 400, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (0, 0), (400, 120), (200, 30, 30), -1)   # blue banner
    cv2.rectangle(img, (0, 280), (400, 400), (20, 180, 40), -1)  # green block
    for y in range(140, 270, 30):
        cv2.rectangle(img, (40, y), (360, y + 10), (0, 0, 0), -1)  # black text
    return img


def _dynamic_range(img: np.ndarray) -> float:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return float(g.std())


# (1) low-contrast synthetic → flagged + dynamic range increases
def test_low_contrast_flagged_and_expanded():
    page = _low_contrast_page()
    stats = estimate_contrast(page)
    assert stats["low_contrast"] is True

    out, info = enhance_low_contrast(page)
    assert info["low_contrast"] is True
    assert info["clahe"] is True
    # CLAHE (or the binarize path) must widen the intensity distribution.
    assert _dynamic_range(out) > _dynamic_range(page)


# (2) high-contrast image → not flagged, returned essentially unchanged
def test_high_contrast_not_flagged_and_unchanged():
    page = _high_contrast_page()
    stats = estimate_contrast(page)
    assert stats["low_contrast"] is False

    out, info = enhance_low_contrast(page)
    assert info["low_contrast"] is False
    assert info["clahe"] is False and info["binarized"] is False
    # returned object is the input untouched
    assert out is page
    assert np.array_equal(out, page)


# (3) preprocess(do_enhance=True) keeps the contract + merges enhance info
def test_preprocess_merges_enhance_info():
    out, info = preprocess(_low_contrast_page(), do_enhance=True)
    assert isinstance(out, np.ndarray)
    assert isinstance(info, dict)
    assert "deskew_deg" in info          # original contract preserved
    assert "enhance" in info
    assert info["enhance"]["low_contrast"] is True


def test_preprocess_enhance_noop_on_clean():
    out, info = preprocess(_high_contrast_page(), do_enhance=True)
    assert "deskew_deg" in info
    assert info["enhance"]["low_contrast"] is False


# (4) edge cases: grayscale + tiny images must not crash, on any helper
def test_grayscale_and_tiny_no_crash():
    gray = np.full((50, 50), 128, dtype=np.uint8)            # single-channel
    tiny = np.full((2, 2, 3), 200, dtype=np.uint8)           # tiny BGR
    empty = np.zeros((0, 0, 3), dtype=np.uint8)              # degenerate

    for sample in (gray, tiny, empty):
        st = estimate_contrast(sample)
        assert "low_contrast" in st
        assert apply_clahe(sample).ndim == 3
        assert adaptive_binarize(sample).ndim == 3
        out, info = enhance_low_contrast(sample)
        assert isinstance(out, np.ndarray) and "low_contrast" in info

    # preprocess on grayscale shouldn't blow up either
    out, info = preprocess(gray, do_enhance=True)
    assert "deskew_deg" in info
