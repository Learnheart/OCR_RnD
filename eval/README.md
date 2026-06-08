# OmniDocBench — Ground Truth & OCR Quality Eval

Bộ ground truth + công cụ đánh giá chất lượng OCR/document-parsing cho pipeline trong `RnD_pipeline/`.

> 🆕 **Người mới?** Đọc [`BENCHMARK_GUIDE.md`](BENCHMARK_GUIDE.md) trước — giới thiệu benchmark,
> giải thích các chỉ số (Edit Distance vs TEDS), cách đọc output và dùng số để tinh chỉnh pipeline.
> File README này là phần **thao tác/lệnh/env** chi tiết.

## Cấu trúc thư mục

```
eval/
├── OmniDocBench_data/          # GROUND TRUTH (tải từ HuggingFace)
│   ├── images/                 # 1651 ảnh trang tài liệu (.png)
│   └── OmniDocBench.json        # annotation đầy đủ (text/table/formula/reading order)
├── OmniDocBench_eval/          # CODE chấm điểm (clone từ GitHub)
│   ├── pdf_validation.py        # entrypoint
│   └── configs/
│       ├── end2end_local.yaml   # config Windows (CDM tắt) ← dùng cái này
│       └── end2end_full.yaml    # config đầy đủ (CDM bật, cần Docker/WSL)
├── predictions/
│   ├── end2end/                # ← THẢ output Markdown của pipeline vào đây
│   └── ocr/
├── results/                    # (tham khảo) kết quả copy ra cho gọn
├── check_setup.py              # kiểm tra GT + độ phủ prediction
└── README.md
```

> Kết quả chấm điểm thực tế được ghi vào `OmniDocBench_eval/result/` (do code quy định).

## Dataset là gì

OmniDocBench v1.5 — 1651 trang PDF thực tế, đa dạng:
- **Nguồn**: book, PPT, academic paper, exam paper, textbook, newspaper, magazine, research report, note…
- **Ngôn ngữ**: Trung giản thể (765), Anh (755), Trung-Anh hỗn hợp (116), Trung phồn thể (13)…
- **Annotation theo vùng**: text_block, title, table, equation, header/footer, figure, reading order…

## 0. Môi trường (đã setup sẵn)

Bộ chấm điểm yêu cầu **Python 3.10/3.11** (KHÔNG chạy được trên Python 3.12 mặc định của máy).
Đã tạo sẵn conda env `omnidocbench`:
```powershell
conda create -n omnidocbench python=3.10 -y
conda run -n omnidocbench python -m pip install -e .\OmniDocBench_eval
```
Python của env: `%USERPROFILE%\.conda\envs\omnidocbench\python.exe`
(`run_eval.ps1` tự gọi đúng python này — không cần `conda activate`).

## 1. Tải ground truth (nếu chưa có)

```powershell
pip install -U "huggingface_hub[cli]"
cd C:\Projects\ComputerVision\RnD_pipeline\eval
hf download opendatalab/OmniDocBench --repo-type dataset --local-dir OmniDocBench_data
```

> Nếu HF bị chặn ở VN: đặt `$env:HF_ENDPOINT="https://hf-mirror.com"` trước khi tải.
> `hf download` đôi khi báo xong nhưng thiếu file — luôn chạy `check_setup.py` để xác minh.

## 2. Kiểm tra setup

```powershell
cd C:\Projects\ComputerVision\RnD_pipeline\eval
python check_setup.py
```
Phải thấy `Ảnh THIẾU: 0` và `[OK] Ground truth đầy đủ.`

## 3. Chạy pipeline OCR và xuất prediction

Cho pipeline của bạn xử lý từng ảnh trong `OmniDocBench_data/images/`, xuất **mỗi trang 1 file `.md`** vào `predictions/end2end/`.

**Quy ước tên (bắt buộc)**: tên file = tên ảnh đổi đuôi sang `.md`
```
images/page-d1561665-....png   ->   predictions/end2end/page-d1561665-....md
```
Nội dung file .md = toàn bộ nội dung trang dưới dạng Markdown (text + bảng dạng HTML/Markdown + công thức dạng LaTeX `$...$`).

Lấy danh sách ảnh còn chưa xử lý:
```powershell
python check_setup.py --list-todo end2end > todo_images.txt
```
Kiểm tra độ phủ sau khi chạy:
```powershell
python check_setup.py --preds end2end
```

## 4. Chấm điểm

**Cách 1 — wrapper (khuyến nghị):** tự bật UTF-8 + dùng đúng env.
```powershell
cd C:\Projects\ComputerVision\RnD_pipeline\eval
.\run_eval.ps1                       # config mặc định end2end_local.yaml
.\run_eval.ps1 end2end_demo_local    # smoke-test trên demo (xác nhận harness OK)
```

**Cách 2 — thủ công:**
```powershell
cd C:\Projects\ComputerVision\RnD_pipeline\eval\OmniDocBench_eval
$env:PYTHONUTF8 = "1"   # BẮT BUỘC trên Windows (xem ghi chú bên dưới)
& "$env:USERPROFILE\.conda\envs\omnidocbench\python.exe" pdf_validation.py --config configs/end2end_local.yaml
```

Kết quả: `OmniDocBench_eval/result/end2end_quick_match_*_result.json`
và `..._metric_result.json` (điểm tổng hợp), bóc tách theo **ngôn ngữ / nguồn tài liệu / layout / nền màu**…
(bản tóm tắt cũng được copy ra `eval/results/`).

> ⚠️ **Bắt buộc `PYTHONUTF8=1` trên Windows.** Code OmniDocBench mở file JSON
> không khai báo `encoding`, nên console Windows (cp1252) sẽ crash với tiếng Trung/Việt.
> `run_eval.ps1` đã tự xử lý việc này.

**Metric trả về**: Edit Distance (text/formula/reading-order), TEDS (table).
Thấp hơn = tốt hơn với Edit Distance; TEDS cao hơn = tốt hơn.

### Đánh giá đầy đủ công thức (CDM)
CDM cần TeX Live + Ghostscript + ImageMagick → không chạy được trên Windows native.
Dùng Docker:
```powershell
docker pull ghcr.io/zeng-weijun/omnidocbench-eval:repro-ubuntu2204
```
rồi chạy với `configs/end2end_full.yaml`.

## Mẹo: test nhanh trên tập nhỏ

Để thử pipeline trước khi chạy cả 1651 trang, copy vài chục ảnh ra tập con và lọc JSON tương ứng — hoặc dùng demo có sẵn trong `OmniDocBench_eval/demo_data/`:
```powershell
cd OmniDocBench_eval
python pdf_validation.py --config configs/end2end.yaml   # config demo gốc
```
