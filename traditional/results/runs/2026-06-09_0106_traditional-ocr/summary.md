# Eval run — 2026-06-09_0106_traditional-ocr

- **Solution**: traditional-ocr  ·  **Engine**: paddleocr-ppstructure@cpu
- **Sample**: 100 images  ·  `sample_100.txt`
- **Generation**: avg 5.06s/img · p50 3.51s · max 37.54s · 8.4 min · err 0

## Overall by task

| Task.metric | Value | Dir |
|---|---|---|
| text_block.Edit_dist | 0.342 | ↓ low=good |
| display_formula.Edit_dist | 0.839 | ↓ low=good |
| table.TEDS | 0.170 | ↑ high=good |
| table.TEDS_structure_only | 0.420 | ↑ high=good |
| table.Edit_dist | 0.683 | ↓ low=good |
| reading_order.Edit_dist | 0.367 | ↓ low=good |

## Source × task matrix

| data_source | text ↓ | formula ↓ | table TEDS ↑ | table edit ↓ | reading ↓ |
|---|---|---|---|---|---|
| magazine | 0.167 | – | – | – | 0.119 |
| research_report | 0.186 | – | 0.342 | 0.534 | 0.399 |
| PPT2PDF | 0.237 | 0.762 | 0.248 | 0.764 | 0.277 |
| colorful_textbook | 0.241 | 0.651 | – | – | 0.232 |
| academic_literature | 0.325 | 0.901 | 0.403 | 0.410 | 0.348 |
| note | 0.350 | – | 0.000 | 1.000 | 0.285 |
| book | 0.374 | 0.808 | 0.245 | 0.664 | 0.460 |
| exam_paper | 0.448 | 0.925 | 0.000 | 1.000 | 0.497 |
| newspaper | 0.694 | – | 0.000 | 1.000 | 0.607 |
| historical_document | 0.918 | – | – | – | 0.286 |
