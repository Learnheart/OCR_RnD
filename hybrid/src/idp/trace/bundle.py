"""Per-page trace bundle (R9) — mỗi trang 1 folder, mỗi step rơi artifact vào đó.

Mục tiêu: mở `page_index.html` là thấy rõ 5 step (preprocess → layout → handlers →
reading order → output) cạnh nhau, ảnh + dữ liệu, không cần đọc code. Overlay vẽ
bằng OpenCV (không thêm dependency nặng). `enabled=False` → no-op (full run nhanh).

Cấu trúc (xem design.md mục 10.1):
  <run_dir>/<page_stem>/
    00_input.jpg
    01_preprocess/ {preprocess.json, before_after.jpg}
    02_layout/     {regions.json, overlay.jpg, crops/}
    03_handlers/   {blocks_raw.json, <group>/r##.*, overlay_ocr.jpg}
    04_reading_order/ {order.json, order_overlay.jpg}
    05_output/     {page.md, page.json}
    page_index.html, page_trace.json
"""

from __future__ import annotations

import html as _html
import json
from pathlib import Path

import cv2
import numpy as np

from idp.preprocess.base import PreprocessedPage
from idp.schemas import Block, LayoutResult, Region

# Màu BGR theo group (design mục 10.2).
GROUP_COLORS: dict[str, tuple[int, int, int]] = {
    "text": (255, 90, 0),     # lam
    "table": (0, 170, 0),     # lục
    "formula": (0, 0, 230),   # đỏ
    "chart": (0, 140, 255),   # cam
    "seal": (200, 0, 160),    # tím
    "drop": (170, 170, 170),  # xám
}
_FIELD_EXT = {"text": "txt", "html": "html", "latex": "tex"}


def _imwrite(path: Path, img: np.ndarray) -> None:
    """imwrite an toàn unicode path (cv2.imwrite hỏng với path non-ASCII)."""
    ext = path.suffix or ".jpg"
    ok, buf = cv2.imencode(ext, img)
    if ok:
        path.parent.mkdir(parents=True, exist_ok=True)
        buf.tofile(str(path))


def _ascii(s: str, n: int = 40) -> str:
    """Preview ASCII-safe cho putText (cv2 không vẽ được CJK)."""
    s = (s or "").replace("\n", " ")
    return s.encode("ascii", "replace").decode("ascii")[:n]


def _label_box(img, x0, y0, text, color):
    """Vẽ nhãn nền đặc phía trên-trái box cho dễ đọc."""
    font, scale, th = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
    (tw, tht), _ = cv2.getTextSize(text, font, scale, th)
    yy = max(0, y0 - 4)
    cv2.rectangle(img, (x0, yy - tht - 4), (x0 + tw + 4, yy), color, -1)
    cv2.putText(img, text, (x0 + 2, yy - 3), font, scale, (255, 255, 255), th, cv2.LINE_AA)


