# Eval run — 2026-06-08_0511_hybrid-qwen3vl

- **Solution**: hybrid-qwen3vl  ·  **Engine**: qwen3-vl-8b@lmstudio  ·  **model**: qwen/qwen3-vl-8b  ·  max_tokens=4096
- **Sample**: 100 ảnh  ·  `sample_100.txt`
- **Generation**: avg 0.0s/ảnh · p50 0s · max 0s · 0.0 phút · lỗi 0

## Overall (Edit_dist: thấp=tốt · TEDS: cao=tốt)

| Metric | Value |
|---|---|
| text_block.Edit_dist | 0.467 |
| display_formula.Edit_dist | 0.5384 |
| table.TEDS | 0.1881 |
| table.TEDS_structure_only | 0.3636 |
| table.Edit_dist | 0.7919 |
| reading_order.Edit_dist | 0.4105 |

## text_block Edit_dist theo nguồn (thấp=tốt)

| data_source | Edit_dist |
|---|---|
| PPT2PDF | 0.1255 |
| book | 0.3025 |
| academic_literature | 0.361 |
| colorful_textbook | 0.4299 |
| note | 0.5402 |
| magazine | 0.5442 |
| exam_paper | 0.5755 |
| research_report | 0.7762 |
| newspaper | 0.906 |
| historical_document | 0.9844 |
