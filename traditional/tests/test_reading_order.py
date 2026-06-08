"""XY-cut reading-order recovery."""

from idp_trad.layout.reading_order import order_boxes


def test_single_box():
    assert order_boxes([(0, 0, 10, 10)]) == [0]


def test_empty():
    assert order_boxes([]) == []


def test_two_columns_with_header():
    # header spans full width on top; then left column (2 paras), right column (2)
    header = (0, 0, 200, 20)
    left_top = (0, 40, 90, 60)
    left_bot = (0, 70, 90, 90)
    right_top = (110, 40, 200, 60)
    right_bot = (110, 70, 200, 90)
    boxes = [right_bot, left_top, header, right_top, left_bot]  # shuffled
    order = order_boxes(boxes)
    # header first; left column before right column; top before bottom within column
    seq = [boxes[i] for i in order]
    assert seq[0] == header
    assert seq.index(left_top) < seq.index(left_bot)
    assert seq.index(right_top) < seq.index(right_bot)
    assert seq.index(left_top) < seq.index(right_top)


def test_single_column_top_to_bottom():
    a = (0, 0, 100, 20)
    b = (0, 30, 100, 50)
    c = (0, 60, 100, 80)
    order = order_boxes([c, a, b])
    assert [(0, 0, 100, 20), (0, 30, 100, 50), (0, 60, 100, 80)] == \
        [[c, a, b][i] for i in order]


def test_overlapping_falls_back_to_yx_sort():
    # heavily overlapping boxes (no clean gutter) → stable y,x order
    boxes = [(0, 5, 100, 50), (0, 0, 100, 45)]
    order = order_boxes(boxes)
    assert order == [1, 0]  # the one starting higher (y0=0) comes first
