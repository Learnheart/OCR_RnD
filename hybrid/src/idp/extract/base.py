"""★ CONTRACT (đóng băng trước) — ParseEngine ABC.

Mọi engine trích xuất (Tier 0 direct, Tier B VLM, PaddleOCR-VL, PP-StructureV3…)
hiện thực interface này → swap bằng config, A/B trên cùng OmniDocBench.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from idp.ingest.loader import LoadedPage
from idp.schemas import Block


class ParseEngine(ABC):
    """Trích 1 trang đã nạp → danh sách Block (có reading_order)."""

    #: tên engine ghi vào DocumentResult.engines_used
    name: str = "base"

    @abstractmethod
    def parse(self, page: LoadedPage) -> list[Block]:
        """Trả về list[Block] cho 1 trang. Engine tự gán reading_order."""
        raise NotImplementedError
