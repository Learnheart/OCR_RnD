# Kế hoạch Triển khai — Hybrid IDP Pipeline

> **Loại tài liệu**: Implementation Plan (đi kèm `architecture.md`)
> **Trạng thái**: draft v0.2 (đồng bộ engine Tier B = Qwen3-VL @ LM Studio; AGENT.md là source of truth) — chốt techstack + slice đầu tiên
> **Ngày**: 2026-06-08
> **Tài liệu nền**: `architecture.md` (TDD), `../data_requirements.md` (BA), `../eval/README.md` (harness eval)

---

## 0. Quyết định đã chốt (từ review + Q&A)

| Quyết định | Lựa chọn | Hệ quả |
|---|---|---|
| **Mục tiêu slice đầu** | Document-parsing **tổng quát** (hành chính nội bộ, báo cáo, CCCD…), đo trên **OmniDocBench v1.5** | Slice đầu = lõi **Tier 0 + Tier B** (doc → Markdown/structured), KHÔNG phải KYC banking |
| **GPU thực tế** | **RTX 5060 Ti 16GB** (Blackwell sm_120, driver 581.29/CUDA13) | VRAM dư cho Qwen3-VL-8B (~7GB) + CV. KHÁC giả định 3090/4090: kiến trúc Blackwell mới hơn → nếu sau này dùng vLLM phải build CUDA 12.8+ |
| **Engine Tier B (slice đầu)** | **Qwen3-VL-8B qua LM Studio** (OpenAI-compatible API :1234) | Bỏ Docker/vLLM cho khởi đầu. LM Studio=llama.cpp/GGUF KHÔNG chạy được PaddleOCR-VL (NaViT+ERNIE) → đổi engine. PaddleOCR-VL/vLLM giữ làm target accuracy sau |
| **Build vs Buy (Tier A VN)** | Tự host open-weight (PaddleOCR + VietOCR) | Không phụ thuộc vendor; on-prem ngay; chi phí = công fine-tune (giai đoạn sau) |
| **Runtime** | **Python 3.13** + FastAPI + Pydantic v2 (qua `uv`) | Độc lập repo `IDP/`. Slice đầu chỉ cần HTTP client gọi LM Studio → không phụ thuộc wheel paddle/vLLM. Máy mặc định Py3.12 → `uv python install 3.13`. Eval scorer giữ env `omnidocbench` py3.10 riêng |

> **Điều chỉnh quan trọng so với roadmap architecture mục 8**: roadmap gốc bắt đầu Phase 1 = KYC banking. Theo mục tiêu thực tế, ta **đảo thứ tự**: build lõi *general document parsing* trước (có vòng đo OmniDocBench ngay), rồi mới chồng KYC/Validation banking lên. Lý do: harness eval đã sẵn sàng → có baseline số đo trong vài ngày thay vì vài tuần.

---

## 1. Techstack AI — chốt cho Phase 1 (general parsing)

Đã verify tồn tại & phù hợp GPU tầm trung (xem `architecture.md` mục 9.3 — rủi ro tên model ảo, nay đã giải tỏa).

### 1.1. Engine trích xuất

| Vai trò | Công nghệ chốt | Lý do / Ràng buộc |
|---|---|---|
| **Tier 0 — Direct parse (PDF số)** | `PyMuPDF` (text+bbox) + `pdfplumber` + `Camelot` (bảng) | Free win, provenance miễn phí, zero hallucination. Chạy đầu tiên trên mọi PDF |
| **Tier B — Parsing tổng quát (CHỦ LỰC slice đầu)** | **Qwen3-VL-8B qua LM Studio** | VLM tổng quát, gọi OpenAI-compatible API (ảnh base64). 0 hạ tầng (LM Studio chạy sẵn), ~7GB VRAM. Đánh đổi: điểm OmniDocBench thấp hơn PaddleOCR-VL, KHÔNG có quad/bbox grounding native |
| **Tier B — target accuracy (về sau)** | **PaddleOCR-VL 1.5 (0.9B)** qua **vLLM** | SOTA 94.5% OmniDocBench v1.5; 3–4GB VRAM; trả quad 4 điểm → grounding native. Cần vLLM (Docker/native, build CUDA 12.8+ cho Blackwell). Cắm cùng `ParseEngine` |
| **Tier B — baseline đối chứng (no-VLM)** | **PP-StructureV3** (PaddleOCR pipeline) | Pipeline CV thuần (det+rec+layout+table), deterministic, để so sánh accuracy/latency vs VLM |
| **Tier B — baseline đối chứng #2** | **MinerU 2** (tùy chọn) | Tham chiếu leaderboard; output Markdown+JSON; chỉ để benchmark, không vào critical path |
| Table structure (cross-check) | **Table-Transformer (TATR)** / PP-Structure SLANet | Đo TEDS tách biệt |
| Reading order | **Surya order** (hoặc order native của PaddleOCR-VL) | Giữ thứ tự đọc đa cột |

