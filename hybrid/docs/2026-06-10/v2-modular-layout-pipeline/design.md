---
author: lytinh358@gmail.com
date: 2026-06-10
status: draft
agents: hybrid
summary: Thiết kế kỹ thuật chi tiết hybrid V2 — module, contract per-step, ánh xạ nhãn PP-DocLayout↔5 nhánh↔OmniDocBench, orchestration song song, per-step eval harness.
---

# Design — Hybrid V2: Modular Layout-Driven Pipeline

> Đọc cùng `plan.md`. File này đặc tả **contract vào/ra từng step** (cơ sở của eval per-step) và **cấu trúc code** khi tiến hóa `hybrid/src/idp/` tại chỗ.

## 1. Sơ đồ luồng V2

```
file (img/pdf)
  │
  ▼
[S1] PREPROCESS          preprocess/  ──────────► PreprocessedPage {image, gray, angle, orient, quality, source_ref}
  │
  ▼
[S2] LAYOUT DETECT       layout/      ──────────► LayoutResult { regions: Region[] }   (PP-DocLayout, CPU, 20+ nhãn)
  │                                                 dump: regions.json  ◄── EVAL step-2 (mAP)
  │  fan-out theo Region.group
  ├──► text   ─► TextHandler     (text-layer / PP-OCRv5)
  ├──► table  ─► TableHandler    (PP-Structure SLANet → HTML)
  ├──► formula─► FormulaHandler  (Qwen3-VL crop → LaTeX)
  ├──► chart  ─► ChartHandler    (Qwen3-VL crop → mô tả/bảng)
  └──► seal   ─► SealHandler     (detect + Qwen3-VL/seal-OCR)
  │                                                 mỗi handler → Block (bbox = region.poly)
  │                                                 dump: blocks_raw.json ◄── EVAL step-3 (per-region CER/TEDS/Edit)
  ▼  fan-in
[S4] READING ORDER+MERGE reading_order/ ─────────► Block[] có reading_order  ◄── EVAL step-4 (order Edit_dist)
  │
  ▼
[S5] SERIALIZE           serialize/   ──────────► markdown (OmniDocBench) + JSON (DocumentResult) [+DOCX iface]
                                                    ◄── EVAL step-5 (end2end, so V1)
```

Song song hóa: các handler trong fan-out độc lập theo region → chạy concurrent (thread/async). Reading-order là **barrier** (cần mọi block để sắp xếp).

## 2. Schema mở rộng (`schemas.py`)

Giữ nguyên `BBox`, `Block`, `PageResult`, `DocumentResult` (V1 compatible). Thêm:

```python
RegionGroup = Literal["text", "table", "formula", "chart", "seal", "drop"]

# 23 nhãn PP-DocLayout_plus-L (verify với model thực — mục 4)
RegionLabel = Literal[
    "doc_title","paragraph_title","text","abstract","content","reference",
    "footnote","header","footer","page_number","aside_text","number",
    "figure_title","table_title","chart_title","algorithm",
    "table","formula","formula_number","figure","chart","seal", ...  # đóng băng sau khi verify
]

class Region(BaseModel):
    label: RegionLabel
    group: RegionGroup          # nhóm fan-out (map từ label)
    bbox: BBox                  # poly từ layout detector (pixel ảnh gốc)
    score: float                # confidence detector
    region_id: int              # ổn định để trace qua các step
    reading_order: int | None = None   # gán ở S4

class LayoutResult(BaseModel):
    page: int
    regions: list[Region] = Field(default_factory=list)
    image_size: tuple[int, int]        # (w,h) để chuẩn hóa bbox khi cần
```

`Block` (đã có) được handler trả về, **mang lại `bbox = region.bbox`** → V2 có grounding thật cho mọi nhánh deterministic (khác V1 no-bbox). VLM crop handler vẫn gắn bbox = bbox vùng (grounding ở mức vùng, không mức ký tự).

## 3. Contract từng step

### S1 — Preprocess (`preprocess/`)
- **In**: `LoadedPage` (từ `ingest/loader.py` hiện có).
- **Out**: `PreprocessedPage { image_bytes, angle_deg, orientation, quality_score, source_ref }`.
- **Làm**: deskew (OpenCV/projection), orientation 0/90/180/270 (PP-LCNet doc-orient), quality gate (variance-of-Laplacian → cờ low-quality, **không** reject ở slice đầu). **Nhẹ** cho luồng VLM/detector (architecture.md mục 3.1 callout ⚠️). Giữ ảnh gốc.
- **Config**: bật/tắt từng bước; mặc định chỉ deskew + orient.

