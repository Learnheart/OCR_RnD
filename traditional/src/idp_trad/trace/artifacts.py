"""Artifact renderers for the run tracer (feature F1).

The Tracer (idp_trad.trace.tracer) calls `dump_page(...)` after each page, handing
us the original + preprocessed images, the final ordered blocks, and the engine's
`last_meta`. We write inspectable files under the page dir and return a mapping
{step_name: [Artifact, ...]} so the Tracer can attach each file to its step record.

Hard rule: tracing must NEVER raise into the pipeline. Every risky op is wrapped so a
single bad block (or a missing image) is skipped, not fatal. The Tracer guards too,
but we are defensive here so partial output still lands.

Image writes are unicode-safe: cv2.imwrite chokes on non-ASCII paths on Windows, so
we mirror loader.py's `_imread_unicode` in reverse (cv2.imencode + ndarray.tofile).
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from idp_trad.trace.models import Artifact

# Fixed colour legend (BGR, since cv2 is BGR). Keyed by Block.type.
_TYPE_COLORS: dict[str, tuple[int, int, int]] = {
    "text": (0, 200, 0),  # green
    "title": (220, 0, 0),  # blue
    "table": (0, 140, 255),  # orange
    "formula": (255, 0, 255),  # magenta
    "list": (255, 255, 0),  # cyan
    "header": (150, 150, 150),  # gray
    "footer": (150, 150, 150),  # gray
    "figure": (0, 0, 230),  # red
}
_DEFAULT_COLOR = (0, 200, 0)

# Cap crops so a dense page can't flood the trace dir.
_MAX_CROPS = 60


def _imwrite_unicode(path: Path, image: np.ndarray) -> bool:
    """cv2.imwrite-equivalent that survives non-ASCII Windows paths.

    Returns True on success, False (never raises) on any failure.
    """
    try:
        ext = path.suffix or ".png"
        ok, buf = cv2.imencode(ext, image)
        if not ok:
            return False
        buf.tofile(str(path))
        return True
    except Exception:  # noqa: BLE001 — tracing must never raise
        return False


def _color_for(block_type: str) -> tuple[int, int, int]:
    return _TYPE_COLORS.get(block_type or "", _DEFAULT_COLOR)


def _clamp_box(
    x0: float, y0: float, x1: float, y1: float, w: int, h: int
) -> tuple[int, int, int, int]:
    ix0 = max(0, min(int(round(x0)), w))
    iy0 = max(0, min(int(round(y0)), h))
    ix1 = max(0, min(int(round(x1)), w))
    iy1 = max(0, min(int(round(y1)), h))
    if ix1 < ix0:
        ix0, ix1 = ix1, ix0
    if iy1 < iy0:
        iy0, iy1 = iy1, iy0
    return ix0, iy0, ix1, iy1


def render_layout_overlay(image: np.ndarray, blocks: list) -> np.ndarray:
    """Draw each block's bbox (coloured by type) + reading-order number.

    Returns an annotated COPY; the input image is not mutated. Never raises.
    """
    canvas = image.copy()
    h, w = canvas.shape[:2]
    for b in blocks:
        try:
            bbox = getattr(b, "bbox", None)
            if bbox is None:
                continue
            x0, y0, x1, y1 = bbox.as_xyxy()
            ix0, iy0, ix1, iy1 = _clamp_box(x0, y0, x1, y1, w, h)
            btype = getattr(b, "type", "text")
            color = _color_for(btype)
            cv2.rectangle(canvas, (ix0, iy0), (ix1, iy1), color, 2)
            order = int(getattr(b, "reading_order", 0))
            label = str(order)
            # label background just inside the top-left corner
            ty = max(iy0 + 16, 16)
            cv2.putText(
                canvas,
                label,
                (ix0 + 2, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                3,
                cv2.LINE_AA,
            )
            cv2.putText(
                canvas,
                label,
                (ix0 + 2, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                1,
                cv2.LINE_AA,
            )
        except Exception:  # noqa: BLE001 — skip one bad block, never fatal
            continue
    return canvas


def _dump_crops(page_dir: Path, preprocessed: np.ndarray, blocks: list) -> list[Artifact]:
    """Write per-block crops into `crops/`. Capped, unicode-safe, never raises."""
    arts: list[Artifact] = []
    crops_dir = page_dir / "crops"
    try:
        crops_dir.mkdir(parents=True, exist_ok=True)
    except Exception:  # noqa: BLE001
        return arts
    h, w = preprocessed.shape[:2]
    written = 0
    for b in blocks:
        if written >= _MAX_CROPS:
            break
        try:
            bbox = getattr(b, "bbox", None)
            if bbox is None:
                continue
            x0, y0, x1, y1 = bbox.as_xyxy()
            ix0, iy0, ix1, iy1 = _clamp_box(x0, y0, x1, y1, w, h)
            if ix1 <= ix0 or iy1 <= iy0:
                continue  # empty crop
            crop = preprocessed[iy0:iy1, ix0:ix1]
            if crop.size == 0:
                continue
            order = int(getattr(b, "reading_order", 0))
            btype = str(getattr(b, "type", "text"))
            name = f"{order:02d}_{btype}.png"
            out = crops_dir / name
            if _imwrite_unicode(out, crop):
                arts.append(
                    Artifact(
                        kind="block_crop",
                        path=str(out),
                        label=f"[{order}] {btype}",
                    )
                )
                written += 1
        except Exception:  # noqa: BLE001 — skip one bad block
            continue
    return arts


def dump_page(
    page_dir: Path,
    *,
    original=None,
    preprocessed=None,
    blocks=None,
    last_meta=None,
) -> dict[str, list[Artifact]]:
    """Write all artifacts for one page; return {step_name: [Artifact, ...]}.

    Steps populated:
      ingest         -> original.png
      preprocess     -> preprocessed.png
      extract        -> structure_raw.json
      reading_order  -> layout_overlay.png + crops/<order>_<type>.png
    """
    page_dir = Path(page_dir)
    blocks = blocks or []
    last_meta = last_meta or {}
    by_step: dict[str, list[Artifact]] = {}

    # --- ingest: original image ---
    if original is not None:
        out = page_dir / "original.png"
        if _imwrite_unicode(out, original):
            by_step.setdefault("ingest", []).append(
                Artifact(kind="original_image", path=str(out), label="ingested image")
            )

    # --- preprocess: preprocessed image (bbox coord space) ---
    if preprocessed is not None:
        out = page_dir / "preprocessed.png"
        if _imwrite_unicode(out, preprocessed):
            by_step.setdefault("preprocess", []).append(
                Artifact(
                    kind="preprocessed_image",
                    path=str(out),
                    label="after preprocess",
                )
            )

    # --- extract: raw structure JSON ---
    out = page_dir / "structure_raw.json"
    try:
        out.write_text(
            json.dumps(last_meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        by_step.setdefault("extract", []).append(
            Artifact(kind="structure_raw", path=str(out), label="engine last_meta")
        )
    except Exception:  # noqa: BLE001 — never fatal
        pass

    # --- reading_order: layout overlay + crops ---
    ro_arts: list[Artifact] = []
    if preprocessed is not None:
        try:
            overlay = render_layout_overlay(preprocessed, blocks)
            out = page_dir / "layout_overlay.png"
            if _imwrite_unicode(out, overlay):
                ro_arts.append(
                    Artifact(
                        kind="layout_overlay",
                        path=str(out),
                        label="bbox + reading order",
                    )
                )
        except Exception:  # noqa: BLE001
            pass
        ro_arts.extend(_dump_crops(page_dir, preprocessed, blocks))
    if ro_arts:
        by_step.setdefault("reading_order", []).extend(ro_arts)

    return by_step