> **Quyết định engine mặc định slice đầu (chốt 2026-06-08)**: **Qwen3-VL-8B qua LM Studio** làm primary (rẻ nhất về hạ tầng, có số end-to-end ngay). **PaddleOCR-VL 1.5 qua vLLM** là target accuracy về sau; **PP-StructureV3** là đối chứng no-VLM. Cả ba cắm cùng một `ParseEngine` interface (mục 3) → swap bằng config, đo trên cùng OmniDocBench. Lý do bỏ PaddleOCR-VL ở khởi đầu: LM Studio = llama.cpp/GGUF, không chạy được kiến trúc NaViT+ERNIE của PaddleOCR-VL (chỉ vLLM mới chạy).

### 1.2. Thành phần dùng lại / giai đoạn sau (chưa code ở slice đầu)

| Lớp | Công nghệ | Phase |
|---|---|---|
| Tier A — VN KIE | PP-OCRv5 det/rec + **VietOCR** + LayoutLMv3 | Phase 2 (CCCD/GTGT) |
| Tier C — handwriting/relation | TrOCR fine-tune VN · Qwen3-VL (quantize) | Phase 3 |
| Detectors | pyzbar · YOLO (seal/signature) · PassportEye (MRZ) | Phase 2 |
| Validation engine | Python rule engine + checksum + reconcile | Phase 2 (banking) — *interface dựng từ slice đầu* |
| Calibration | scikit-learn (isotonic/Platt) + temperature scaling | Phase 2 (cần nhãn HITL) |
| PII | Presidio + PhoBERT-NER + regex VN | Phase 2 |

### 1.3. Hạ tầng

| Lớp | Slice đầu (dev) | Production (sau) |
|---|---|---|
| Model serving VLM | **LM Studio** (Qwen3-VL-8B, OpenAI-compatible API :1234) — 0 hạ tầng, chạy sẵn trên Windows | vLLM/SGLang cluster (khi chuyển sang PaddleOCR-VL) |
| CV/ONNX | Paddle native / ONNXRuntime | Triton |
| API | FastAPI (uvicorn local) | FastAPI + workers |
| Orchestration | Gọi hàm trực tiếp / CLI batch | Temporal/Airflow + Kafka |
| Storage | Filesystem local | MinIO + PostgreSQL |
| Eval | **Harness OmniDocBench sẵn có** (`../eval/`) | + dashboard nội bộ |
| Package mgmt | `uv` (env riêng cho pipeline) | — |

> **Lưu ý môi trường**: harness eval dùng conda env `omnidocbench` (Py 3.10). Pipeline dùng **env riêng** (uv/venv) để tránh xung đột dependency với bộ chấm điểm. Hai env nói chuyện qua **file Markdown** thả vào `../eval/predictions/end2end/`.

---

## 2. Cấu trúc codebase `hybrid/`

```
hybrid/
├── architecture.md                  # TDD (đã có)
├── implementation-plan.md           # tài liệu này
├── pyproject.toml                   # deps + tool config (uv)
├── README.md                        # quickstart
├── config/
│   ├── default.yaml                 # engine mặc định, ngưỡng, paths
│   └── engines.yaml                 # cấu hình từng engine (model path, vLLM args)
├── src/idp/
│   ├── schemas.py                   # ★ CONTRACT: Pydantic models (Block, Page, DocResult, Envelope)
│   ├── pipeline.py                  # orchestrator: ingest→classify→route→extract→serialize
│   ├── ingest/
│   │   ├── loader.py                # PDF/image/HEIC → chuẩn hóa, tách trang (PyMuPDF/pillow-heif)
│   │   └── preprocess.py            # deskew/orient/quality-score (light cho VLM, heavy cho CV)
│   ├── classify/
│   │   └── router.py                # ★ Routing: digital-born? difficulty? → tier (spec mục 4)
│   ├── extract/
│   │   ├── base.py                  # ★ ParseEngine ABC: parse(image|pdf) -> list[Block]
│   │   ├── tier0_direct.py          # PyMuPDF/pdfplumber/Camelot
│   │   ├── tier_b_lmstudio_vlm.py   # Qwen3-VL-8B qua LM Studio API (PRIMARY slice đầu)
│   │   ├── tier_b_paddleocrvl.py    # PaddleOCR-VL 1.5 qua vLLM (target accuracy, về sau)
│   │   └── tier_b_ppstructure.py    # PP-StructureV3 (đối chứng no-VLM)
│   ├── serialize/
│   │   └── markdown.py              # Block[] → Markdown (reading order) cho OmniDocBench
│   ├── validate/
│   │   └── gate.py                  # stub slice đầu (grounding round-trip dựng sau)
│   └── api/
│       └── app.py                   # FastAPI: POST /parse
├── scripts/
│   ├── run_omnidocbench.py          # batch ảnh OmniDocBench → predictions → gọi eval
│   └── parse_one.py                 # CLI 1 file để debug
└── tests/
    ├── test_schemas.py
    ├── test_router.py
    └── test_tier0.py
```

