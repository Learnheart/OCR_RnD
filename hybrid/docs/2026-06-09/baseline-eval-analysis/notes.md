---
author: lytinh358@gmail.com
date: 2026-06-09
status: done
agents: hybrid
summary: Phân tích kết quả test baseline v0.0.1 (Qwen3-VL-8B @ LM Studio) trên OmniDocBench 100 ảnh — chẩn đoán 4 vấn đề pipeline, runaway/hallucination là thủ phạm chính.
---

# Notes — Kết quả test baseline v0.0.1 & chẩn đoán pipeline

> Engine: `qwen3-vl-8b@lmstudio` · sample cố định `eval/samples/sample_100.txt` (100 ảnh) ·
> `temperature=0.0`, `max_tokens=4096`, `frequency_penalty=0.3`.
> Nguồn dữ liệu: `results/runs/2026-06-08_0357|0511|0614_hybrid-qwen3vl/`.

## 1. Tóm tắt: 3 lần chạy nhưng chỉ có 1 kết quả thực

| Run | Sinh prediction | Kết quả |
|---|---|---|
| `0357` | sinh mới 100 ảnh | điểm X |
| `0511` | `reuse_seeded=100`, `n_total=0` → **không sinh gì** | điểm X (y hệt) |
| `0614` | sinh lại mới 100 ảnh (`reuse_seeded=0`) | điểm X (**y hệt tới 16 chữ số thập phân**) |

`temperature=0.0` (greedy) → decode tất định → output byte-identical → điểm identical.
`0511` và `0614` **không thêm thông tin gì**. Kết luận quy trình: chưa có ước lượng
variance; **ngừng rerun cùng config** — chỉ rerun khi đã đổi prompt/tham số.

> ⚠️ Cần xác minh: `0614` sinh lại tươi mà điểm trùng tới 16 chữ số thập phân — chỉ đúng
> nếu scorer đọc đúng predictions của chính run đó. Kiểm tra `scripts/eval_run.py` không
> vô tình chấm lại từ thư mục `eval/predictions/end2end/` dùng chung/cache cũ.

## 2. Điểm baseline v0.0.1 (100 ảnh; Edit_dist thấp=tốt, TEDS cao=tốt)

```
text_block Edit_dist   0.467     (SOTA ~0.05–0.10 → rất tệ)
table TEDS             0.188     (SOTA ~0.85 → gần như hỏng)
table TEDS (struct)    0.364
reading_order          0.411
display_formula        0.538
table Edit_dist        0.792
```

Theo `data_source` (text_block Edit_dist), các nhóm tệ nhất:
`historical_document 0.984 · newspaper 0.906 · research_report 0.776 · exam_paper 0.575 · magazine 0.544`.
Nhóm ổn: `PPT2PDF 0.126 · book 0.302 · academic 0.361 · single_column 0.346`.

## 3. Vấn đề #1 — VLM runaway + hallucination trên trang dày (thủ phạm chính)

Nguyên nhân số 1 kéo điểm. Bằng chứng trực tiếp trong predictions:
- `newspaper_2a6b4...`: sinh `(a) The authority for this rule is 50 U.S.C...` lặp từ
  `(a)` đến `(cu)` — văn bản **bịa hoàn toàn**, lặp vô tận tới khi chạm `max_tokens`.
- `magazine_TheEconomist.2023.12.16_page_037`: bịa tác giả "John H. Smith", lặp 1 đoạn ~50 lần.

**Quy mô (từ `latency.json`):** ~**35/100 ảnh** chạm trần ~64–66s (= chạm `max_tokens=4096`),
kèm char count phình to (newspaper 21.317 / scihub 20.930 / magazine 19.756 ký tự). 35 trang
runaway này nuốt ~37/48 phút wall-clock. p50 chỉ 13s → **một nửa ảnh OK, cái đuôi dày toàn
runaway** vừa giết điểm vừa giết throughput.

**Quan trọng:** fix trước đó (`max_tokens=4096` + `frequency_penalty=0.3`) **chỉ chặn thời gian,
KHÔNG chặn hallucination**. Ở `temperature=0` greedy, `frequency_penalty=0.3` quá yếu để phá
vòng lặp khi model "đọc không nổi" trang.

## 4. Vấn đề #2 — "Hybrid" thực chất đang là 100% VLM, Tier 0 không bao giờ chạy

`classify/router.py`: `is_digital_born()` trả `False` khi `page.pdf_page is None`. OmniDocBench
cấp **ảnh** (`.jpg`/`.png`), không phải PDF có text-layer → **mọi trang route sang Tier B**.
"Free win, zero hallucination" của Tier 0 (PyMuPDF/pdfplumber) **không xảy ra lần nào** trên
benchmark này. Số đo hiện tại = **pure-VLM baseline**, không phải kiến trúc tiered như tên gọi.
→ Cần ghi rõ điều này trong `AGENT.md` để khỏi hiểu nhầm số liệu.

## 5. Vấn đề #3 — Bảng gần như hỏng (TEDS 0.188)

newspaper TEDS **0.0**, note **0.0015**, exam **0.10**. VLM không phát hiện/emit `<table>` HTML
khớp cấu trúc. `frequency_penalty=0.3` còn phản tác dụng: bảng vốn nhiều token lặp (cell rỗng,
số) → bị phạt → cấu trúc vỡ thêm.

## 6. Vấn đề #4 — Reading order vỡ ở layout nhiều cột

three_column **0.973**, newspaper reading **0.872**, double_column **0.454**. VLM bị quăng cả
trang đa cột dày và mất thứ tự đọc.

## 7. Khuyến nghị (ưu tiên giảm dần)

1. **Diệt runaway (ROI cao nhất).** `tier_b_lmstudio_vlm.py`: thêm `presence_penalty` +
   `repetition_penalty`, và đặt **`temperature ~0.1–0.2`** thay vì 0.0 (greedy tuyệt đối dễ kẹt
   vòng lặp nhất). Thêm **post-process dò lặp n-gram** (>k lần → cắt) làm lưới an toàn. Cứu được
   newspaper/magazine/historical/research_report.
2. **Cắt trang dày trước khi đưa vào VLM.** Ảnh đa cột/dày → tách cột hoặc chia ngang thành 2–3
   lát, mỗi lát 1 lần gọi → ghép. Giảm runaway + cứu reading_order + giảm latency đuôi.
3. **Làm Tier 0 có ích trên ảnh**, hoặc ghi rõ pipeline đang đo là pure-VLM, hoặc thêm Tier OCR
   truyền thống (PaddleOCR) cho ảnh để có đường "rẻ" thật.
4. **Tách prompt cho bảng** / giảm `frequency_penalty` riêng cho trang nhiều bảng — TEDS 0.188 là
   điểm dễ cải thiện nhất sau runaway.
5. **Quy trình:** ngừng rerun cùng config (tất định). Mỗi thay đổi = 1 run mới, meta ghi rõ cái
   gì đổi, so chéo trên cùng `sample_100.txt`.

## 8. Kết luận

Bản thân Qwen3-VL ổn (trang sạch/đơn giản điểm tốt). Pipeline sập đúng vào: **trang dày, đa cột,
scan, và bảng** — và cơ chế sập là **runaway/hallucination khi chạm max_tokens**. Ưu tiên #1 cho
vòng lặp tiếp theo là chống lặp ở Tier B; đây là thay đổi nhỏ nhưng cứu được nhiều category nhất.
