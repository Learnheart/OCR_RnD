"""VLM crop handlers — Qwen3-VL @ LM Studio trên CROP vùng (S3).

Khác V1 (feed cả trang): mỗi handler chỉ gửi ROI của 1 vùng + prompt theo loại →
scope hẹp, ít hallucination/token (D6). Dùng cho formula/chart/seal.

Degrade gracefully: LM Studio tắt / lỗi → Block rỗng + `last_warning`, KHÔNG ném
(trang vẫn dựng được trace bundle). Client httpx khởi tạo lười, dùng chung run.
"""

from __future__ import annotations

import base64
import time

import cv2
import numpy as np

from idp.extract.handlers.base import RegionHandler, crop_region
from idp.preprocess.base import PreprocessedPage
from idp.schemas import BBox, Block, BlockType, Region

DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "qwen/qwen3-vl-8b"

PROMPT_FORMULA = (
    "The image is a cropped mathematical formula from a document. Output ONLY the "
    "LaTeX for it, no delimiters, no explanation. If it is not a formula, output the "
    "raw text verbatim."
)
PROMPT_CHART = (
    "The image is a cropped chart/figure from a document. Describe it concisely and, "
    "if it encodes tabular data, output an HTML <table> of the data. Output only the "
    "description/table, no preamble."
)
PROMPT_SEAL = (
    "The image is a cropped stamp/seal from a document. Transcribe any text on the "
    "seal verbatim (keep original language). Output only the text; empty if none."
)


def _png_b64(roi: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", roi)
    if not ok:
        raise ValueError("cv2.imencode failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


class VLMCropHandler(RegionHandler):
    """Base cho handler gọi VLM trên crop. Subclass đặt group/prompt/field/btype."""

    prompt: str = ""
    out_field: str = "text"  # "text" | "latex" | "html"
    btype: BlockType = "text"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
        timeout_s: float = 120.0,
        temperature: float = 0.0,
    ) -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.temperature = temperature
        self._client = None

    def _http(self):
        if self._client is None:
            import httpx

            self._client = httpx.Client(timeout=self.timeout_s)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _call(self, image_b64: str) -> str:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                }
            ],
        }
        r = self._http().post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": "Bearer lm-studio"},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    def handle(self, region: Region, page: PreprocessedPage) -> Block:
        self.last_warning = None
        self.last_engine = f"{self.model}@lmstudio"
        roi = crop_region(page.image, region, pad=8)
        content = ""
        t0 = time.perf_counter()
        if roi is not None and roi.size:
            try:
                content = self._call(_png_b64(roi))
            except Exception as e:  # noqa: BLE001 — LM Studio tắt/lỗi → degrade
                self.last_warning = f"VLM unavailable: {type(e).__name__}: {e}"
        else:
            self.last_warning = "empty crop"
        self.last_latency_s = time.perf_counter() - t0
        kwargs = {self.out_field: content or None}
        return Block(
            type=self.btype,
            bbox=BBox(quad=list(region.bbox.as_xyxy()), page=page.index),
            confidence=0.0 if self.last_warning else region.score,
            reading_order=region.region_id,
            **kwargs,
        )


class FormulaHandler(VLMCropHandler):
    group = "formula"
    name = "qwen3vl-formula@lmstudio"
    prompt = PROMPT_FORMULA
    out_field = "latex"
    btype = "formula"


class ChartHandler(VLMCropHandler):
    group = "chart"
    name = "qwen3vl-chart@lmstudio"
    prompt = PROMPT_CHART
    out_field = "text"
    btype = "figure"


class SealHandler(VLMCropHandler):
    group = "seal"
    name = "qwen3vl-seal@lmstudio"
    prompt = PROMPT_SEAL
    out_field = "text"
    btype = "figure"