**Nguyên tắc**: `schemas.py` và `extract/base.py` là **contract đóng băng trước** — mọi tier/engine khác cắm vào hai interface này, cho phép phát triển song song và A/B model trên cùng eval.

---

## 3. Contract giữa các stage (việc làm ĐẦU TIÊN)

Architecture mô tả "cái gì" rất tốt nhưng thiếu schema I/O *giữa* các stage (review điểm #1). Đây là deliverable code đầu tiên:

```python
# schemas.py — phác thảo (Pydantic v2)
class BBox(BaseModel):              # tọa độ chuẩn hóa [x0,y0,x1,y1] hoặc quad 4 điểm
    quad: list[float]              # 8 số (PaddleOCR-VL) hoặc 4 số (axis-aligned)
    page: int

class Block(BaseModel):            # đơn vị nội dung có provenance
    type: Literal["text","title","table","formula","figure","header","footer","list"]
    text: str | None
    html: str | None               # cho table (TEDS)
    latex: str | None              # cho formula (CDM)
    bbox: BBox
    confidence: float
    reading_order: int

class PageResult(BaseModel):
    page: int
    blocks: list[Block]
    image_uri: str                 # ảnh gốc (provenance + VLM dùng lại)

class DocumentResult(BaseModel):   # tiền thân của Provenance Envelope (architecture mục 5)
    document_id: str
    doc_type: str | None
    doc_type_confidence: float | None
    tier: Literal["0","A","B","C"]
    engines_used: list[str]
    pages: list[PageResult]
    warnings: list[str] = []
```

→ `DocumentResult` mở rộng dần thành **Provenance Envelope** đầy đủ (thêm `fields[]`, `validation`, `pii`, `detections`) khi sang Phase 2 banking. Slice đầu chỉ cần tới mức `blocks` để serialize Markdown cho OmniDocBench.

---

## 4. Spec Routing layer (lấp khoảng trống architecture mục 2.1)

Slice đầu chỉ cần luật tối thiểu, mở rộng sau:

```
def route(doc) -> tier:
    if is_digital_born(doc):        # PDF có text-layer thật (PyMuPDF: page.get_text() đủ ký tự
        return TIER_0               #   & font embedded, không phải scan-in-PDF)
    else:
        return TIER_B               # mặc định slice đầu: mọi ảnh/scan → Qwen3-VL @ LM Studio
    # Phase 2+ : thêm difficulty score → Tier A (template) / Tier C (handwriting/relation)
```

`is_digital_born`: `len(page.get_text().strip()) > N` **và** tỷ lệ ký tự có font embedded cao → digital. Ngược lại (PDF chỉ chứa ảnh scan) → Tier B. Đây là "free win" lớn nhất, làm trước.

---

## 5. Lộ trình Milestone (slice đầu → mở rộng)

Mỗi milestone có **Definition of Done đo được** (đa số bằng OmniDocBench).

### M0 — Scaffold + Contract  *(nền móng)*
- `pyproject.toml`, cấu trúc thư mục, `schemas.py`, `extract/base.py`.
- **DoD**: `pytest tests/test_schemas.py` xanh; import được package.

### M1 — Tier 0 Direct parse + Markdown serializer  *(free win)*
- `tier0_direct.py` (PyMuPDF text+bbox), `serialize/markdown.py`.
- **DoD**: parse 1 PDF số → Markdown đúng reading order, có bbox mọi block.

### M2 — Tier B (Qwen3-VL @ LM Studio) + Eval baseline  *(★ mốc quan trọng nhất)*
- `tier_b_lmstudio_vlm.py` (HTTP client → `http://localhost:1234/v1/chat/completions`, ảnh base64 `image_url`), `scripts/run_omnidocbench.py`.
- **Chuẩn bị trước**: tăng context LM Studio **4096 → ~32k** (full-page doc→markdown dễ tràn 4096); `uv python install 3.13`.
- Chạy OmniDocBench (1–2 ảnh trước theo Rule 4, rồi full) → thả Markdown vào `../eval/predictions/end2end/` → `run_eval.ps1`.
- **DoD**: có **số đo baseline thật** (overall, text edit-dist, TEDS, reading order) ghi vào `../eval/results/`. Đây là baseline "rẻ" của Qwen3-VL — KHÔNG kỳ vọng ~94% của PaddleOCR-VL; log latency/trang ngay từ M2.

### M3 — Router + engine đối chứng + Ingest  *(robustness)*
- `router.py`, `preprocess.py` (deskew/orient/quality), engine đối chứng thứ 2 (PP-StructureV3 hoặc PaddleOCR-VL/vLLM khi dựng được).
- **DoD**: tự động chọn Tier 0/B; có **bảng số đối chứng** so sánh Qwen3-VL vs engine thứ 2 trên cùng OmniDocBench.

### M4 — FastAPI + đóng gói  *(usable service)*
- `api/app.py` `POST /parse` (upload → DocumentResult JSON + Markdown).
- **DoD**: `curl` 1 file nhận envelope; README quickstart chạy được.

### M5+ — Mở rộng theo roadmap banking (Phase 2/3 architecture)
- Tier A VN (CCCD/GTGT) + Validation gate + grounding round-trip + detectors + calibration + PII.
- **DoD** theo `data_requirements.md`: ID ≥99.5%, amount ≥99%, table F1 ≥95%…

---

## 6. Mapping Plan ↔ Architecture stages

| Architecture stage | Slice đầu (M0–M4) | Mở rộng (M5+) |
|---|---|---|
| 1. Ingest & Pre-process | Loader + light preprocess (M3) | Dewarp/super-res/binarize theo tier |
| 2. Classification | Router tối thiểu (digital vs scan) | LayoutLMv3/Donut doc_type |
| 3. Splitting | (defer) | Page-stream seg + cross-page table merge |
| 4. Extraction | **Tier 0 + Tier B** (M1, M2) | Tier A/C + detectors |
| 5. Validation & Grounding | stub (M0) | Checksum/reconcile/round-trip/calibration |
| 6. PII | — | Presidio + PhoBERT |
| 7. HITL | — | Label Studio + active learning |

---

## 7. Rủi ro & việc cần kiểm (cập nhật sau verify)

| Rủi ro (architecture mục 9) | Trạng thái | Hành động |
|---|---|---|
| Tên model ảo / version | ✅ Đã verify: PaddleOCR-VL 1.5, PP-StructureV3, MinerU2 đều có thật trên leaderboard hiện tại | Pin version trong `engines.yaml` khi cài |
| VRAM | ✅ Qwen3-VL-8B ~7GB / RTX 5060 Ti 16GB — dư | Tắt LM Studio model khác khi chạy; PaddleOCR-VL (3–4GB) chỉ cần khi chuyển vLLM |
| LM Studio context 4096 quá nhỏ | ⚠️ Mới phát hiện | Reload Qwen3-VL với context ~32k TRƯỚC M2 — full-page markdown tràn 4096 token |
| Blackwell sm_120 với vLLM | ⚠️ Chỉ liên quan khi chuyển PaddleOCR-VL | Image/build vLLM phải CUDA 12.8+; slice đầu (LM Studio) không vướng |
| Grounding/bbox cho Tier B | ⚠️ Qwen3-VL KHÔNG có quad/bbox native | Slice đầu provenance Tier B yếu; đo grounding tách biệt khi cắm PaddleOCR-VL (engine grounded) |
| Calibration cần nhãn holdout | ⚠️ Chicken-egg | Để Phase 2 (sau khi HITL sinh nhãn); slice đầu không gate theo confidence |
| Latency/throughput Tier B | ⚠️ Chưa đo | Log latency/trang ngay từ M2 |

---

## 8. Next actions (đề xuất bắt đầu ngay)

1. **M0**: tạo `pyproject.toml` + cấu trúc thư mục + `schemas.py` + `extract/base.py` + test contract.
2. **M1**: Tier 0 (PyMuPDF) + Markdown serializer (không cần GPU, làm được ngay).
3. **M2**: tăng context LM Studio (4096→~32k) + `uv python install 3.13`, viết `tier_b_lmstudio_vlm.py` + `run_omnidocbench.py`, lấy baseline số đo.

> Khuyến nghị làm M0→M1 trước (không phụ thuộc GPU/model). LM Studio đã chạy sẵn nên M2 chỉ cần chỉnh context + viết HTTP client — không có bước dựng Docker/vLLM.
