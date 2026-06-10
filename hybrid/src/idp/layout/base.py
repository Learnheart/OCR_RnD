"""S2 contract — LayoutDetector ABC + ánh xạ nhãn → RegionGroup.

Detector swappable: PPStructure 2.x (cài sẵn) hôm nay; PP-DocLayout_plus-L /
DocLayout-YOLO sau, cùng interface. Bảng map nhãn→group quy về 5 nhánh fan-out.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from idp.preprocess.base import PreprocessedPage
from idp.schemas import LayoutResult, RegionGroup

# Nhãn detector (PPStructure 2.x + dự phòng nhãn PP-DocLayout) → nhánh fan-out.
# PPStructure(en) trả: text/title/list/table/figure; (ch) thêm header/footer/
# reference/equation/figure_caption/table_caption. Map rộng để swap detector khác.
LABEL_TO_GROUP: dict[str, RegionGroup] = {
    # text-ish
    "text": "text",
    "title": "text",
    "doc_title": "text",
    "paragraph_title": "text",
    "list": "text",
    "reference": "text",
    "abstract": "text",
    "content": "text",
    "header": "text",
    "footer": "text",
    "footnote": "text",
    "aside_text": "text",
    "number": "text",
    "figure_caption": "text",
    "table_caption": "text",
    "chart_title": "text",
    "figure_title": "text",
    "table_title": "text",
    "algorithm": "text",
    # table
    "table": "table",
    # formula
    "equation": "formula",
    "formula": "formula",
    "formula_number": "formula",
    # chart / figure
    "figure": "chart",
    "chart": "chart",
    # seal
    "seal": "seal",
    # drop (vùng không lấy nội dung)
    "abandon": "drop",
    "page_number": "drop",
}

DEFAULT_GROUP: RegionGroup = "text"


def label_to_group(label: str) -> RegionGroup:
    return LABEL_TO_GROUP.get(label.lower().strip(), DEFAULT_GROUP)


class LayoutDetector(ABC):
    name: str = "base"

    @abstractmethod
    def detect(self, page: PreprocessedPage) -> LayoutResult:
        """PreprocessedPage → LayoutResult{regions} (bbox theo `page.image`)."""
        raise NotImplementedError
