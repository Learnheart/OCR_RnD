"""CV preprocessing (OpenCV only)."""

import cv2
import numpy as np

from idp_trad.preprocess.cv_preprocess import deskew, estimate_skew, preprocess


def _text_like_image(angle_deg: float = 0.0) -> np.ndarray:
    """White page with horizontal black bars (text rows), optionally rotated."""
    img = np.full((400, 400, 3), 255, dtype=np.uint8)
    for y in range(60, 340, 40):
        cv2.rectangle(img, (60, y), (340, y + 12), (0, 0, 0), -1)
    if angle_deg:
        m = cv2.getRotationMatrix2D((200, 200), angle_deg, 1.0)
        img = cv2.warpAffine(img, m, (400, 400), borderValue=(255, 255, 255))
    return img


def test_estimate_skew_near_zero_on_upright():
    assert abs(estimate_skew(cv2.cvtColor(_text_like_image(), cv2.COLOR_BGR2GRAY))) < 1.0


def test_deskew_corrects_small_rotation():
    rotated = _text_like_image(angle_deg=6.0)
    _, applied = deskew(rotated)
    # a clear ~6° skew should trigger a correction within the allowed band
    assert abs(applied) > 0.3


def test_deskew_leaves_upright_untouched():
    _, applied = deskew(_text_like_image(0.0))
    assert applied == 0.0


def test_preprocess_returns_info():
    out, info = preprocess(_text_like_image(0.0))
    assert out.shape == (400, 400, 3)
    assert "deskew_deg" in info and info["denoise"] is False


def test_preprocess_blank_image_safe():
    blank = np.full((100, 100, 3), 255, dtype=np.uint8)
    out, info = preprocess(blank)
    assert out.shape == blank.shape
