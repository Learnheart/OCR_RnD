# AGENT — `hybrid` (Hybrid Tiered IDP Pipeline)

> **Source of truth** cho solution agent này. Chi tiết method/techstack/cách chạy sống ở đây.
> Index ngắn ở `../CLAUDE.md`; thiết kế đầy đủ ở `architecture.md`; lộ trình ở `implementation-plan.md`.
> Mọi thay đổi hành vi/engine/cách chạy → cập nhật file này TRƯỚC.

---

## 1. Một dòng

Pipeline IDP **hybrid, phân tầng (tiered), grounded-first**: chạy engine rẻ & deterministic trước, chỉ "leo thang" lên VLM cho phần khó. Ưu tiên thiết kế: **độ chính xác → truy vết (provenance) → chi phí**.

## 2. Mục tiêu slice đầu (đang làm)

- **Document-parsing tổng quát** (hành chính, báo cáo, CCCD…), KHÔNG phải KYC banking.
- Đo trên **OmniDocBench v1.5** qua harness chung ở `../eval/` → có baseline số đo trong vài ngày.
- Phạm vi code slice đầu = lõi **Tier 0 + Tier B** (doc → Markdown/structured). Validation/KIE/PII banking để Phase 2+.
- **Trạng thái hiện tại** (2026-06-08): **M0–M2 code xong** (`src/idp/`, 14/14 pytest xanh) + **eval harness có timestamp** (`scripts/eval_run.py`, loopback nhiều solution). **Có baseline đầu tiên** trên 100 ảnh sample (xem dưới). Code/lệnh: mục 7–8.

### Baseline đầu tiên — `hybrid-qwen3vl` (2026-06-08, 100 ảnh stratified)

> Run: `results/runs/2026-06-08_0357_hybrid-qwen3vl/`. Engine Qwen3-VL-8B @ LM Studio, max_tokens=4096. Sample 100 ảnh chia đều 10 nguồn (`eval/samples/sample_100.txt`). Đo trên GT lọc xuống 100 ảnh đó.

| Metric | Value | Ghi chú |
|---|---|---|
| text_block Edit_dist | **0.467** | thấp=tốt (SOTA ~0.05–0.10) |
| display_formula Edit_dist | **0.538** | thấp=tốt |
| table TEDS | **0.188** | cao=tốt (SOTA ~0.85) |
| table TEDS_structure_only | 0.364 | cao=tốt |
| table Edit_dist | 0.792 | thấp=tốt |
| reading_order Edit_dist | 0.411 | thấp=tốt |
| Latency | **28.7s/ảnh** (avg) | 0 lỗi/100; 48 phút |

Theo nguồn (text_block Edit_dist, thấp=tốt): PPT2PDF **0.13** (tốt nhất) · book 0.30 · academic 0.36 · colorful_textbook 0.43 · note/magazine ~0.54 · exam 0.58 · research_report 0.78 · newspaper **0.91** · historical **0.98** (kém nhất — trang dày/đa cột/cổ).

**Đọc số**: Qwen3-VL-8B (general VLM qua GGUF) kém xa PaddleOCR-VL SOTA — ĐÚNG như plan dự báo. Baseline "rẻ" để so khi cắm PaddleOCR-VL/vLLM (cùng `ParseEngine`). Điểm yếu rõ: bảng (TEDS 0.19), trang đa cột/dày (newspaper, historical, research_report).

  - **Gotcha đã xử lý**: (1) **runaway generation** trang toán/dày (24k ký tự/135s) → cap `max_tokens=4096` + `frequency_penalty=0.3`. (2) **GT-filtering**: OmniDocBench chấm trên TOÀN BỘ 1651 GT, ảnh thiếu prediction bị tính edit=1.0 → eval subset PHẢI lọc GT xuống đúng N ảnh (eval_run.py tự làm `gt_subset.json`).

## 3. Phương pháp — mô hình phân tầng

