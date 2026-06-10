"""Classic CV preprocessing — the front of a traditional OCR pipeline.

Document images in OmniDocBench are mostly clean renders, but `data_requirements.md`
calls out mobile photos / scans with ≤15° skew. We apply a *conservative* deskew
(only when a clear small skew is detected) plus optional light denoise. Conservative
because over-correcting a near-upright clean render can hurt recognition.
"""

from __future__ import annotations

import cv2
import numpy as np

from .enhance import enhance_low_contrast

# Only correct skew within this band. Below MIN we treat as noise (leave as-is);
# above MAX we assume the angle estimate is wrong (e.g. a big figure dominates).
MIN_SKEW_DEG = 0.3
MAX_SKEW_DEG = 15.0


def estimate_skew(gray: np.ndarray) -> float:
    """Estimate page skew (degrees) from the minimum-area rect of foreground ink.

    Returns a signed angle in degrees; 0.0 when no reliable estimate.
    """
    # binarize: ink = dark → foreground white via inverse Otsu
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    coords = cv2.findNonZero(thr)
    if coords is None or len(coords) < 50:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    # Normalize to (-45, 45] — robust to both the legacy (-90, 0] and the
    # OpenCV >=4.5 (0, 90] minAreaRect angle conventions. A near-upright page
    # (bars horizontal) maps to ~0; a tilted page to its small signed skew.
    angle = angle % 90.0
    if angle > 45:
        angle -= 90.0
    return float(angle)


def deskew(image: np.ndarray) -> tuple[np.ndarray, float]:
    """Rotate the image to correct small detected skew. Returns (image, applied_deg)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    angle = estimate_skew(gray)
    if not (MIN_SKEW_DEG <= abs(angle) <= MAX_SKEW_DEG):
        return image, 0.0
    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(
        image, m, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated, angle


def preprocess(
    image: np.ndarray,
    do_deskew: bool = True,
    do_denoise: bool = False,
    do_enhance: bool = True,
) -> tuple[np.ndarray, dict]:
    """Run the preprocessing chain. Returns (image, info) where info logs what ran.

    Order rationale: contrast enhancement runs FIRST. CLAHE makes faded ink
    sharper, which gives the skew estimator (it binarizes ink via Otsu) much more
    reliable foreground on washed-out pages — so enhance-before-deskew helps the
    angle estimate. The enhance step gates binarization internally and is a no-op
    on clean pages, so clean docs flow through unchanged. ``do_enhance`` defaults
    True because the gate (see enhance.estimate_contrast) is conservative enough
    not to touch clean sources.
    """
    info: dict = {"deskew_deg": 0.0, "denoise": False}
    out = image
    if do_enhance:
        out, enhance_info = enhance_low_contrast(out)
        info["enhance"] = enhance_info
    if do_deskew:
        out, deg = deskew(out)
        info["deskew_deg"] = round(deg, 3)
    if do_denoise:
        out = cv2.fastNlMeansDenoisingColored(out, None, 5, 5, 7, 21)
        info["denoise"] = True
    return out, info
