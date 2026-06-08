# Hướng dẫn Benchmark OmniDocBench — cho người mới

> Tài liệu giới thiệu **benchmark dùng chung** của workspace: nó đo cái gì, các chỉ số
> nghĩa là gì, cách chạy, cách **đọc output** và **dùng số để tinh chỉnh pipeline**.
> Phần thao tác chi tiết (lệnh, env): [`README.md`](README.md). Quy ước workspace:
> [`../CLAUDE.md`](../CLAUDE.md).

Mục tiêu của mọi solution trong `RnD_pipeline/` là như nhau: **biến 1 trang tài liệu
thành output có cấu trúc (Markdown/HTML/LaTeX)**, rồi đo chất lượng trên cùng một thước
đo để **so sánh các cách làm một cách công bằng (apples-to-apples)**.

---

## 1. Benchmark là gì

**OmniDocBench v1.5** — 1651 trang tài liệu PDF **thật**, đa dạng cao:

- **Nguồn (`data_source`)**: book 276 · PPT2PDF 253 · academic_literature 215 ·
  exam_paper 193 · colorful_textbook 159 · newspaper 151 · magazine 149 ·
  research_report 132 · note 118 · historical_document 5.
- **Ngôn ngữ**: Trung giản thể 765 · Anh 755 · Trung-Anh hỗn hợp 116 · Trung phồn thể 13 · khác 2.
- **Thuộc tính khác**: layout (1 cột / nhiều cột…), nền (trắng / màu), loại đặc biệt
  (vd `equation_hard`).
- **Định dạng ảnh**: 981 `.jpg` + 670 `.png` (tổng 1651).

Ground truth (`OmniDocBench_data/OmniDocBench.json`) gán nhãn **theo vùng**: mỗi trang có
nhiều `layout_dets`, mỗi cái có `category_type` (text_block, title, table, equation,
header/footer, figure…), nội dung (`text` / `html` cho bảng / `latex` cho công thức) và
thứ tự đọc. Vì vậy benchmark đo được **từng loại nội dung tách biệt**, không chỉ một điểm gộp.

---

## 2. Bài toán & "hợp đồng" output

Với **mỗi ảnh** trong `OmniDocBench_data/images/`, solution phải xuất **đúng 1 file Markdown**
vào `predictions/end2end/`, **cùng tên** đổi đuôi `.md`:

```
images/PPT_Catalysis.ppt_page_016.png   →   predictions/end2end/PPT_Catalysis.ppt_page_016.md
```

Trong file `.md`: toàn bộ nội dung trang dưới dạng Markdown —
**text thường**, **tiêu đề** bằng heading, **bảng** dạng HTML `<table>…</table>`,
**công thức** dạng LaTeX `$…$` / `$$…$$`. Trình chấm sẽ tự tách các thành phần này ra để đo.

---

## 3. Các task & chỉ số đo

Benchmark đo **4 task**, mỗi task một chỉ số. Có **hai họ chỉ số ngược chiều nhau** —
đây là chỗ hay nhầm nhất:

| Chỉ số | Họ | Chiều | Áp dụng cho |
|---|---|---|---|
| **Edit Distance** (NED) | khoảng cách lỗi | **THẤP = tốt** (0=hoàn hảo, 1=sai hết) | text · formula · table · reading-order |
| **TEDS** | độ giống cấu trúc | **CAO = tốt** (1=hoàn hảo, 0=sai hết) | table |

### 3.1. Edit Distance (Normalized Edit Distance — NED)
Đếm số phép **chèn / xóa / thay ký tự** (Levenshtein) để biến chuỗi dự đoán thành chuỗi
ground-truth, rồi **chuẩn hóa theo độ dài** → số 0–1. Bản chất: so sánh **tuyến tính, theo
từng ký tự**, KHÔNG hiểu cấu trúc. Dùng cho:

- **text_block** — độ chính xác phiên âm text của trang.
- **display_formula** — so chuỗi LaTeX công thức. *(Lưu ý: chỉ số "xịn" cho công thức là
  **CDM**, nhưng CDM cần TeX Live + Ghostscript + ImageMagick → tắt trên Windows native;
  config local chấm công thức bằng Edit_dist. Muốn CDM đầy đủ phải chạy Docker.)*
- **reading_order** — thứ tự đọc các khối có khớp GT không (quan trọng với trang đa cột).
- **table (Edit_dist)** — so **chuỗi HTML** của bảng (xem 3.3 để hiểu hạn chế).

### 3.2. TEDS (Tree-Edit-Distance based Similarity) — riêng cho bảng
Parse bảng thành **cây HTML** (table → rows → cells, có `rowspan`/`colspan`), tính
tree-edit-distance giữa 2 cây → điểm tương đồng 0–1. **Hiểu cấu trúc lưới 2 chiều**: ô có
đúng hàng/cột không, gộp ô đúng không, nội dung ô có khớp không. Hai biến thể:

