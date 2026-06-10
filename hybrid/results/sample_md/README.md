# sample_md — output Markdown V2 trên `eval/sample/`

Markdown kết quả của **Pipeline V2** (modular layout-driven) chạy trên 9 ảnh QA
`../../../eval/sample/` (pha R10, KHÔNG có ground-truth — chỉ QA trực quan).

- Run: `2026-06-10_0921_sample-visual`, env conda `ocr-worker`, VLM Qwen3-VL-8B (LM Studio).
- 0 warning, ~21s/ảnh.
- `pageN.md` ↔ `eval/sample/pageN.jpg`.

> Đây chỉ là phần `.md`. Trace bundle đầy đủ (ảnh từng step + `index.html`) nằm ở
> `hybrid/results/v2_runs/` — **không commit** (chứa ảnh, theo convention `results/`).
> Tái tạo: `python scripts/run_v2.py --images ../eval/sample --run-name sample-visual`.
