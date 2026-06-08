"""Pure helpers in the engine (no PaddleOCR — models are imported lazily)."""

from idp_trad.extract.paddle_engine import (
    _extract_table_html,
    _group_lines_to_blocks,
    _join_lines,
    _quad_to_xyxy,
)


def test_quad_to_xyxy():
    quad = [[0, 0], [10, 0], [10, 4], [0, 4]]
    assert _quad_to_xyxy(quad) == (0.0, 0.0, 10.0, 4.0)


def test_join_lines_orders_top_to_bottom():
    items = [
        {"text": "world", "text_region": [[0, 30], [50, 30], [50, 40], [0, 40]]},
        {"text": "hello", "text_region": [[0, 0], [50, 0], [50, 10], [0, 10]]},
    ]
    assert _join_lines(items) == "hello world"


def test_join_lines_skips_empty():
    items = [{"text": "  ", "text_region": [[0, 0], [1, 0], [1, 1], [0, 1]]}]
    assert _join_lines(items) == ""


def test_extract_table_html_strips_wrapper():
    raw = "<html><body><table><tr><td>1</td></tr></table></body></html>"
    assert _extract_table_html({"html": raw}) == "<table><tr><td>1</td></tr></table>"


def test_extract_table_html_empty():
    assert _extract_table_html({"html": ""}) == ""
    assert _extract_table_html(None) == ""


def test_group_lines_splits_on_large_gap():
    # two lines close together, then a big vertical gap, then one line
    lines = [
        ((0, 0, 100, 10), "para1 line1"),
        ((0, 12, 100, 22), "para1 line2"),
        ((0, 200, 100, 210), "para2"),
    ]
    blocks = _group_lines_to_blocks(lines)
    assert len(blocks) == 2
    assert blocks[0].text == "para1 line1 para1 line2"
    assert blocks[1].text == "para2"