- **TEDS** = cấu trúc **+ nội dung ô**.
- **TEDS_structure_only** = chỉ **khung lưới** (bỏ qua chữ trong ô).

> So sánh `TEDS` với `TEDS_structure_only` rất hữu ích: nếu structure_only **cao hơn**
> nhiều → model dựng khung lưới ổn nhưng **đọc sai chữ trong ô**; nếu cả hai cùng thấp →
> sai cả khung.

### 3.3. `table TEDS` khác `table Edit_dist` ở chỗ nào
| | table **Edit_dist** | table **TEDS** |
|---|---|---|
| Nhìn bảng như | chuỗi HTML **phẳng** (1 chiều) | **cây/lưới** (2 chiều) |
| Hiểu cấu trúc? | **Không** | **Có** |
| Nhạy với | từng ký tự, thẻ tag, thứ tự, khoảng trắng | vị trí ô, ô gộp, nội dung ô |
| Vai trò | proxy thô | **metric bảng chuẩn** (leaderboard dùng) |

**Ví dụ**: GT bảng 2×2, model đọc đúng hết 4 ô chữ nhưng dựng sai thành 4 hàng 1 cột →
**TEDS thấp** (bắt đúng lỗi cấu trúc), còn **Edit_dist** chỉ thấy chuỗi HTML khác vài thẻ →
không phản ánh được bảng đã hỏng hình hài. → **TEDS mới là thước đo thật của bảng.**

---

## 4. Cách chạy đánh giá

> Trình chấm cần **Python 3.10/3.11** (conda env `omnidocbench`) + `PYTHONUTF8=1` trên
> Windows. `run_eval.ps1` tự lo cả hai. Chi tiết: [`README.md`](README.md).

### Quy tắc vàng (Rule 4): **nhỏ trước, rồi full**
Luôn chạy **1–2 ảnh** chứng minh end-to-end (đúng format, đúng tên file, chấm không crash)
TRƯỚC khi chạy cả 1651 trang.

### ⚠️ Bẫy quan trọng nhất: trình chấm chấm trên **TOÀN BỘ** ground truth
Ảnh **không có prediction** bị tính `edit_dist = 1.0` (coi như sai hoàn toàn). Hệ quả:

- Muốn chấm **full** → phải có **đủ 1651** prediction trong `predictions/end2end/`.
- Muốn chấm trên **một sample N ảnh** → phải **lọc ground truth xuống đúng N ảnh đó**,
  nếu không điểm tổng sẽ ≈ 1.0 (giả) dù prediction tốt.

### Hai đường chạy

**(A) Full / chuẩn workspace** — predictions vào thư mục chung, chấm trên toàn bộ GT:
```powershell
cd C:\Projects\ComputerVision\RnD_pipeline\eval
python check_setup.py                 # kiểm GT đủ chưa
python check_setup.py --preds end2end # độ phủ prediction
.\run_eval.ps1                        # chấm (config end2end_local.yaml)
.\run_eval.ps1 end2end_demo_local     # smoke-test trên demo (xác nhận harness OK)
```

**(B) Sample có timestamp (khuyến nghị khi so nhiều phương án)** — solution `hybrid`
có sẵn `scripts/eval_run.py`: tự sinh prediction trên sample → **tự lọc GT** → chấm →
archive vào `hybrid/results/runs/<ngày_giờ>_<solution>/` (isolated, không đụng thư mục chung):
```powershell
cd C:\Projects\ComputerVision\RnD_pipeline\hybrid
uv run python scripts/eval_run.py --n 100 --solution <tên-phương-án>
```
Sample **cố định, chia đều theo `data_source`** ở `eval/samples/sample_100.txt`
(tạo bằng `scripts/make_sample.py`) → **mọi phương án test trên cùng N ảnh** để so công bằng.

---

## 5. Cách đọc output

### 5.1. File kết quả thô
Sau khi chấm, trình chấm ghi vào `OmniDocBench_eval/result/`:
- `*_metric_result.json` — **điểm tổng hợp** (đọc cái này trước).
- `*_text_block_result.json`, `*_table_per_table_TEDS.json`, `*_*_per_page_edit.json` —
  chi tiết từng cặp khớp / từng trang (để debug sâu).

Cấu trúc `*_metric_result.json` (4 task, mỗi task 3 tầng):
```
<task>.all.<metric>          → điểm tổng của task (ALL_page_avg / "all" cho TEDS)
<task>.page.<metric>         → bóc tách theo trang: "data_source: book", "ALL", …
<task>.group.<metric>        → bóc tách theo nhóm: language / background / layout
```
Ví dụ đường dẫn hay dùng:
- `text_block.all.Edit_dist.ALL_page_avg` — điểm text tổng.
- `table.all.TEDS.all` — TEDS bảng tổng.
- `text_block.page.Edit_dist["data_source: newspaper"]` — text của riêng báo.

