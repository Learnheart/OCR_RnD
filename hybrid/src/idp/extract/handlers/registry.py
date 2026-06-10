"""Registry mặc định — dựng {group: handler} cho fan-out S3.

Deterministic: text (PP-OCRv4), table (PP-Structure). VLM: formula/chart/seal
(Qwen3-VL @ LM Studio). `enable_vlm=False` → bỏ nhánh VLM (chạy nhanh, chỉ
deterministic); khi LM Studio tắt handler tự degrade nên vẫn an toàn để bật.
"""

from __future__ import annotations

from idp.extract.handlers.base import RegionHandler, build_registry
from idp.extract.handlers.table import TableHandler
from idp.extract.handlers.text import TextHandler
from idp.extract.handlers.vlm import ChartHandler, FormulaHandler, SealHandler
from idp.schemas import RegionGroup


def default_handlers(
    lang: str = "en",
    use_gpu: bool = False,
    enable_vlm: bool = True,
    vlm_base_url: str = "http://localhost:1234/v1",
    vlm_model: str = "qwen/qwen3-vl-8b",
) -> dict[RegionGroup, RegionHandler]:
    handlers: list[RegionHandler] = [
        TextHandler(lang=lang, use_gpu=use_gpu),
        TableHandler(lang=lang, use_gpu=use_gpu),
    ]
    if enable_vlm:
        handlers += [
            FormulaHandler(base_url=vlm_base_url, model=vlm_model),
            ChartHandler(base_url=vlm_base_url, model=vlm_model),
            SealHandler(base_url=vlm_base_url, model=vlm_model),
        ]
    return build_registry(handlers)
