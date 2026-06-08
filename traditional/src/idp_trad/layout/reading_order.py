"""Reading-order recovery via recursive XY-cut on bounding boxes.

The classic traditional algorithm: recursively split a set of boxes by the widest
whitespace gutter. A horizontal cut peels off a full-width band (e.g. a header,
then the body); a vertical cut separates columns. Reading top→bottom and left→right
falls out of always emitting the top/left partition first.

Operates on box-level intervals (not pixels) so it is cheap and robust to figures.
"""

from __future__ import annotations

Box = tuple[float, float, float, float]  # x0, y0, x1, y1

# A gutter narrower than this (px) is not a real column/section break.
MIN_GAP = 12.0


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
    """Return (gap_size, cut_position) for the widest gutter between merged
    intervals. (0.0, 0.0) when there is no gap."""
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
    h_gap, h_pos = _widest_gap(y_int)  # horizontal cut (split top/bottom)
    v_gap, v_pos = _widest_gap(x_int)  # vertical cut (split left/right)

    if max(h_gap, v_gap) < MIN_GAP:
        # no clean cut → stable order top→bottom, then left→right
        return sorted(idx, key=lambda i: (boxes[i][1], boxes[i][0]))

    if h_gap >= v_gap:
        top = [i for i in idx if (boxes[i][1] + boxes[i][3]) / 2.0 < h_pos]
        bottom = [i for i in idx if i not in set(top)]
        return _xy_cut(boxes, top) + _xy_cut(boxes, bottom)
    left = [i for i in idx if (boxes[i][0] + boxes[i][2]) / 2.0 < v_pos]
    right = [i for i in idx if i not in set(left)]
    return _xy_cut(boxes, left) + _xy_cut(boxes, right)


def order_boxes(boxes: list[Box]) -> list[int]:
    """Return indices of `boxes` in recovered reading order."""
    return _xy_cut(boxes, list(range(len(boxes))))
