"""Tier B — Grounded VLM qua LM Studio (Qwen3-VL-8B).

Gọi OpenAI-compatible API `http://localhost:1234/v1/chat/completions`, ảnh base64
`image_url`. Trả nguyên 1 block Markdown đầy đủ trang (Qwen3-VL không có bbox/quad
native → provenance Tier B yếu, đo grounding tách biệt khi cắm engine grounded).

Prompt tối ưu cho OmniDocBench: bảng HTML (TEDS), công thức LaTeX, giữ nguyên ngôn
ngữ gốc, đúng reading order, không thêm lời bình.
"""

from __future__ import annotations

import base64
import time

import httpx

from idp.extract.base import ParseEngine
from idp.ingest.loader import LoadedPage
from idp.schemas import Block

DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "qwen/qwen3-vl-8b"

PROMPT = (
    "You are a precise document-parsing engine. Convert the document page in the "
    "image into clean Markdown that reproduces the page faithfully.\n"
    "Rules:\n"
    "- Output ONLY the page content as Markdown. No explanations, no commentary, "
    "no code fences around the whole output.\n"
    "- Preserve the original language exactly (Chinese / English / Vietnamese). Do "
    "NOT translate or summarize.\n"
    "- Follow the natural reading order (handle multi-column layouts left-to-right, "
    "top-to-bottom).\n"
    "- Headings/titles → Markdown headings (#, ##). Lists → '-' or numbered.\n"
    "- Tables → raw HTML <table><tr><td>…</td></tr></table> (preserve row/column "
    "structure and merged cells with rowspan/colspan). Do NOT use Markdown pipe tables.\n"
    "- Mathematical formulas → LaTeX: inline as $…$, display equations as $$…$$.\n"
    "- Transcribe all visible text including headers and footers. Ignore decorative "
    "background and watermarks.\n"
)


class LMStudioVLMEngine(ParseEngine):
    name = "qwen3-vl-8b@lmstudio"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout_s: float = 300.0,
        max_retries: int = 2,
        api_key: str = "lm-studio",
        frequency_penalty: float = 0.3,
    ) -> None:
        # max_tokens=4096: 1 trang hiếm khi cần hơn; chặn runaway (VLM lặp vô tận
        # trên trang toán/dày → từng sinh 24k ký tự/135s). frequency_penalty phá vòng lặp.
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.api_key = api_key
        self.frequency_penalty = frequency_penalty
        self.last_latency_s: float = 0.0
        self._client = httpx.Client(timeout=timeout_s)

    def close(self) -> None:
        self._client.close()

    @staticmethod
    def _strip_fences(text: str) -> str:
        t = text.strip()
        if t.startswith("```"):
            # bỏ dòng mở ```lang và dòng đóng ```
            lines = t.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            t = "\n".join(lines).strip()
        return t

    def _call(self, image_b64: str) -> str:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "frequency_penalty": self.frequency_penalty,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}"
                            },
                        },
                    ],
                }
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/chat/completions"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                r = self._client.post(url, json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:  # noqa: BLE001
                last_exc = e
                if attempt < self.max_retries:
                    time.sleep(2.0 * (attempt + 1))
        raise RuntimeError(f"LM Studio call failed after retries: {last_exc}")

    def parse(self, page: LoadedPage) -> list[Block]:
        image_b64 = base64.b64encode(page.image_bytes).decode("ascii")
        t0 = time.perf_counter()
        raw = self._call(image_b64)
        self.last_latency_s = time.perf_counter() - t0
        markdown = self._strip_fences(raw)
        # Qwen3-VL không có bbox → 1 block markdown đầy đủ trang, không grounding
        return [Block(type="text", text=markdown, bbox=None, reading_order=0)]
