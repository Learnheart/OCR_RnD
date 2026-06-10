---
author: lytinh358@gmail.com
date: 2026-06-10
status: draft
agents: hybrid
summary: Kiến trúc hybrid V2 — preprocessing → layout detection (PP-DocLayout, 20+ nhãn) → fan-out song song theo loại vùng (text/table/formula/chart/seal) → khôi phục reading order & merge → MD/JSON/DOCX. Mỗi step có output trung gian để truy vết & chấm chất lượng riêng.
---

# Plan — Hybrid V2: Modular Layout-Driven Pipeline

## Problem statement

Hybrid V1 (đường chính trên OmniDocBench) là **VLM một-bước hộp đen**: cả trang ảnh → 1 lần gọi Qwen3-VL → 1 block Markdown (no bbox). Hệ quả:

1. **Không truy vết được từng bước** — layout, OCR text, table, formula, reading order đều gộp trong một lần gọi VLM; không có ranh giới trung gian để chấm riêng hay quy lỗi.
2. **VLM quá tải** — phải tự lo toàn bộ (đa cột, bảng→HTML, công thức→LaTeX, reading order) trong 1 prompt → điểm thấp ở trang dày/đa cột (newspaper 0.91, historical 0.98, table TEDS 0.188).
3. **Không tận dụng engine deterministic** — bảng/text PDF số đáng ra chấm bằng PP-Structure/text-layer thì lại đẩy hết cho VLM.

V2 chuyển sang kiến trúc **detect → fan-out chuyên biệt → merge** (theo `highlevel_design.png`): chia nhỏ tài liệu thành các vùng theo loại, mỗi loại do một module đơn lẻ xử lý song song, rồi khôi phục thứ tự. Mục tiêu: **giảm tải VLM + mỗi step có output trung gian kiểm tra/chấm độc lập**.

## Goals & non-goals

**Goals**
- Kiến trúc modular 5 step có ranh giới rõ: Preprocess → Layout → Fan-out (5 handler) → Reading-order/Merge → Serialize.
- **Eval per-step**: tận dụng annotation OmniDocBench (`category_type` + `poly` + `order` + `text` mỗi vùng) để chấm riêng từng step, không chỉ markdown cuối.
- Engine **hybrid deterministic + VLM**: dùng bộ rẻ ở đâu được (PP-Structure cho bảng, text-layer/OCR cho văn bản), VLM chỉ cho nhánh khó (công thức, biểu đồ, con dấu).
- Giữ contract `ParseEngine` + `schemas.py` để A/B với V1 trên cùng harness; **không phá baseline V1**.
- So sánh đối chứng **V1 (end2end VLM) ↔ V2 (modular)** trên cùng OmniDocBench.

**Non-goals (để Phase sau)**
- Validation & Grounding Gate, calibration, PII, HITL (giữ stub như V1 — xem `architecture.md` mục 3.5–3.7).
- Banking KIE / field extraction (Tier A/C). Slice này vẫn là **general doc-parsing** trên OmniDocBench.
- Output DOCX thật (chỉ thiết kế interface; slice đầu chấm MD; JSON là phụ phẩm của Block[]).

## Requirements

- **R1 — Preprocessing**: chuẩn hóa nhẹ cho luồng VLM/detector (deskew + orientation; dewarp/denoise tùy chọn). Giữ ảnh gốc cho provenance. (architecture.md mục 3.1 — "tiền xử lý nhẹ cho VLM".)
- **R2 — Layout detection (định tuyến)**: PP-DocLayout_plus-L → danh sách `Region{label, poly, score}` với 20+ nhãn. Chạy **CPU** (Blackwell sm_120 + paddle-gpu hỏng → ép `use_gpu=False`, xem [[blackwell-paddle-gpu-broken]]).
- **R3 — Fan-out song song**: dispatch mỗi region tới handler theo loại; 5 nhóm handler: **text · table · formula · chart · seal**. Handler chạy độc lập, song song được.
- **R4 — Engine hybrid**: text = text-layer (PDF số) / PP-OCRv5 (ảnh); table = PP-Structure SLANet → HTML; formula/chart/seal = Qwen3-VL @ LM Studio với prompt theo loại (crop vùng, không feed cả trang).
- **R5 — Reading order & merge**: gộp Block[] từ mọi handler, khôi phục thứ tự đọc đa cột (XY-cut baseline → LayoutReader/Surya nếu cần), gán `reading_order`.
- **R6 — Serialize**: Block[] → Markdown (như V1, cho OmniDocBench) + JSON (DocumentResult). DOCX = interface, chưa implement.
- **R7 — Per-step trace**: mỗi step ghi artifact trung gian (regions.json, per-region outputs, order) để eval & debug.
- **R8 — Rule 4**: smoke 1–2 ảnh trước, rồi 100-img sample (so V1), rồi full 1651.
- **R9 — Per-page visual trace bundle (★ ưu tiên trước)**: mỗi trang → **1 folder kết quả** chứa artifact **xem được bằng mắt** cho từng step: ảnh overlay bbox (layout, màu theo nhóm + nhãn + region_id), crop từng vùng, text/HTML/LaTeX OCR mỗi vùng, ảnh overlay reading-order (số thứ tự + mũi tên), markdown/JSON cuối, và **`index.html` tổng hợp** xem mọi step cạnh nhau. Mục tiêu: người đọc nhìn 1 trang là hiểu rõ pipeline làm gì ở mỗi bước. Đặc tả: `design.md` mục 10.
- **R10 — Sample-first workflow**: chạy & soi trực quan trên `../eval/sample/` (9 ảnh chụp thật `page1..9.jpg`, **không có GT** → QA định tính) **TRƯỚC**; chỉ khi trace bundle nhìn hợp lý mới chạy OmniDocBench (`sample_100` có GT → chấm số) như bản cũ. Đặc tả: `design.md` mục 11.

