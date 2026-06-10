"""Conditional contrast normalization for low-contrast / aged documents.

OmniDocBench's worst text sources are aged pages: `newspaper` (text Edit_dist
0.694) and `historical_document` (0.918) vs clean `magazine` (0.167). These pages
are typically washed-out / low-dynamic-range — faded ink on yellowed or grayed
paper. CLAHE (local contrast equalization) and, in the worst case, adaptive
binarization recover the ink so PaddleOCR's detector/recognizer can read it.

The hard constraint is *don't regress the clean majority*. Clean color magazine
renders already have full dynamic range; running CLAHE on them is at best a no-op
and binarization actively destroys color/photographic content. So every transform
is gated behind a deliberately *conservative* low-contrast detector — only
genuinely flat pages get touched; everything else is returned byte-for-byte
unchanged.

All helpers are pure: deterministic, side-effect free, and they never raise on odd
inputs (grayscale, tiny, empty) — they degrade gracefully instead.
"""

from __future__ import annotations

import cv2
import numpy as np

# ── Gating thresholds (tuned conservative — see estimate_contrast) ───────────
# A page is "low contrast" only when it is BOTH globally flat (low std) AND has a
# narrow dynamic range (5–95th percentile spread small). Requiring both keeps
# sparse-but-crisp clean pages (lots of white, little ink → low std, but wide
# spread) from being mislabelled.
#
# Reference points on uint8 [0,255]:
#   * A clean B/W scan: std ~80–110, p95-p5 spread ~230+  → NOT low contrast.
#   * A clean color magazine: std ~50–70, spread ~200+    → NOT low contrast.
#   * A faded newspaper (gray ink on gray paper): std ~25, spread ~70 → LOW.
_LOW_STD = 40.0           # global intensity std below this == flat
_LOW_SPREAD = 110.0       # p95-p5 dynamic range below this == narrow
# Binarization is the most destructive step → only when the page is *very* flat
# AND looks grayscale-ish (low color saturation, i.e. a real document scan, not a
# photo). Stricter than the CLAHE gate on purpose.
_BIN_STD = 28.0
_BIN_SPREAD = 80.0
_BIN_MAX_SATURATION = 35.0  # mean S channel; color/photo pages exceed this


def _to_gray(image: np.ndarray) -> np.ndarray:
    """Best-effort grayscale view of a BGR / gray / odd-shaped array."""
    if image is None:
        return np.zeros((1, 1), dtype=np.uint8)
    arr = np.ascontiguousarray(image)
    if arr.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    if arr.ndim == 2:
        gray = arr
    elif arr.ndim == 3 and arr.shape[2] == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    elif arr.ndim == 3 and arr.shape[2] == 4:
        gray = cv2.cvtColor(arr, cv2.COLOR_BGRA2GRAY)
    elif arr.ndim == 3 and arr.shape[2] == 1:
        gray = arr[:, :, 0]
    else:
        # fall back: collapse to a 2-D view however we can
        gray = arr.reshape(arr.shape[0], -1)
    if gray.dtype != np.uint8:
        gray = np.clip(gray, 0, 255).astype(np.uint8)
    return gray


def _to_bgr(image: np.ndarray) -> np.ndarray:
    """Best-effort 3-channel BGR view (PaddleOCR expects BGR uint8)."""
    arr = np.ascontiguousarray(image)
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.size == 0:
        return np.zeros((0, 0, 3), dtype=np.uint8)
    if arr.ndim == 2:
        return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    if arr.ndim == 3 and arr.shape[2] == 4:
        return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
    if arr.ndim == 3 and arr.shape[2] == 1:
        return cv2.cvtColor(arr[:, :, 0], cv2.COLOR_GRAY2BGR)
    return arr


def estimate_contrast(image: np.ndarray) -> dict:
    """Cheap grayscale contrast stats + a conservative ``low_contrast`` decision.

    Returns a dict with: ``std``, ``p5``, ``p95``, ``spread`` (p95-p5),
    ``mid_gray_frac`` (fraction of pixels in [96,160] — flat pages pile up around
    mid-gray), ``saturation`` (mean S, 0 for grayscale), and ``low_contrast``.
    """
    gray = _to_gray(image)
    if gray.size == 0:
        return {
            "std": 0.0, "p5": 0.0, "p95": 0.0, "spread": 0.0,
            "mid_gray_frac": 0.0, "saturation": 0.0, "low_contrast": False,
        }
    g = gray.astype(np.float32)
    std = float(g.std())
    p5, p95 = (float(v) for v in np.percentile(g, (5, 95)))
    spread = p95 - p5
    mid_gray_frac = float(np.mean((gray >= 96) & (gray <= 160)))

    # saturation: only meaningful for genuine color input
    arr = np.ascontiguousarray(image)
    if arr.ndim == 3 and arr.shape[2] == 3 and arr.dtype == np.uint8:
        saturation = float(cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)[:, :, 1].mean())
    else:
        saturation = 0.0

    # Conservative AND gate: must be both flat and narrow-range to qualify.
    low_contrast = (std < _LOW_STD) and (spread < _LOW_SPREAD)

    return {
        "std": round(std, 2),
        "p5": round(p5, 1),
        "p95": round(p95, 1),
        "spread": round(spread, 1),
        "mid_gray_frac": round(mid_gray_frac, 3),
        "saturation": round(saturation, 1),
        "low_contrast": bool(low_contrast),
    }


def apply_clahe(image: np.ndarray) -> np.ndarray:
    """CLAHE on the L channel (LAB) for local contrast; returns BGR uint8.

    Operating on L (luminance) preserves color; only brightness contrast is
    equalized, which is exactly what faded ink needs.
    """
    bgr = _to_bgr(image)
    if bgr.size == 0:
        return bgr
    try:
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l2 = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((l2, a, b)), cv2.COLOR_LAB2BGR)
    except cv2.error:
        return bgr


def adaptive_binarize(image: np.ndarray) -> np.ndarray:
    """Grayscale → adaptive (Gaussian) threshold w/ Otsu fallback → BGR 3-channel.

    GATED-ONLY helper: binarization wrecks color/photographic pages, so callers
    must restrict it to the very-low-contrast grayscale-document path.
    """
    gray = _to_gray(image)
    if gray.size == 0:
        return _to_bgr(image)
    # light blur first to suppress paper-grain speckle that adaptive thresholding
    # would otherwise turn into salt-and-pepper noise.
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    try:
        binar = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, blockSize=31, C=10,
        )
    except cv2.error:
        binar = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
        )[1]
    return cv2.cvtColor(binar, cv2.COLOR_GRAY2BGR)


def enhance_low_contrast(image: np.ndarray) -> tuple[np.ndarray, dict]:
    """Conditionally enhance a low-contrast page. Returns (image, info).

    On a normal/clean page: returns the input unchanged with
    ``{"low_contrast": False}``. On a flat page: applies CLAHE (always) and, for
    the worst grayscale-document case, adaptive binarization on top.
    """
    stats = estimate_contrast(image)
    info: dict = {
        "low_contrast": stats["low_contrast"],
        "clahe": False,
        "binarized": False,
        "stats": stats,
    }
    if not stats["low_contrast"]:
        return image, info

    out = apply_clahe(image)
    info["clahe"] = True

    # Worst-case path: very flat AND looks like a grayscale document scan (not a
    # color photo) → binarize for maximum ink/paper separation.
    if (
        stats["std"] < _BIN_STD
        and stats["spread"] < _BIN_SPREAD
        and stats["saturation"] < _BIN_MAX_SATURATION
    ):
        out = adaptive_binarize(out)
        info["binarized"] = True

    return out, info
