# Eval run — 2026-06-08_0357_hybrid-qwen3vl

- **Solution**: hybrid-qwen3vl  ·  **Engine**: qwen3-vl-8b@lmstudio  ·  **model**: qwen/qwen3-vl-8b  ·  max_tokens=4096
- **Sample**: 100 ảnh  ·  `sample_100.txt`
- **Generation**: avg 28.71s/ảnh · p50 13.42s · max 65.96s · 48.4 phút · lỗi 0

## Tổng quan theo task

| Task.metric | Value | Chiều |
|---|---|---|
| text_block.Edit_dist | 0.467 | ↓ thấp=tốt |
| display_formula.Edit_dist | 0.538 | ↓ thấp=tốt |
| table.TEDS | 0.188 | ↑ cao=tốt |
| table.TEDS_structure_only | 0.364 | ↑ cao=tốt |
| table.Edit_dist | 0.792 | ↓ thấp=tốt |
| reading_order.Edit_dist | 0.410 | ↓ thấp=tốt |

## Ma trận nguồn tài liệu × task

> Edit_dist (text/formula/table/reading) **thấp=tốt** · TEDS **cao=tốt**. `–` = nguồn không có loại phần tử đó trên các trang sample; giá trị 1.0 ở formula/table thường nghĩa là trang không có công thức/bảng để khớp.

| data_source | text ↓ | formula ↓ | table TEDS ↑ | table edit ↓ | reading ↓ |
|---|---|---|---|---|---|
| PPT2PDF | 0.126 | 0.325 | 0.191 | 0.727 | 0.132 |
| book | 0.302 | 0.504 | 0.623 | 0.582 | 0.321 |
| academic_literature | 0.361 | 0.677 | 0.173 | 0.770 | 0.369 |
| colorful_textbook | 0.430 | 0.371 | – | – | 0.393 |
| note | 0.540 | – | 0.002 | 0.997 | 0.438 |
| magazine | 0.544 | – | – | – | 0.339 |
| exam_paper | 0.576 | 0.625 | 0.102 | 0.903 | 0.593 |
| research_report | 0.776 | – | 0.232 | 0.776 | 0.464 |
| newspaper | 0.906 | – | 0.000 | 1.000 | 0.872 |
| historical_document | 0.984 | – | – | – | 0.452 |
