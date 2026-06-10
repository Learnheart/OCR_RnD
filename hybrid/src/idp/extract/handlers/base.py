"""S3 contract — RegionHandler ABC + crop tiện ích + registry.

Mỗi handler nhận 1 Region + PreprocessedPage → 1 Block (bbox = region.bbox →
grounding mức vùng cho MỌI nhánh, khác V1 no-bbox). Lỗi 1 region → Block rỗng +
warning, không phá trang (xử lý ở pipeline). Handler tự đặt `last_engine`/
`last_latency_s`/`last_warning` để trace đọc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from idp.preprocess.base import PreprocessedPage
from idp.schemas import Block, Region, RegionGroup

# padding (px) nới quanh bbox khi crop — bù sai số bbox detector.
CROP_PAD = 4


def crop_region(image: np.ndarray, region: Region, pad: int = CROP_PAD) -> np.ndarray | None:
    """Cắt ROI của region từ ảnh (kèm padding, clamp biên). None nếu rỗng."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = region.bbox.as_xyxy()
    x0 = max(0, int(round(x0)) - pad)
    y0 = max(0, int(round(y0)) - pad)
    x1 = min(w, int(round(x1)) + pad)
    y1 = min(h, int(round(y1)) + pad)
    if x1 <= x0 or y1 <= y0:
        return None
    return image[y0:y1, x0:x1]


class RegionHandler(ABC):
    group: RegionGroup = "text"
    name: str = "base"

    def __init__(self) -> None:
        self.last_engine: str = self.name
        self.last_latency_s: float = 0.0
        self.last_warning: str | None = None

    @abstractmethod
    def handle(self, region: Region, page: PreprocessedPage) -> Block:
        """Region → Block (luôn gắn bbox = region.bbox)."""
        raise NotImplementedError


def build_registry(handlers: list[RegionHandler]) -> dict[RegionGroup, RegionHandler]:
    """List handler → dict {group: handler}. Trùng group thì cái sau ghi đè."""
    reg: dict[RegionGroup, RegionHandler] = {}
    for h in handlers:
        reg[h.group] = h
    return reg
