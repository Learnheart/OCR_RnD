# Eval run — 2026-06-10_0128_trad-v0.2.0b

- **Solution**: trad-v0.2.0b  ·  **Engine**: paddleocr-ppstructure@cpu
- **Sample**: 20 images  ·  `sample_100.txt`
- **Generation**: avg 2.57s/img · p50 2.28s · max 6.96s · 0.9 min · err 0

## Overall by task

| Task.metric | Value | Dir |
|---|---|---|
| text_block.Edit_dist | 0.198 | ↓ low=good |
| display_formula.Edit_dist | 0.732 | ↓ low=good |
| table.TEDS | 0.149 | ↑ high=good |
| table.TEDS_structure_only | 0.470 | ↑ high=good |
| table.Edit_dist | 0.743 | ↓ low=good |
| reading_order.Edit_dist | 0.293 | ↓ low=good |

## Source × task matrix

| data_source | text ↓ | formula ↓ | table TEDS ↑ | table edit ↓ | reading ↓ |
|---|---|---|---|---|---|
| colorful_textbook | 0.025 | – | – | – | 0.136 |
| magazine | 0.029 | – | – | – | 0.125 |
| book | 0.240 | 0.738 | 0.086 | 0.701 | 0.396 |
| PPT2PDF | 0.261 | 0.724 | 0.211 | 0.786 | 0.267 |
