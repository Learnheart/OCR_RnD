# Changelog — hybrid

Tất cả thay đổi đáng kể của solution `hybrid`. Định dạng theo [Keep a Changelog],
versioning theo [SemVer]. Mục mới nhất trên cùng.

[Keep a Changelog]: https://keepachangelog.com/
[SemVer]: https://semver.org/

## [0.1.0] — 2026-06-08

Slice đầu end-to-end (M0→M2): ảnh/PDF → Markdown, đo trên OmniDocBench v1.5.

### Added — Evaluation harness có timestamp (loopback nhiều solution)
- `[hybrid]` `scripts/eval_run.py` — orchestrator 1 lệnh: sinh prediction trên
  sample → chấm điểm → archive vào `results/runs/<YYYY-MM-DD_HHMM>_<solution>/`
  (isolated: gt_subset.json + eval_config.yaml absolute-path + predictions +
  result + meta.json + latency.json + summary in console). Chấm bằng cách
  subprocess gọi conda env `omnidocbench` (PYTHONUTF8=1).
- `[hybrid]` `scripts/make_sample.py` — sample CỐ ĐỊNH 100 ảnh chia đều theo
  `data_source` (largest-remainder, deterministic) → `eval/samples/sample_100.txt`,
  SHARED cho mọi solution để so sánh apples-to-apples.
- `[hybrid]` `src/idp/batch.py` — batch runner dùng chung (resume, latency, log).
- `[hybrid]` `eval_run.py --reuse-dir` (mặc định: run trước cùng solution + shared
  `eval/predictions/end2end`) — tái dùng prediction đã sinh, chỉ sinh phần thiếu
  (tiết kiệm GPU). `scripts/resummarize.py` — tái tóm tắt run cũ không cần chấm lại.
- `[eval]` `eval/samples/sample_100.txt` — manifest 100 ảnh chuẩn (10 nguồn).

### Fixed
- `[hybrid]` **GT-filtering** (critical): OmniDocBench chấm trên TOÀN BỘ 1651 GT —
  ảnh không có prediction bị tính edit_dist=1.0. Eval subset N ảnh giờ lọc GT
  xuống đúng N (gt_subset.json) → text_block Edit_dist từ 0.99 (artifact) về ~0.33 (thật).
- `[hybrid]` **Runaway VLM**: cap `max_tokens` 8192→4096 + `frequency_penalty=0.3`
  → trang xấu nhất 135s→68s, 24k→11k ký tự. Trang thường ~5–15s.
- `[hybrid]` UTF-8 stdout cho mọi script (Windows cp1252 crash với CJK/tiếng Việt).
- `[hybrid]` `run_omnidocbench.py` glob cả `.jpg` (981) + `.png` (670) = 1651 (trước chỉ .png).

### Added — Core M0→M2
- `[hybrid]` **M0 — Contract đóng băng**: `src/idp/schemas.py` (Pydantic v2: `BBox`,
  `Block`, `PageResult`, `DocumentResult`) + `extract/base.py` (`ParseEngine` ABC).
  `Block.bbox` nullable để hỗ trợ engine không grounding (Qwen3-VL). `tests/test_schemas.py`.
- `[hybrid]` **M1 — Tier 0 + serializer**: `extract/tier0_direct.py` (PyMuPDF text+bbox,
  pdfplumber tables→HTML, loại text trong vùng bảng), `serialize/markdown.py`
  (Block[]→Markdown reading order: title→heading, table→HTML, formula→`$$`).
  `ingest/loader.py` (ảnh/PDF→LoadedPage), `classify/router.py` (digital-born→Tier0).
  `tests/test_tier0.py`, `tests/test_router.py`.
- `[hybrid]` **M2 — Tier B VLM + eval**: `extract/tier_b_lmstudio_vlm.py` (Qwen3-VL-8B
  qua LM Studio, OpenAI-compatible, ảnh base64, prompt tối ưu OmniDocBench),
  `pipeline.py` (orchestrator route→extract, trace latency/tier),
  `scripts/parse_one.py` (debug 1 file), `scripts/run_omnidocbench.py`
  (batch 1651 ảnh jpg+png → predictions, resume, log latency/ETA).
- `[hybrid]` Scaffold uv (Python 3.13, Pydantic v2, PyMuPDF, pdfplumber, httpx, FastAPI):
  `pyproject.toml`, `config/{default,engines}.yaml`, `validate/gate.py` (stub),
  `api/app.py` (FastAPI `POST /parse`), `README.md`.
- `[hybrid]` `docs/2026-06-08/end-to-end-pipeline/plan.md` (Rule 1).

### Verified (2026-06-08)
- 14/14 pytest xanh. Tier B chạy thật trên ảnh OmniDocBench: ~7–11s/trang, Markdown sạch.
- LM Studio server :1234, `qwen/qwen3-vl-8b` context 32768, GPU RTX 5060 Ti 16GB.
- Harness demo (`run_eval.ps1 end2end_demo_local`) chấm điểm OK; smoke 2 ảnh được scorer nhận.

### Measured — baseline `hybrid-qwen3vl` (100 ảnh stratified, GT lọc)
- text_block Edit_dist **0.467** · display_formula Edit_dist **0.538** · table TEDS **0.188**
  (struct-only 0.364) · table Edit_dist 0.792 · reading_order Edit_dist 0.411.
- Latency **28.7s/ảnh** (avg, max_tokens=4096), 0 lỗi/100, 48 phút.
- Theo nguồn (text_block, thấp=tốt): PPT2PDF 0.13 · book 0.30 · academic 0.36 ·
  colorful_textbook 0.43 · note/magazine ~0.54 · exam 0.58 · research_report 0.78 ·
  newspaper 0.91 · historical 0.98. Run: `results/runs/2026-06-08_0357_hybrid-qwen3vl/`.

### Notes
- Engine Tier B = Qwen3-VL-8B (KHÔNG bbox/quad native → provenance Tier B yếu, defer
  grounding). PaddleOCR-VL 1.5 @ vLLM giữ làm target accuracy, cắm cùng `ParseEngine`.
- Baseline "rẻ" để A/B khi cắm PaddleOCR-VL/vLLM. Điểm yếu rõ: bảng (TEDS 0.19),
  trang đa cột/dày (newspaper, historical, research_report). Full 1651 ≈ 13h ở tốc độ này.
