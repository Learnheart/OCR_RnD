"""S4 — Reading order qua recursive XY-cut trên bounding box.

Đệ quy cắt theo khoảng trắng rộng nhất: cắt ngang tách band đầy-rộng (header →
body); cắt dọc tách cột. Luôn phát top/left trước → đọc trên→dưới, trái→phải.
Hoạt động ở mức box (không pixel) → rẻ, bền với hình lớn.
"""

from __future__ import annotations

from idp.reading_order.base import ReadingOrderer
from idp.schemas import Block, LayoutResult

Box = tuple[float, float, float, float]  # x0, y0, x1, y1

MIN_GAP = 12.0  # gutter hẹp hơn ngưỡng này không coi là ranh cột/section


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    s = sorted(intervals)
    merged = [list(s[0])]
    for a, b in s[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def _widest_gap(intervals: list[tuple[float, float]]) -> tuple[float, float]:
    merged = _merge_intervals(intervals)
    best_size, best_pos = 0.0, 0.0
    for (_, end), (start, _) in zip(merged, merged[1:]):
        gap = start - end
        if gap > best_size:
            best_size, best_pos = gap, (end + start) / 2.0
    return best_size, best_pos


def _xy_cut(boxes: list[Box], idx: list[int]) -> list[int]:
    if len(idx) <= 1:
        return idx
    x_int = [(boxes[i][0], boxes[i][2]) for i in idx]
    y_int = [(boxes[i][1], boxes[i][3]) for i in idx]
    h_gap, h_pos = _widest_gap(y_int)
    v_gap, v_pos = _widest_gap(x_int)
    if max(h_gap, v_gap) < MIN_GAP:
        return sorted(idx, key=lambda i: (boxes[i][1], boxes[i][0]))
    if h_gap >= v_gap:
        top = [i for i in idx if (boxes[i][1] + boxes[i][3]) / 2.0 < h_pos]
        bottom = [i for i in idx if i not in set(top)]
        return _xy_cut(boxes, top) + _xy_cut(boxes, bottom)
    left = [i for i in idx if (boxes[i][0] + boxes[i][2]) / 2.0 < v_pos]
    right = [i for i in idx if i not in set(left)]
    return _xy_cut(boxes, left) + _xy_cut(boxes, right)


def order_boxes(boxes: list[Box]) -> list[int]:
    """Trả index của `boxes` theo thứ tự đọc khôi phục."""
    return _xy_cut(boxes, list(range(len(boxes))))


class XYCutOrderer(ReadingOrderer):
    name = "xycut"

    def order(self, blocks: list[Block], layout: LayoutResult) -> list[Block]:
        boxed = [b for b in blocks if b.bbox is not None]
        unboxed = [b for b in blocks if b.bbox is None]
        if boxed:
            boxes = [b.bbox.as_xyxy() for b in boxed]
            for rank, i in enumerate(order_boxes(boxes)):
                boxed[i].reading_order = rank
        for j, b in enumerate(unboxed):
            b.reading_order = len(boxed) + j
        ordered = boxed + unboxed
        ordered.sort(key=lambda b: b.reading_order)
        return ordered