## Decisions made (chốt 2026-06-10 từ Q&A)

| # | Quyết định | Lý do |
|---|---|---|
| D1 | **Engine = hybrid deterministic + VLM** | Bảng/text dùng bộ rẻ chính xác hơn VLM general; VLM chỉ cho phần khó → giảm tải, dễ truy vết. |
| D2 | **Layout = PP-DocLayout_plus-L (CPU)** | ~23 nhãn khớp "20+", có sẵn `seal`/`chart`. Ép CPU vì paddle-gpu hỏng trên Blackwell ([[blackwell-paddle-gpu-broken]]). Đồng bộ stack với `traditional/`. |
| D3 | **Tiến hóa `hybrid/` tại chỗ** | Thêm module V2 vào `src/idp/`, giữ `ParseEngine`/`schemas` contract. Pipeline V1 và V2 chọn bằng config/flag để A/B trên cùng eval. |
| D4 | **Slice này = design docs only** | Plan-first (Rule 1). Code sau khi duyệt. |
| D5 | **Eval per-step bằng annotation OmniDocBench** | GT JSON đã có `category_type`+`poly`+`order`+`text` mỗi vùng → chấm layout/region/order độc lập, không cần label mới. |
| D6 | **VLM nhận crop vùng, không cả trang** | Đúng tinh thần "chia nhỏ"; giảm hallucination & token; mỗi call có scope hẹp dễ verify. |
| D7 | **Tái dùng conda env `ocr-worker` của `traditional/`** cho paddle CPU | Env đã có paddle CPU + PP-OCRv4/PP-Structure chạy được ([[traditional-ocr-solution]]); chỉ thêm PP-DocLayout_plus-L, khỏi cài lại từ đầu. VLM handler vẫn gọi LM Studio qua HTTP (không phụ thuộc env này). |

## Per-step evaluation plan (mấu chốt)

GT OmniDocBench (`eval/OmniDocBench_data/OmniDocBench.json`, 1651 trang) chứa mỗi vùng: `category_type` (~25 nhãn: text_block, title, table, equation_isolated, figure, header, footer, page_number, abandon…), `poly` (4 điểm), `order` (reading order), `text` (nội dung GT). → cho phép chấm **từng step**:

| Step | Artifact dự đoán | GT đối chiếu | Metric |
|---|---|---|---|
| 1. Preprocess | góc deskew, orientation, quality flag | (cần nhãn phụ; OmniDocBench không có orient GT trực tiếp) | skew error, orient acc — **đo trên set tự gán** |
| 2. Layout detect | `Region[]{label,poly}` | `layout_dets[].category_type + poly` | **mAP / P-R per class**, IoU-matched |
| 3a. Text handler | text mỗi vùng text/title | `text` của vùng tương ứng | CER / Edit_dist **per-region** |
| 3b. Table handler | HTML mỗi vùng table | `text` (HTML) vùng table | **TEDS per-region** |
| 3c. Formula handler | LaTeX mỗi vùng equation | `text` (LaTeX) vùng equation | Edit_dist / CDM **per-region** |
| 3d. Chart handler | mô tả/bảng vùng chart/figure | (OmniDocBench chart GT hạn chế) | **gap — đánh dấu**, đo định tính |
| 3e. Seal handler | text/ phát hiện con dấu | (OmniDocBench không có seal category) | **gap — đánh dấu**, đo trên set riêng |
| 4. Reading order | thứ tự Block[] | `order` field | reading_order Edit_dist (như harness) |
| 5. End-to-end | markdown cuối | toàn trang GT | **harness OmniDocBench hiện tại** (so V1↔V2) |