class TraceBundle:
    def __init__(self, run_dir: Path, page_stem: str, enabled: bool = True) -> None:
        self.enabled = enabled
        self.page_dir = Path(run_dir) / page_stem
        self.page_stem = page_stem
        self.trace: dict = {"page_stem": page_stem, "steps": {}, "warnings": []}
        if enabled:
            self.page_dir.mkdir(parents=True, exist_ok=True)

    # ── S0 input ──
    def save_input(self, image: np.ndarray) -> None:
        if not self.enabled:
            return
        _imwrite(self.page_dir / "00_input.jpg", image)

    # ── S1 preprocess ──
    def save_preprocess(self, pp: PreprocessedPage) -> None:
        if not self.enabled:
            return
        d = self.page_dir / "01_preprocess"
        d.mkdir(parents=True, exist_ok=True)
        info = {
            "angle_deg": pp.angle_deg,
            "orientation": pp.orientation,
            "quality_score": pp.quality_score,
            "steps": pp.steps,
        }
        (d / "preprocess.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # before/after ghép ngang (resize cùng chiều cao)
        before, after = pp.original, pp.image
        h = min(before.shape[0], after.shape[0], 900)

        def _fit(im):
            scale = h / im.shape[0]
            return cv2.resize(im, (int(im.shape[1] * scale), h))

        gap = np.full((h, 12, 3), 255, np.uint8)
        _imwrite(d / "before_after.jpg", np.hstack([_fit(before), gap, _fit(after)]))
        self.trace["steps"]["preprocess"] = info

    # ── S2 layout ──
    def save_layout(self, layout: LayoutResult, image: np.ndarray) -> None:
        if not self.enabled:
            return
        d = self.page_dir / "02_layout"
        crops = d / "crops"
        crops.mkdir(parents=True, exist_ok=True)
        regions_json = []
        overlay = image.copy()
        for r in layout.regions:
            x0, y0, x1, y1 = (int(round(v)) for v in r.bbox.as_xyxy())
            color = GROUP_COLORS.get(r.group, (0, 0, 0))
            cv2.rectangle(overlay, (x0, y0), (x1, y1), color, 2)
            _label_box(overlay, x0, y0, f"#{r.region_id} {r.label} {r.score:.2f}", color)
            roi = image[max(0, y0):max(0, y1), max(0, x0):max(0, x1)]
            if roi.size:
                _imwrite(crops / f"r{r.region_id:02d}_{r.group}.jpg", roi)
            regions_json.append({
                "region_id": r.region_id, "label": r.label, "group": r.group,
                "bbox": [x0, y0, x1, y1], "score": round(r.score, 4),
            })
        (d / "regions.json").write_text(
            json.dumps(regions_json, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _imwrite(d / "overlay.jpg", overlay)
        self.trace["steps"]["layout"] = {"n_regions": len(regions_json)}

    # ── S3 handlers ──
    def save_handlers(
        self,
        results: list[dict],  # mỗi: {region, block, engine, latency_s, warning}
        image: np.ndarray,
    ) -> None:
        if not self.enabled:
            return
        d = self.page_dir / "03_handlers"
        d.mkdir(parents=True, exist_ok=True)
        blocks_raw = []
        overlay = image.copy()
        for item in results:
            r: Region = item["region"]
            b: Block = item["block"]
            grp = r.group
            color = GROUP_COLORS.get(grp, (0, 0, 0))
            content = b.text or b.html or b.latex or ""
            field = "text" if b.text else "html" if b.html else "latex" if b.latex else "text"
            # ghi file nội dung mỗi vùng
            sub = d / grp
            sub.mkdir(parents=True, exist_ok=True)
            (sub / f"r{r.region_id:02d}.{_FIELD_EXT.get(field, 'txt')}").write_text(
                content or "", encoding="utf-8"
            )
            # overlay text preview
            x0, y0, x1, y1 = (int(round(v)) for v in r.bbox.as_xyxy())
            cv2.rectangle(overlay, (x0, y0), (x1, y1), color, 1)
            _label_box(overlay, x0, y0, f"#{r.region_id} {_ascii(content, 30)}", color)
            blocks_raw.append({
                "region_id": r.region_id, "group": grp, "type": b.type,
                "field": field, "chars": len(content), "engine": item.get("engine"),
                "latency_s": round(item.get("latency_s", 0.0), 3),
                "warning": item.get("warning"),
                "preview": content[:120].replace("\n", " "),
            })
            if item.get("warning"):
                self.trace["warnings"].append(f"r{r.region_id} ({grp}): {item['warning']}")
        (d / "blocks_raw.json").write_text(
            json.dumps(blocks_raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _imwrite(d / "overlay_ocr.jpg", overlay)
        self.trace["steps"]["handlers"] = {"n_blocks": len(blocks_raw)}
        self._blocks_raw = blocks_raw  # dùng cho page_index.html

    # ── S4 reading order ──
    def save_reading_order(self, ordered: list[Block], image: np.ndarray) -> None:
        if not self.enabled:
            return
        d = self.page_dir / "04_reading_order"
        d.mkdir(parents=True, exist_ok=True)
        overlay = image.copy()
        order_json = []
        centers: list[tuple[int, int]] = []
        for b in ordered:
            if b.bbox is None:
                continue
            x0, y0, x1, y1 = (int(round(v)) for v in b.bbox.as_xyxy())
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            centers.append((cx, cy))
            cv2.rectangle(overlay, (x0, y0), (x1, y1), (120, 120, 120), 1)
            order_json.append({"reading_order": b.reading_order, "type": b.type,
                               "bbox": [x0, y0, x1, y1]})
        # mũi tên nối luồng đọc
        for (p, q) in zip(centers, centers[1:]):
            cv2.arrowedLine(overlay, p, q, (0, 0, 255), 2, tipLength=0.03)
        for rank, (cx, cy) in enumerate(centers):
            cv2.circle(overlay, (cx, cy), 16, (0, 0, 255), -1)
            cv2.putText(overlay, str(rank), (cx - 8, cy + 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        (d / "order.json").write_text(
            json.dumps(order_json, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _imwrite(d / "order_overlay.jpg", overlay)
        self.trace["steps"]["reading_order"] = {"n_ordered": len(order_json)}

    # ── S5 output ──
    def save_output(self, markdown: str, doc_json: str) -> None:
        if not self.enabled:
            return
        d = self.page_dir / "05_output"
        d.mkdir(parents=True, exist_ok=True)
        (d / "page.md").write_text(markdown, encoding="utf-8")
        (d / "page.json").write_text(doc_json, encoding="utf-8")
        self._markdown = markdown

    # ── finalize ──
    def finalize(self) -> dict:
        if not self.enabled:
            return self.trace
        (self.page_dir / "page_trace.json").write_text(
            json.dumps(self.trace, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._write_page_html()
        return self.trace

    def _write_page_html(self) -> None:
        blocks_raw = getattr(self, "_blocks_raw", [])
        md = getattr(self, "_markdown", "")
        pp = self.trace["steps"].get("preprocess", {})
        rows = "".join(
            f"<tr><td>#{b['region_id']}</td><td>{b['group']}</td><td>{b['type']}</td>"
            f"<td>{b['chars']}</td><td>{b['latency_s']}s</td>"
            f"<td>{_html.escape(b.get('engine') or '')}</td>"
            f"<td>{_html.escape(b.get('warning') or '')}</td>"
            f"<td><code>{_html.escape(b['preview'])}</code></td></tr>"
            for b in blocks_raw
        )
        warns = "".join(f"<li>{_html.escape(w)}</li>" for w in self.trace["warnings"])
        html = f"""<!doctype html><meta charset="utf-8">
<title>{_html.escape(self.page_stem)} — V2 trace</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;margin:0;background:#f4f5f7;color:#222}}
 h2{{background:#2d3748;color:#fff;margin:0;padding:10px 16px;font-size:16px}}
 section{{background:#fff;margin:14px;padding:12px 16px;border-radius:8px;box-shadow:0 1px 3px #0002}}
 img{{max-width:100%;border:1px solid #ccc;border-radius:4px}}
 table{{border-collapse:collapse;width:100%;font-size:12px}}
 td,th{{border:1px solid #ddd;padding:4px 6px;text-align:left;vertical-align:top}}
 code{{font-size:11px}} pre{{white-space:pre-wrap;background:#f8f8f8;padding:8px;border-radius:4px}}
 .warn{{color:#b00}}
</style>
<h2>{_html.escape(self.page_stem)} — Hybrid V2 pipeline trace</h2>
<section><h3>S1 · Preprocess</h3>
 <p>angle={pp.get('angle_deg')}° · orientation={pp.get('orientation')} ·
    quality={pp.get('quality_score')} · steps={_html.escape(str(pp.get('steps')))}</p>
 <img src="01_preprocess/before_after.jpg"></section>
<section><h3>S2 · Layout detect</h3>
 <p>{self.trace['steps'].get('layout',{}).get('n_regions',0)} regions ·
    màu: <b style="color:#06f">text</b> · <b style="color:#0a0">table</b> ·
    <b style="color:#e00">formula</b> · <b style="color:#f80">chart</b> ·
    <b style="color:#a09">seal</b></p>
 <img src="02_layout/overlay.jpg"></section>
<section><h3>S3 · Handlers (fan-out)</h3>
 <img src="03_handlers/overlay_ocr.jpg">
 <table><tr><th>region</th><th>group</th><th>type</th><th>chars</th><th>lat</th>
   <th>engine</th><th>warning</th><th>preview</th></tr>{rows}</table></section>
<section><h3>S4 · Reading order</h3>
 <img src="04_reading_order/order_overlay.jpg"></section>
<section><h3>S5 · Output markdown</h3>
 <pre>{_html.escape(md)}</pre></section>
{'<section class="warn"><h3>⚠ Warnings</h3><ul>' + warns + '</ul></section>' if warns else ''}
"""
        (self.page_dir / "page_index.html").write_text(html, encoding="utf-8")


def write_run_index(run_dir: Path, pages: list[dict], meta: dict) -> None:
    """Lưới thumbnail mọi trang → link tới page_index.html từng trang."""
    run_dir = Path(run_dir)
    cards = ""
    for p in pages:
        stem = p["page_stem"]
        cards += (
            f'<a class="card" href="{stem}/page_index.html">'
            f'<img src="{stem}/02_layout/overlay.jpg" loading="lazy">'
            f'<div>{_html.escape(stem)}<br><small>{p.get("n_regions",0)} regions · '
            f'{p.get("latency_s",0):.1f}s</small></div></a>'
        )
    html = f"""<!doctype html><meta charset="utf-8"><title>V2 run — {_html.escape(meta.get('run_name',''))}</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;margin:16px;background:#f4f5f7}}
 h1{{font-size:18px}} .meta{{color:#555;font-size:13px;margin-bottom:12px}}
 .grid{{display:flex;flex-wrap:wrap;gap:12px}}
 .card{{display:block;width:240px;background:#fff;border-radius:8px;overflow:hidden;
   box-shadow:0 1px 3px #0002;text-decoration:none;color:#222}}
 .card img{{width:100%;height:300px;object-fit:contain;background:#fafafa;border-bottom:1px solid #eee}}
 .card div{{padding:8px;font-size:13px}}
</style>
<h1>Hybrid V2 — {_html.escape(meta.get('run_name',''))}</h1>
<div class="meta">{_html.escape(json.dumps(meta, ensure_ascii=False))}</div>
<div class="grid">{cards}</div>
"""
    (run_dir / "index.html").write_text(html, encoding="utf-8")
    (run_dir / "run_meta.json").write_text(
        json.dumps({"meta": meta, "pages": pages}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
