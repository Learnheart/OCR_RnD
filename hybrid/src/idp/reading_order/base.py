"""S4 contract — ReadingOrderer ABC.

In: Block[] (mọi handler) + LayoutResult. Out: cùng Block[] đã gán reading_order
liên tục theo thứ tự đọc (barrier — cần mọi block để sắp xếp).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from idp.schemas import Block, LayoutResult


class ReadingOrderer(ABC):
    name: str = "base"

    @abstractmethod
    def order(self, blocks: list[Block], layout: LayoutResult) -> list[Block]:
        raise NotImplementedError