### S2 — Layout detect (`layout/ppdoclayout.py`)
- **In**: `PreprocessedPage`.
- **Out**: `LayoutResult{regions}`.
- **Engine**: PP-DocLayout_plus-L qua PaddleX/PaddleOCR, `use_gpu=False` (bắt buộc — [[blackwell-paddle-gpu-broken]]).
- **Map label→group**: bảng tra cứu (mục 5). Vùng `abandon`/`*_mask`/`page_number`(tùy) → `group="drop"`.
- **Trace**: dump `regions.json` (region_id, label, group, bbox, score) → input của **eval step-2**.
- **Interface** để swap detector khác (DocLayout-YOLO) sau:
```python
class LayoutDetector(ABC):
    name: str
    @abstractmethod
    def detect(self, page: PreprocessedPage) -> LayoutResult: ...
```

### S3 — Fan-out handlers (`extract/handlers/`)
ABC chung + registry dispatch theo `group`:
```python
class RegionHandler(ABC):
    group: RegionGroup
    @abstractmethod
    def handle(self, region: Region, page: PreprocessedPage) -> Block: ...

HANDLERS: dict[RegionGroup, RegionHandler]   # registry, chọn bằng config
```
| Handler | group | Engine (D1 hybrid) | Out Block |
|---|---|---|---|
| `TextHandler` | text | text-layer (PDF số) → fallback **PP-OCRv5 rec** (ảnh) | `type=text/title`, `text=`, bbox |
| `TableHandler` | table | **PP-Structure SLANet** → HTML | `type=table`, `html=`, bbox |
| `FormulaHandler` | formula | **Qwen3-VL** crop, prompt LaTeX-only | `type=formula`, `latex=`, bbox |
| `ChartHandler` | chart | **Qwen3-VL** crop, prompt mô tả/→bảng | `type=figure`, `text=`/`html=`, bbox |
| `SealHandler` | seal | detector + **Qwen3-VL**/PaddleOCR seal | `type=figure`, `text=`, bbox |

- **Crop**: cắt ảnh theo `region.bbox` (+padding) → input handler. VLM nhận **crop**, không cả trang (D6).
- **Song song**: nhóm region theo group, chạy concurrent. Lỗi 1 region → Block rỗng + warning, không phá trang.
- **Trace**: dump `blocks_raw.json` (region_id → Block) → input **eval step-3**.

### S4 — Reading order & merge (`reading_order/`)
- **In**: `Block[]` (mọi handler) + `Region[]`.
- **Out**: `Block[]` có `reading_order` liên tục.
- **Thuật toán**: baseline **XY-cut** (đệ quy cắt khoảng trắng dọc/ngang → thứ tự đa cột); leo thang **LayoutReader/Surya order** nếu order Edit_dist tệ. Drop region `group="drop"`.
- **Trace**: thứ tự region_id → **eval step-4**.

### S5 — Serialize (`serialize/`)
- Mở rộng `markdown.py` hiện có (đã xử lý table HTML/formula `$$`). Thêm `json.py` (dump `DocumentResult`) + `docx.py` (interface stub).
- **Out OmniDocBench**: vẫn 1 file `.md`/ảnh vào `eval/predictions/end2end/` (output contract không đổi).

## 4. Orchestration (`pipeline_v2.py`)

Pipeline V2 song song với V1 (không thay `pipeline.py`); chọn bằng flag/config (D3).
```python
@dataclass
class PipelineV2:
    preprocessor: Preprocessor
    detector: LayoutDetector
    handlers: dict[RegionGroup, RegionHandler]
    orderer: ReadingOrderer
    trace_dir: Path | None = None

    def process_page(self, page: LoadedPage) -> PageResult:
        pp = self.preprocessor.run(page)                 # S1
        layout = self.detector.detect(pp)                # S2  → regions.json
        blocks = []
        for group, regs in group_by(layout.regions):    # S3  fan-out song song
            h = self.handlers.get(group)
            if h is None: continue                       # drop
            blocks += parallel_map(lambda r: h.handle(r, pp), regs)
        ordered = self.orderer.order(blocks, layout)     # S4  barrier → reading_order
        return PageResult(page=page.index, blocks=ordered, image_uri=pp.source_ref)
```
- `parallel_map`: `ThreadPoolExecutor` (handler I/O-bound: HTTP VLM + paddle CPU). Cap concurrency.
- `trace_dir` set → dump regions.json / blocks_raw.json / order.json mỗi trang cho eval & debug.