| Tier | Route vào khi | Engine slice đầu |
|---|---|---|
| **Tier 0 — Direct parse** | PDF digital-born (có text-layer thật) | `PyMuPDF` + `pdfplumber` + `Camelot` (text+bbox miễn phí, zero hallucination) |
| **Tier B — Grounded VLM** | Ảnh/scan, bảng phức tạp, layout rối (mặc định slice đầu) | **Qwen3-VL-8B qua LM Studio** — xem mục 4 |
| Tier A / Tier C / Detectors / Validation gate | template VN, viết tay, quan hệ, QR/dấu/chữ ký | **Phase 2/3** — chưa code (xem `architecture.md`) |

Routing slice đầu (tối thiểu): `is_digital_born(doc)` → Tier 0; ngược lại → Tier B. (`is_digital_born` = `PyMuPDF page.get_text()` đủ ký tự + font embedded cao.)

## 4. Engine Tier B — quyết định hiện hành

> Đã đồng bộ vào `architecture.md` (callout cuối mục 4) + `implementation-plan.md` (v0.2) ngày 2026-06-08. AGENT.md vẫn là source of truth nếu sau này có lệch.

- **Quyết định đang dùng cho slice đầu (chốt 2026-06-08, từ Q&A với user)**: Tier B = **Qwen3-VL-8B** gọi qua **LM Studio** (OpenAI-compatible API `http://localhost:1234/v1/chat/completions`, ảnh truyền base64 `image_url`).
  - Đã verify OCR tiếng Việt qua API OK.
  - Lý do bỏ PaddleOCR-VL ở khởi đầu: LM Studio = llama.cpp/GGUF, **KHÔNG chạy được** kiến trúc NaViT+ERNIE của PaddleOCR-VL (chỉ vLLM mới chạy). Đổi lại: **0 hạ tầng Docker/WSL/vLLM**, có số end-to-end ngay.
- **PaddleOCR-VL 1.5 qua vLLM** (SOTA 94.5% OmniDocBench) giờ là **mục tiêu accuracy về sau**, không phải engine khởi đầu. `architecture.md` + `implementation-plan.md` đã được cập nhật khớp với điều này.
- **Đánh đổi đã chấp nhận**: Qwen3-VL điểm OmniDocBench thấp hơn PaddleOCR-VL SOTA, và **không có bbox/quad grounding native** → grounding/provenance cho Tier B phải xử lý cách khác hoặc defer. PaddleOCR-VL/vLLM giữ lại làm target accuracy, cắm vào **cùng `ParseEngine` interface** để swap bằng config.

## 5. Phần cứng & môi trường thực tế (verify 2026-06-08)

- **GPU**: RTX **5060 Ti 16GB** (Blackwell sm_120, driver 581.29 / CUDA 13) — KHÁC giả định 3090/4090 trong plan. VRAM dư; nếu sau này dùng vLLM phải build CUDA 12.8+.
- RAM 32GB · i5-13400F 10c/16t · ổ C: trống ~454GB. Docker 28.4 + nvidia runtime + WSL2 Ubuntu sẵn sàng.
- **LM Studio** đã chạy sẵn (API :1234), Qwen3-VL-8B đã tải. **Cần làm trước khi code Tier B**: tăng context LM Studio **4096 → ~32k** (full-page doc→markdown tràn 4096).
- **Runtime pipeline**: kế hoạch Python **3.13** + FastAPI + Pydantic v2, package mgmt `uv` (env riêng). Hiện máy mặc định Py 3.12 → cần `uv python install 3.13`.
- **Env eval tách biệt**: bộ chấm điểm OmniDocBench dùng conda env `omnidocbench` (Py 3.10) — KHÔNG trộn với env pipeline. Hai env nói chuyện qua **file Markdown** thả vào `../eval/predictions/end2end/`.

## 6. Techstack (slice đầu)

| Lớp | Công nghệ |
|---|---|
| Tier 0 | PyMuPDF · pdfplumber · Camelot |
| Tier B (primary) | Qwen3-VL-8B @ LM Studio (OpenAI-compatible) |
| Tier B (target sau) | PaddleOCR-VL 1.5 @ vLLM · đối chứng PP-StructureV3 / MinerU2 |
| Contract | Pydantic v2 (`schemas.py`) |
| API | FastAPI (uvicorn local) |
| Serialize | Block[] → Markdown (reading order) cho OmniDocBench |
| Eval | harness chung `../eval/` (OmniDocBench v1.5) |