### 5.2. Bản tóm tắt dễ đọc (`summary.md` của mỗi run, đường B)
Mỗi run có `summary.md` gồm:
- **Tổng quan theo task** — 6 dòng (text · formula · table TEDS · table TEDS_struct ·
  table edit · reading-order), mỗi dòng kèm **mũi tên chiều** (↑/↓).
- **Ma trận nguồn × task** — mỗi `data_source` × 5 cột (text↓ · formula↓ · table TEDS↑ ·
  table edit↓ · reading↓) → thấy ngay phương án **mạnh/yếu ở loại tài liệu nào, task nào**.

Kèm theo trong thư mục run: `meta.json` (engine/model/config/latency), `latency.json`
(per-ảnh), `gt_subset.json` (GT đã lọc), `eval_config.yaml`, `predictions/`, `result/`.

### 5.3. Đọc con số cho đúng (cảnh báo nhiễu)
- **Chiều**: Edit_dist **thấp=tốt**; TEDS **cao=tốt**. Đừng đọc ngược.
- **Per-source của table/formula rất nhiễu khi sample nhỏ**: mỗi nguồn chỉ có vài bảng/
  công thức. `–` = nguồn đó **không có** loại phần tử ấy trên trang sample. `table edit=1.0`
  + `TEDS=0.0` thường là **1 bảng duy nhất fail** → đừng kết luận chắc. Cột **text** và
  **reading-order** đáng tin nhất (mọi trang đều có text). Muốn cột bảng/công thức ổn định
  → **tăng sample** (300–500 ảnh).
- So **TEDS vs TEDS_structure_only** để biết lỗi nằm ở khung hay ở chữ trong ô.

---

## 6. Dùng số để tinh chỉnh pipeline

Mỗi metric chỉ thẳng vào một "đòn bẩy" cụ thể:

| Triệu chứng (số xấu) | Khả năng nguyên nhân | Đòn bẩy tinh chỉnh |
|---|---|---|
| **text_block Edit_dist** cao toàn cục | engine đọc chữ kém / ảnh mờ / sai ngôn ngữ | đổi/upgrade engine; tăng `RENDER_DPI`; sửa prompt giữ nguyên ngôn ngữ; (CJK) chọn model mạnh tiếng Trung |
| **reading_order** cao (nhất là newspaper) | sai thứ tự đọc đa cột | prompt nhấn "đọc trái→phải, trên→dưới theo cột"; cắm model reading-order (Surya/LayoutReader) |
| **table TEDS** thấp | dựng sai cấu trúc bảng | prompt bắt buộc HTML `<table>` + `rowspan/colspan`; cắm table model (PP-Structure SLANet / TATR) cross-check |
| **TEDS_structure_only** ổn nhưng **TEDS** thấp | khung đúng, **chữ trong ô** sai | cải thiện OCR ô bảng; tăng độ phân giải vùng bảng |
| **display_formula** cao | LaTeX sai | prompt LaTeX rõ; model chuyên công thức; chấm CDM (Docker) để đo đúng |
| Một **nguồn** kém hẳn (historical, newspaper) | layout dày/đa cột/ảnh cổ | tiền xử lý (deskew/dewarp/super-res) theo tier; tăng DPI; engine grounded |
| **Latency** cao / **runaway** (sinh lặp vô tận) | trang dày làm VLM lặp | cap `max_tokens`; thêm `frequency_penalty`; theo dõi ảnh đầu trước khi chạy nền |

**Vòng lặp tinh chỉnh đề xuất**: chạy đường B trên cùng `sample_100` → đọc `summary.md` →
xác định task/nguồn yếu nhất → chỉnh **một** đòn bẩy → chạy lại với `--solution <tên-mới>`
→ so `summary.md` giữa các run. Mỗi thay đổi một run riêng để truy được cái gì giúp/hại.

---

## 7. Tra cứu nhanh

| Việc | Lệnh |
|---|---|
| Kiểm GT đủ | `python check_setup.py` |
| Độ phủ prediction | `python check_setup.py --preds end2end` |
| Danh sách ảnh chưa làm | `python check_setup.py --list-todo end2end > todo.txt` |
| Chấm full (thư mục chung) | `.\run_eval.ps1` |
| Smoke harness | `.\run_eval.ps1 end2end_demo_local` |
| Sample + chấm + archive (hybrid) | `uv run python scripts/eval_run.py --n 100 --solution <tên>` |
| Tạo sample cố định | `uv run python scripts/make_sample.py --n 100` |
| Tái tóm tắt run cũ | `uv run python scripts/resummarize.py results/runs/<id>` |

**Chiều metric (nhớ kỹ)**: Edit Distance ↓ thấp=tốt · TEDS ↑ cao=tốt.

> Tài liệu liên quan: [`README.md`](README.md) (thao tác/env) · [`../CLAUDE.md`](../CLAUDE.md)
> (quy ước workspace) · `../hybrid/AGENT.md` (ví dụ một solution + baseline số đo thực tế).