## 5. Ánh xạ nhãn (đóng băng sau khi verify model + GT)

**PP-DocLayout label → RegionGroup** (fan-out):
| group | PP-DocLayout labels |
|---|---|
| text | doc_title, paragraph_title, text, abstract, content, reference, footnote, header, footer, aside_text, number, algorithm, figure_title, table_title, chart_title, formula_number |
| table | table |
| formula | formula |
| chart | chart, figure |
| seal | seal |
| drop | (abandon/mask/page_number tùy chọn) |

**Pred group → OmniDocBench `category_type`** (eval step-2/step-3 — IoU match):
| group / nhãn V2 | OmniDocBench category | Ghi chú eval |
|---|---|---|
| text | text_block, title, header, footer, page_number, abandon, reference, *_caption, code_txt | gộp title→text khi chấm group; tách khi chấm nhãn mịn |
| table | table | TEDS per-region |
| formula | equation_isolated, equation_semantic | Edit_dist/CDM per-region |
| chart | figure (+ chart_mask hiếm) | **GT chart hạn chế → gap** |
| seal | (không có) | **không có GT → đo set riêng** |

> 2 taxonomy lệch nhau; bảng này là **ánh xạ eval**, phải chốt bằng số liệu thực khi cài model (Risk #2, #3 trong plan).

## 6. Per-step eval harness (`scripts/eval_steps.py` — mới, trong hybrid/)

Không sửa `eval/` chung (Rule 2). Đọc `eval/OmniDocBench_data/OmniDocBench.json` + artifact trace.

| Script/mode | Đọc | Chấm |
|---|---|---|
| `--step layout` | `regions.json` ↔ GT `layout_dets[poly,category]` | mAP@IoU, P/R per group |
| `--step text` | `blocks_raw.json` (text) ↔ GT `text` vùng matched | CER / Edit_dist per-region, agg |
| `--step table` | blocks (html) ↔ GT table `text`(html) | TEDS per-region |
| `--step formula` | blocks (latex) ↔ GT equation `text` | Edit_dist per-region |
| `--step order` | order.json ↔ GT `order` | reading_order Edit_dist |
| `--step e2e` | markdown cuối | gọi harness `eval/` hiện có (so V1) |
| `--oracle-crop` | dùng GT poly thay vì predicted | **cô lập lỗi handler khỏi lỗi layout** (Risk #5) |

**Oracle-crop** là kỹ thuật then chốt: chấm handler trên crop từ **GT bbox** → biết handler giỏi cỡ nào khi layout hoàn hảo; so với predicted-crop → phần chênh là do layout sai. Tách bạch hai nguồn lỗi.

## 7. Cấu trúc code (tiến hóa `hybrid/src/idp/` tại chỗ — D3)

```
src/idp/
  schemas.py            # + Region, RegionGroup, RegionLabel, LayoutResult
  pipeline.py           # V1 (giữ nguyên)
  pipeline_v2.py        # ★ mới — orchestrator V2
  ingest/loader.py      # giữ nguyên
  preprocess/           # ★ S1: deskew, orient, quality
    base.py  opencv_pre.py
  layout/               # ★ S2
    base.py  ppdoclayout.py
  extract/
    base.py             # ParseEngine (giữ — dùng cho handler engine bên dưới)
    tier0_direct.py     # V1 (giữ) — TextHandler PDF số tái dùng logic
    tier_b_lmstudio_vlm.py  # V1 (giữ) — Formula/Chart/Seal handler tái dùng client
    handlers/           # ★ S3
      base.py  registry.py
      text.py  table.py  formula.py  chart.py  seal.py
  reading_order/        # ★ S4
    base.py  xycut.py
  serialize/
    markdown.py json.py docx.py   # markdown giữ; +json +docx(stub)
  validate/gate.py      # stub (giữ)
scripts/
  eval_steps.py         # ★ per-step eval
  run_v2.py             # ★ batch V2 → predictions (song song run_omnidocbench.py)
```

Reuse tối đa: `loader`, `tier0_direct` (→ TextHandler PDF số), `tier_b_lmstudio_vlm` client (→ VLM handlers), `markdown` serializer, `batch.py` runner.

### 7.1. Môi trường (D7)
- Module paddle (layout PP-DocLayout, table PP-Structure, OCR PP-OCRv5) chạy trong **conda env `ocr-worker`** đã dựng cho `traditional/` (paddle CPU sẵn — [[traditional-ocr-solution]]), chỉ bổ sung **PP-DocLayout_plus-L**. Ép `use_gpu=False` ([[blackwell-paddle-gpu-broken]]).
- VLM handler (formula/chart/seal) gọi **LM Studio qua HTTP** → không phụ thuộc env paddle; có thể chạy từ env uv Py3.13 của hybrid hoặc cùng env.
- **Cần chốt khi vào code**: hai nhóm engine (paddle CPU vs uv/httpx) chạy chung 1 process hay tách worker? Đề xuất: 1 process trong `ocr-worker` (đã có httpx được; đơn giản hoá), đo lại nếu xung đột dependency.

## 8. So sánh V1 ↔ V2 (mục tiêu nghiệm thu)

| Tiêu chí | V1 (end2end VLM) | V2 (modular) — kỳ vọng |
|---|---|---|
| Truy vết per-step | ❌ hộp đen | ✅ regions/blocks/order dump + eval riêng |
| Grounding (bbox) | ❌ no bbox | ✅ bbox mức vùng mọi nhánh |
| Table TEDS | 0.188 | ↑ (PP-Structure deterministic) |
| Text Edit_dist | 0.467 | ↑ ở đa cột (reading-order tách riêng) |
| Latency/img | 28.7s (1 VLM call) | ? (layout CPU + nhiều call — **đo, Risk #1/#6**) |
| Quy lỗi | không | ✅ oracle-crop tách lỗi layout vs handler |

## 10. Per-page trace bundle & visualization (★ R9 — ưu tiên dựng sớm)

Mỗi trang sinh **một folder kết quả độc lập**, mỗi step "rơi" artifact vào sub-folder của nó. Mục tiêu: người đọc mở 1 folder (hoặc `index.html`) là **thấy rõ từng bước xử lý + kết quả** mà không cần đọc code.

### 10.1. Cấu trúc folder mỗi trang
```
results/v2_runs/<YYYY-MM-DD_HHMM>_<run_name>/
  index.html                         # tổng hợp cả run: lưới thumbnail mọi trang, link vào từng trang
  run_meta.json                      # config engine, version, danh sách ảnh, tổng latency
  <page_stem>/                       # vd page1/ , PPT_1001115_..._page_003/
    00_input.jpg                     # ảnh gốc (provenance)
    01_preprocess/
      preprocess.json                # {angle_deg, orientation, quality_score, steps:[deskew,orient,...]}
      deskewed.jpg                   # ảnh sau preprocess
      before_after.jpg               # ghép cạnh nhau (trực quan deskew/orient)
    02_layout/
      regions.json                   # [{region_id,label,group,bbox:[x0,y0,x1,y1]|poly,score}]
      overlay.jpg                    # ★ ảnh + bbox MÀU theo group + nhãn + region_id + score
      crops/                         # cắt từng vùng: r00_text.jpg, r07_table.jpg, ...
    03_handlers/
      blocks_raw.json                # region_id -> {type,text|html|latex,engine,latency_s,confidence}
      text/    r00.txt r03.txt ...   # text OCR mỗi vùng
      table/   r07.html r07.png      # HTML + ảnh render bảng (nếu render được)
      formula/ r09.tex r09.png       # LaTeX + ảnh render công thức (nếu render được)
      chart/   r11.md                # mô tả/bảng từ chart
      seal/    r12.txt               # text con dấu / cờ phát hiện
      overlay_ocr.jpg                # ★ ảnh + đè text đã nhận đúng vùng (soi OCR sai ở đâu)
    04_reading_order/
      order.json                     # thứ tự region_id sau sắp xếp
      order_overlay.jpg              # ★ ảnh + số thứ tự trong mỗi vùng + mũi tên nối luồng đọc
    05_output/
      page.md                        # markdown cuối (đi vào OmniDocBench)
      page.json                      # DocumentResult (Block[] + bbox)
    page_index.html                  # ★ trang HTML 1-page: xếp 5 step cạnh nhau, ảnh + bảng dữ liệu
    page_trace.json                  # tổng hợp latency + đếm region theo group + warning mỗi step
```

### 10.2. Quy ước hình ảnh (đọc bằng mắt)
- **`02_layout/overlay.jpg`**: vẽ bbox lên ảnh gốc, **màu theo group** — text=lam, table=lục, formula=đỏ, chart=cam, seal=tím, drop=xám nhạt. Mỗi box ghi `#<region_id> <label> <score>`. Đây là ảnh quan trọng nhất để verify layout detection.
- **`03_handlers/overlay_ocr.jpg`**: đè text nhận được (rút gọn) vào góc mỗi vùng → nhìn ra vùng nào OCR sai/thiếu.
- **`04_reading_order/order_overlay.jpg`**: số thứ tự đọc lớn ở tâm mỗi vùng + mũi tên nối 1→2→3 → kiểm tra reading order đa cột.
- **`before_after.jpg`**: 2 ảnh cạnh nhau minh họa preprocessing đã làm gì.
- Bảng render (`r07.png`, `r09.png`) tùy chọn (cần lib render HTML/LaTeX) — không bắt buộc M2; có thì trực quan hơn.

### 10.3. `page_index.html` (deliverable "thấy rõ nhất")
Một file HTML tĩnh, **self-contained** (ảnh nhúng dạng đường dẫn tương đối), bố cục dọc theo 5 step:
```
[Input] → [S1 Preprocess: before_after + bảng angle/orient/quality]
        → [S2 Layout: overlay.jpg + bảng regions(label,group,score)]
        → [S3 Handlers: overlay_ocr + accordion text/html/latex từng region]
        → [S4 Reading order: order_overlay + danh sách thứ tự]
        → [S5 Output: render markdown cuối]
Mỗi step kèm latency + warning.
```
Sinh bằng template string thuần (không thêm framework). `run/index.html` = lưới thumbnail link tới từng `page_index.html`.

### 10.4. Module trace (`trace/bundle.py`)
```python
class TraceBundle:
    def __init__(self, run_dir: Path, page_stem: str, enabled: bool = True): ...
    def save_input(self, image): ...
    def step(self, name: str) -> "StepWriter":      # tạo sub-folder NN_<name>/
        ...
    # StepWriter: .json(name,obj) .image(name,arr) .text(path,str) .overlay(img,boxes,...)
    def finalize(self): ...                          # ghi page_index.html + page_trace.json
```
- **Tách bạch khỏi logic xử lý**: pipeline gọi `bundle.step("layout").overlay(...)`; tắt bằng `enabled=False` (chế độ chạy nhanh/eval full không cần ảnh).
- Vẽ bbox/overlay bằng OpenCV/Pillow (đã có Pillow). Không thêm dependency nặng.

> Trace bundle **dùng chung** cho cả sample-first (mục 11) và OmniDocBench: khi chạy OmniDocBench có thể bật bundle cho 1 ít ảnh để debug, tắt cho full run (chỉ cần `.md`).

## 11. Sample-first test workflow (R10)

Hai pha, **pha 1 trước pha 2**:

### Pha 1 — `../eval/sample/` (9 ảnh chụp thật, KHÔNG GT) → QA trực quan
- Lệnh dự kiến: `uv run python scripts/run_v2.py --images ../eval/sample --trace --run-name sample-visual`.
- Sinh `results/v2_runs/<ts>_sample-visual/` với 9 folder trang + `index.html`.
- **Nghiệm thu = soi mắt**: layout bbox đúng cột/vùng? deskew thẳng? table tách đúng? reading order 2 cột đúng luồng? Không có điểm số — đây là cổng "pipeline có hợp lý không" trước khi tốn công chấm.
- 9 ảnh này (ảnh chụp giấy, nghiêng/bóng/đa cột/công thức/chữ dọc) cố ý khó → ép preprocessing + layout + reading order lộ điểm yếu sớm.

### Pha 2 — OmniDocBench (như bản cũ) → chấm số
- Chỉ chạy khi pha 1 nhìn ổn.
- `sample_100` (có GT, stratified 10 nguồn) trước: vừa **end-to-end** (so V1 trên cùng 100 ảnh, tái dùng `eval_run.py`) vừa **per-step** (`eval_steps.py` mục 6, dùng GT `category_type/poly/order/text`).
- Rồi **full 1651** như V1 → ghi số vào Agent Index, so V1↔V2.

> Khác biệt then chốt: `eval/sample/` cho **chất lượng trực quan** (không GT), `sample_100`/full cho **số đo** (có GT). R9 trace bundle phục vụ pha 1; mục 6 eval harness phục vụ pha 2.

## 12. Việc cập nhật tài liệu khi vào code (Rule 3/5)
- `AGENT.md`: thêm mục "Kiến trúc V2" (method, module, cách chạy `run_v2.py`/`eval_steps.py`); cập nhật techstack (PP-DocLayout, PP-Structure, PP-OCRv5).
- `CHANGELOG.md`: entry `[hybrid]` MINOR khi V2-M0 (schema mở rộng = năng lực mới).
- `implementation-plan.md`: thêm milestone V2-M0…M5.
- Agent Index (`../CLAUDE.md`): cập nhật khi V2 có số đo.