## 7. Cấu trúc code dự kiến (xem `implementation-plan.md` mục 2)

`src/idp/` — `schemas.py` (★ contract đóng băng trước) · `pipeline.py` · `ingest/` · `classify/router.py` · `extract/{base.py(★ ParseEngine ABC), tier0_direct.py, tier_b_lmstudio_vlm.py}` · `serialize/markdown.py` · `validate/gate.py` (stub) · `api/app.py`. `scripts/run_omnidocbench.py` (batch → predictions → eval) · `scripts/parse_one.py`.

> **Nguyên tắc**: `schemas.py` + `extract/base.py` là contract **đóng băng trước** mọi tier khác — cho phép A/B engine trên cùng eval.

## 8. Cách chạy

1. **Setup**: `uv sync --extra dev` trong `hybrid/` (tự tạo venv Py3.13). Bật LM Studio:
   `& "$env:USERPROFILE\.lmstudio\bin\lms.exe" server start` rồi
   `... load qwen/qwen3-vl-8b --context-length 32768 --gpu max -y`.
2. **Test**: `uv run pytest` (14 test, không cần GPU).
3. **Debug 1 file**: `uv run python scripts/parse_one.py <path>` → DocumentResult meta + trace latency/tier + Markdown.
4. **Eval có timestamp (KHUYẾN NGHỊ — loopback nhiều solution)**: `uv run python scripts/eval_run.py --n 100 --solution hybrid-qwen3vl` → tự sinh prediction trên sample 100 + lọc GT + chấm điểm + archive vào `results/runs/<ngày_giờ>_<solution>/` (predictions, gt_subset.json, eval_config.yaml, result/, meta.json, latency.json, summary.md). Tái tóm tắt run cũ: `uv run python scripts/resummarize.py results/runs/<run_id>`. Sample cố định chia đều theo nguồn: `scripts/make_sample.py --n 100`.
5. **Eval full thủ công** (Rule 4 — nhỏ trước): `uv run python scripts/run_omnidocbench.py --limit 2` → `uv run python scripts/run_omnidocbench.py` (vào `../eval/predictions/end2end/`). Chấm: `cd ../eval; .\run_eval.ps1` (LƯU Ý: chấm trên toàn bộ 1651 GT — cần đủ prediction, nếu không điểm sai). Coverage: `python check_setup.py --preds end2end`.

## 9. Milestones & Definition of Done (xem `implementation-plan.md` mục 5)

- **M0** Scaffold + Contract — `pytest tests/test_schemas.py` xanh.
- **M1** Tier 0 + Markdown serializer (không cần GPU) — 1 PDF số → Markdown đúng reading order + bbox.
- **M2** ★ Tier B (LM Studio) + eval baseline — **số đo OmniDocBench thật** ghi vào `../eval/results/`.
- **M3** Router + ingest + engine đối chứng. **M4** FastAPI `POST /parse`. **M5+** banking (Tier A/C, Validation gate, grounding, PII, calibration).

**Next action ngay**: M0→M1 (không phụ thuộc GPU), song song chuẩn bị LM Studio cho M2. Trước M2 phải: (1) context LM Studio 4096→32k, (2) `uv python install 3.13`, (3) đóng băng `schemas.py` + `extract/base.py`.

## 10. Rủi ro đang mở

- **Grounding ≠ text accuracy**, và Qwen3-VL không có bbox native → provenance Tier B slice đầu yếu; đo grounding tách biệt khi có engine grounded.
- **Latency/throughput Tier B** chưa đo — log latency/trang ngay từ M2.
- ~~Doc lệch quyết định engine~~ — đã đồng bộ `architecture.md` + `implementation-plan.md` (2026-06-08).
- Repo `IDP/` (Databricks agent stack) **KHÔNG** phải base build pipeline này.

---

## Tài liệu liên quan
- `architecture.md` — TDD đầy đủ (7 stage, provenance envelope, eval framework, roadmap banking).
- `implementation-plan.md` — techstack chốt, cấu trúc code, milestones M0–M5.
- `../CLAUDE.md` — rule workspace + cách chạy eval.
- `../data_requirements.md` — yêu cầu BA (field/accuracy target banking, dùng ở Phase 2+).
