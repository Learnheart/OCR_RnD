"""OpenCV preprocessor — deskew nhẹ + quality gate (S1).

Conservative: chỉ chỉnh skew nhỏ rõ ràng (0.3°–15°); ảnh render sạch gần thẳng để
nguyên. Orientation 0/90/180/270 (PP-LCNet doc-orient) để dành — slice đầu
orientation=0. Quality = variance-of-Laplacian → cờ low-quality, KHÔNG reject.
"""

from __future__ import annotations

import cv2
import numpy as np

from idp.preprocess.base import PreprocessedPage, Preprocessor

# Chỉ chỉnh skew trong dải này. Dưới MIN coi như nhiễu; trên MAX coi như ước
# lượng sai (hình lớn lấn át) → bỏ qua.
MIN_SKEW_DEG = 0.3
MAX_SKEW_DEG = 15.0


def estimate_skew(gray: np.ndarray) -> float:
    """Ước lượng góc nghiêng (độ) từ min-area-rect của mực foreground."""
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    coords = cv2.findNonZero(thr)
    if coords is None or len(coords) < 50:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    angle = angle % 90.0
    if angle > 45:
        angle -= 90.0
    return float(angle)


def _deskew(image: np.ndarray, gray: np.ndarray) -> tuple[np.ndarray, float]:
    angle = estimate_skew(gray)
    if not (MIN_SKEW_DEG <= abs(angle) <= MAX_SKEW_DEG):
        return image, 0.0
    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(
        image, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated, angle


def _quality(gray: np.ndarray) -> float:
    """Độ nét: phương sai của Laplacian (cao = nét, thấp = mờ/nhoè)."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


class OpenCVPreprocessor(Preprocessor):
    name = "opencv-deskew"

    def __init__(self, do_deskew: bool = True) -> None:
        self.do_deskew = do_deskew

    def run(self, image: np.ndarray, index: int, source_path: str) -> PreprocessedPage:
        original = image
        out = image
        steps: list[str] = []
        gray0 = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY) if out.ndim == 3 else out
        angle = 0.0
        if self.do_deskew:
            out, angle = _deskew(out, gray0)
            if angle != 0.0:
                steps.append(f"deskew({angle:.2f}°)")
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY) if out.ndim == 3 else out
        q = _quality(gray)
        return PreprocessedPage(
            index=index,
            image=out,
            original=original,
            gray=gray,
            angle_deg=round(angle, 3),
            orientation=0,
            quality_score=round(q, 2),
            source_path=source_path,
            steps=steps or ["noop"],
        )
