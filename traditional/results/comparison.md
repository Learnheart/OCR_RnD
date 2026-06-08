# Comparison — traditional vs hybrid (OmniDocBench sample_100)

| metric | dir | traditional (PP-OCRv4) | hybrid (Qwen3-VL) | winner |
|---|---|---|---|---|
| text_block Edit_dist | ↓ | **0.342** | 0.467 | traditional (PP-OCRv4) |
| display_formula Edit_dist | ↓ | 0.839 | **0.538** | hybrid (Qwen3-VL) |
| table TEDS | ↑ | 0.170 | **0.188** | hybrid (Qwen3-VL) |
| table TEDS_structure_only | ↑ | **0.420** | 0.364 | traditional (PP-OCRv4) |
| table Edit_dist | ↓ | **0.683** | 0.792 | traditional (PP-OCRv4) |
| reading_order Edit_dist | ↓ | **0.367** | 0.410 | traditional (PP-OCRv4) |
| latency (s/img) | ↓ | **5.060** | 28.890 | traditional (PP-OCRv4) |
