"""S1 contract — PreprocessedPage + Preprocessor ABC.

PreprocessedPage mang ảnh numpy (BGR) thay vì bytes: detector PPStructure và các
handler paddle đều ăn np.ndarray. `image` là ảnh ĐÃ xử lý (deskew/orient) — mọi
bbox của S2 và crop của S3 tham chiếu hệ toạ độ này. `original` giữ ảnh gốc cho
provenance/trace (before/after).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class PreprocessedPage:
    index: int  # 0-based
    image: np.ndarray  # BGR uint8 (H,W,3) — sau preprocess
    original: np.ndarray  # BGR uint8 — ảnh gốc
    gray: np.ndarray  # ảnh xám của `image`
    angle_deg: float  # góc deskew đã áp (0 nếu không)
    orientation: int  # 0/90/180/270 (0 = không xoay; stub ở slice đầu)
    quality_score: float  # variance-of-Laplacian (cao = nét)
    source_path: str
    steps: list[str] = field(default_factory=list)  # các bước đã chạy

    @property
    def width(self) -> int:
        return int(self.image.shape[1])

    @property
    def height(self) -> int:
        return int(self.image.shape[0])


class Preprocessor(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, image: np.ndarray, index: int, source_path: str) -> PreprocessedPage:
        """Ảnh BGR gốc → PreprocessedPage."""
        raise NotImplementedError