> **Gap đã biết**: OmniDocBench tập trung text/table/formula/order; **chart và seal** không có category GT đầy đủ → 2 nhánh này chấm định tính hoặc cần benchmark phụ. Sẽ `log()` rõ thay vì giả vờ phủ hết.

Bộ chấm per-step là **harness mới trong `hybrid/`** (không sửa `eval/` chung — Rule 2), đọc `OmniDocBench.json` + artifact trung gian của pipeline.

## Implementation approach (milestones — code ở slice sau)

> Nguyên tắc R10: **mọi milestone nghiệm thu trên `../eval/sample/` (9 ảnh) bằng trace bundle trực quan TRƯỚC**, rồi mới đụng OmniDocBench. Trace bundle (R9/design mục 10) dựng ngay ở M0–M1 để mọi step sau "rơi" artifact vào đó.

- **V2-M0** — Schema mở rộng: `Region`, `RegionGroup`, map 23 nhãn PP-DocLayout → 5 nhóm, `LayoutResult`; `RegionHandler` ABC + registry. **Khung trace bundle** (`trace/bundle.py`: tạo folder/page, ghi json + ảnh overlay + index.html). Test contract.
- **V2-M1** — `preprocess/` (deskew+orient nhẹ) + `layout/ppdoclayout.py` (CPU). **Chạy 9 ảnh sample → mỗi ảnh 1 folder** có `01_preprocess/` + `02_layout/overlay.jpg` + crops + `index.html`. Soi mắt: bbox layout có đúng cột/vùng không. (Eval step-2 mAP để dành — sample không GT.)
- **V2-M2** — Handlers deterministic: `text` (text-layer/PP-OCRv5) + `table` (PP-Structure). Trace `03_handlers/` (text/HTML mỗi vùng + overlay_ocr). Soi mắt trên sample. Sau đó eval per-region CER/TEDS trên `sample_100` (có GT).
- **V2-M3** — Handlers VLM: `formula` + `chart` + `seal` (Qwen3-VL crop-prompt). Trace LaTeX/mô tả mỗi vùng. Soi sample → eval formula Edit_dist.
- **V2-M4** — `reading_order/` (XY-cut → LayoutReader) + merge → serialize MD/JSON. Trace `04_reading_order/order_overlay.jpg` (số thứ tự + mũi tên). Soi sample → **End-to-end V2 trên `sample_100`, so V1**.
- **V2-M5** — Full 1651 + bảng so sánh V1↔V2 + per-step dashboard. Cập nhật `AGENT.md` + Agent Index.

## Risks / open questions

1. **PP-DocLayout trên CPU chậm** — cần đo latency/trang; có thể là bottleneck so với V1 (28.7s/img đã do VLM). Đo ngay V2-M1.
2. **Danh sách nhãn PP-DocLayout_plus-L chính xác** — phải verify với version model thực cài (design giả định 23 nhãn gồm seal/chart). Map nhãn ↔ 5 nhóm chốt sau khi xác nhận.
3. **Map nhãn PP-DocLayout ↔ category OmniDocBench** cho eval step-2 — 2 taxonomy khác nhau, cần bảng ánh xạ (vd PP `seal`→(không có GT), PP `formula`→`equation_isolated/semantic`).
4. **Reading order đa cột** — XY-cut yếu với layout phức tạp; LayoutReader/Surya thêm dependency. Bắt đầu XY-cut, leo thang nếu order Edit_dist tệ.
5. **Crop chất lượng** phụ thuộc layout bbox đúng — lỗi step-2 lan xuống step-3 (error propagation). Per-step eval giúp tách phần này: chấm handler trên **GT crop** (oracle) vs **predicted crop** để cô lập lỗi layout.
6. **Chi phí VLM nhiều call/trang** — V2 gọi VLM nhiều lần (mỗi vùng formula/chart/seal) thay vì 1 lần/trang. Cân nhắc batch hoặc chỉ leo thang khi cần.

## Tài liệu liên quan
- `design.md` (cùng thư mục) — thiết kế kỹ thuật chi tiết: module, contract per step, label mapping, orchestration, eval harness.
- `../../../architecture.md` — TDD đầy đủ (7 stage); V2 là hiện thực hóa Stage 1 (preprocess) + Stage 4 (extraction phân nhánh) + reading order.
- `../../../AGENT.md` — source of truth; cập nhật mục 3/7 khi V2 vào code.
- `highlevel_design.png` — sơ đồ kiến trúc V2 (nguồn yêu cầu).
