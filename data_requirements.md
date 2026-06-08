# Báo cáo Phân tích Nghiệp vụ: Danh mục Tài liệu cho Kiến trúc IDP Ngân hàng

> **Tài liệu**: Business Analysis – Document Catalog for Intelligent Document Processing (IDP)
> **Phạm vi**: Định nghĩa các loại thông tin đầu vào, đặc tả Input/Output và kỳ vọng chất lượng (Quality Expectation) cho từng nhóm tài liệu.
> **Đối tượng đọc**: Product Owner, Data/ML Engineer, Vendor đối tác OCR/IDP, Risk & Compliance.
> **Phiên bản**: 1.0

---

## 1. Mục đích & Phạm vi

Báo cáo này chuẩn hóa **danh mục tài liệu** mà ngân hàng có thể đưa vào pipeline IDP để số hóa và trích xuất dữ liệu tự động, phục vụ các luồng nghiệp vụ: mở tài khoản/KYC, cấp tín dụng, thanh toán & giao dịch, tài trợ thương mại (trade finance), quản lý tài sản đảm bảo, và tuân thủ (compliance).

Với mỗi nhóm tài liệu, báo cáo mô tả:

- **Input** — định dạng, nguồn phát sinh, chất lượng đầu vào dự kiến.
- **Output** — schema dữ liệu trả ra (field cần trích), kèm metadata bắt buộc (confidence, bounding box, document type).
- **Quality Expectation** — ngưỡng độ chính xác theo từng nhóm field, tỷ lệ xử lý tự động (STP), và quy tắc fallback sang người review.

Nguyên tắc xuyên suốt: **mọi field có ý nghĩa tài chính/định danh đều phải kèm confidence score + tọa độ nguồn (provenance)**, vì đây là yêu cầu bắt buộc cho audit và human-in-the-loop trong môi trường ngân hàng.

---

## 2. Kiến trúc IDP tham chiếu (các stage trong pipeline)

Tài liệu được xử lý qua chuỗi stage chuẩn — không chỉ riêng extraction:

| Stage | Mục đích | Output trung gian |
|---|---|---|
| **1. Ingestion & Pre-processing** | Chuẩn hóa định dạng, deskew, xoay, khử nhiễu, tách trang | Ảnh/PDF đã chuẩn hóa |
| **2. Classification** | Nhận diện loại tài liệu (CCCD? sao kê? hợp đồng?) | `doc_type` + confidence |
| **3. Splitting** | Tách 1 file nhiều tài liệu, ghép bảng tràn trang | Danh sách document con |
| **4. Extraction** | Trích text/table/field/entity theo capability | Structured data thô |
| **5. Validation** | Kiểm tra logic nghiệp vụ, đối chiếu chéo, chống hallucination | Data đã validate + flag lỗi |
| **6. PII Handling** | Phát hiện & che/masking dữ liệu nhạy cảm | Data + bản đã redact |
| **7. Human-in-the-loop** | Route field confidence thấp cho người review | Data đã xác nhận |

Danh mục ở Mục 3 tập trung vào stage **Classification → Extraction → Validation**, nhưng đặc tả Output (Mục 5) áp dụng cho toàn pipeline.

---

## 3. Danh mục Tài liệu theo Nghiệp vụ

### 3.1. Nhóm Định danh & KYC / Onboarding

| Loại tài liệu | Capability chính | Output fields tiêu biểu |
|---|---|---|
| CCCD / CMND (mặt trước & sau) | NER + Form K-V + chip/MRZ + ảnh chân dung | `id_number, full_name, dob, gender, nationality, place_of_origin, place_of_residence, issue_date, expiry_date, issuing_authority` |
| Hộ chiếu | MRZ parsing + NER | `passport_no, surname, given_name, dob, nationality, mrz_line1, mrz_line2, expiry_date` |
| Giấy phép lái xe | Form K-V | `license_no, class, full_name, dob, valid_until` |
| Đăng ký kinh doanh / GPKD (KH doanh nghiệp) | NER + table | `tax_code, company_name, legal_rep, address, business_lines[], charter_capital, registration_date` |
| Chứng từ chứng minh địa chỉ (hóa đơn điện/nước) | K-V + NER | `holder_name, address, billing_period, issuer` |
| Mẫu chữ ký / Signature card | Signature detection + K-V | `account_holder, signature_present(bool), signature_bbox[]` |

**Input**: Ảnh chụp điện thoại (đa số), scan, hoặc file PDF từ app. Chất lượng dao động lớn — nghiêng, lóa sáng, bóng tay, mất góc. Đa ngôn ngữ (tiếng Việt có dấu là bắt buộc).

**Output**: JSON theo schema cố định cho từng loại giấy tờ, kèm `doc_type`, `confidence` từng field, `bbox` từng field, và cờ `is_authentic_layout` (phát hiện bố cục giả mạo cơ bản).

**Quality Expectation**:
- `id_number`, `passport_no`, `tax_code`: **≥ 99.5%** field accuracy — đây là khóa định danh, sai một ký tự là sai toàn bộ hồ sơ. Bắt buộc check digit/MRZ checksum nếu có.
- Tên, ngày tháng: **≥ 98%**.
- Địa chỉ (free text tiếng Việt): **≥ 95%**.
- Mọi field < ngưỡng confidence → route human review, **không** auto-approve hồ sơ KYC dưới ngưỡng.

---

### 3.2. Nhóm Tín dụng / Lending

| Loại tài liệu | Capability chính | Output fields tiêu biểu |
|---|---|---|
| Đơn đề nghị vay vốn | Form K-V + checkbox | `applicant, amount_requested, tenor, purpose, product_code` |
| Sao kê lương / Bảng lương | Table + K-V | `employee, employer, period, gross, net, allowances[]` |
| Hợp đồng lao động | NER + relationship | `employer, employee, position, salary, contract_type, start_date` |
| Sao kê tài khoản ngân hàng | Table (đa trang) + cross-page merge | `account_no, period, opening_balance, closing_balance, transactions[]` |
| Báo cáo tài chính doanh nghiệp | Table phức tạp + hierarchy + relationship | `balance_sheet{}, income_statement{}, cash_flow{}, period, audited(bool)` |
| Hóa đơn / Chứng từ chứng minh thu nhập | Domain field + table | `invoice_no, date, vendor, line_items[], total, vat` |

**Input**: Hỗn hợp — PDF số (sao kê e-banking, BCTC), scan (hợp đồng có chữ ký + con dấu), ảnh chụp. Sao kê và BCTC thường **đa trang, bảng tràn trang**, cần ghép.

**Output**: JSON theo schema, đặc biệt với `transactions[]` và `line_items[]` phải giữ nguyên thứ tự và mapping subtotal → total (relationship extraction). BCTC cần giữ cấu trúc lồng nhau (mục cha–con).

**Quality Expectation**:
- Số tiền (`amount`, `balance`, `total`): **≥ 99%** field accuracy, **bắt buộc** validation logic: `Σ line_items + vat = total`, `opening + Σ transactions = closing`. Sai lệch → flag, không tính tự động.
- Cấu trúc bảng (table structure F1): **≥ 95%** — merge cell, spanning phải đúng.
- Free text (mục đích vay, ghi chú): **≥ 90%** là chấp nhận được.
- STP target cho sao kê chuẩn định dạng cố định: **70–85%**; BCTC scan phức tạp: **40–55%** (phần còn lại review).

---

### 3.3. Nhóm Thanh toán & Giao dịch

| Loại tài liệu | Capability chính | Output fields tiêu biểu |
|---|---|---|
| Ủy nhiệm chi (UNC) | Form K-V + handwriting | `payer, payer_account, beneficiary, beneficiary_account, amount, amount_in_words, content, date` |
| Séc (cheque) | Handwriting + MICR + amount-in-words | `cheque_no, payee, amount_figures, amount_words, date, drawer_signature_present` |
| Điện SWIFT / MT messages | Layout text + field tag parsing | `mt_type, ref, amount, currency, ordering_customer, beneficiary` |
| Hóa đơn GTGT (giấy & điện tử) | Domain field + barcode/QR | `invoice_no, serial, tax_code_seller, tax_code_buyer, items[], vat_rate, total` |
| Phiếu thu / Phiếu chi | Form K-V | `voucher_no, date, payer/payee, amount, reason` |

**Input**: UNC và séc thường có **chữ viết tay** + dấu + chữ ký → khoảng cách độ chính xác lớn so với text in, cần tách xử lý riêng. Hóa đơn điện tử có QR/barcode nhúng. SWIFT là text thuần có cấu trúc tag.

**Output**: JSON. Với séc/UNC bắt buộc đối chiếu **số tiền bằng số vs bằng chữ** (amount_figures vs amount_words) — chênh lệch là red flag.

**Quality Expectation**:
- Số tài khoản, số tiền: **≥ 99.5%** với chữ in; với chữ viết tay đặt ngưỡng thực tế **≥ 92–95%** và **bắt buộc** human review nếu hai cách viết số tiền không khớp.
- QR/barcode đọc đúng: **≥ 99.9%** (đây là dữ liệu cấu trúc, gần như không được sai).
- Mọi chứng từ giao dịch tiền: chính sách **maker–checker** — không auto-post bút toán nếu bất kỳ field tiền nào dưới ngưỡng confidence.

---

### 3.4. Nhóm Tài trợ Thương mại (Trade Finance)

| Loại tài liệu | Capability chính | Output fields tiêu biểu |
|---|---|---|
| Thư tín dụng (L/C) | Layout text + relationship | `lc_number, applicant, beneficiary, amount, expiry, terms[]` |
| Vận đơn (Bill of Lading) | Form K-V + table | `bl_no, shipper, consignee, vessel, port_loading, port_discharge, goods[]` |
| Hóa đơn thương mại (Commercial Invoice) | Table + domain field | `invoice_no, seller, buyer, incoterm, line_items[], total` |
| Packing List | Table | `package_no, description, qty, net_weight, gross_weight` |
| Tờ khai hải quan | Form K-V + table | `declaration_no, hs_code[], value, duty` |

**Input**: Đa dạng định dạng, đa ngôn ngữ (Anh/Việt/đôi khi CJK), bố cục không chuẩn hóa giữa các đối tác. Chất lượng scan trung bình–thấp (fax, photocopy nhiều lần).

**Output**: JSON, nhấn mạnh **relationship extraction** để đối chiếu chéo bộ chứng từ (L/C vs Invoice vs B/L) phục vụ kiểm tra discrepancy — đây là giá trị cốt lõi của IDP trong trade finance.

**Quality Expectation**:
- Field định lượng (amount, quantity, weight, HS code): **≥ 98%**.
- Mục tiêu chính không phải accuracy đơn lẻ mà **discrepancy detection recall ≥ 95%** — không được bỏ sót sai lệch giữa các chứng từ.
- STP thấp (**30–50%**) là bình thường; trọng tâm là giảm thời gian kiểm tra của chuyên viên.

---

### 3.5. Nhóm Tài sản Đảm bảo

| Loại tài liệu | Capability chính | Output fields tiêu biểu |
|---|---|---|
| Sổ đỏ / Sổ hồng (GCN QSDĐ) | NER + table + stamp/seal | `certificate_no, owner, parcel_no, area, address, land_use_purpose, issue_date` |
| Đăng ký xe ô tô | Form K-V | `plate_no, owner, brand, model, chassis_no, engine_no, first_reg_date` |
| Chứng thư thẩm định giá | Table + K-V | `asset, appraised_value, valuation_date, appraiser` |
| Hợp đồng thế chấp | NER + relationship + signature/seal | `mortgagor, mortgagee, collateral, value, sign_date, notarized(bool)` |

**Input**: Chủ yếu scan/ảnh chụp; sổ đỏ thường có **con dấu, watermark, chữ ký** và bố cục phức tạp. Số seri/số thửa là khóa định danh.

**Output**: JSON kèm `seal_detected(bool)`, `signature_detected(bool)`, `bbox` của dấu/chữ ký — phục vụ xác thực tính hợp lệ pháp lý của tài sản.

**Quality Expectation**:
- Số GCN, số chassis/engine, biển số: **≥ 99%** (khóa định danh tài sản).
- Diện tích, giá trị thẩm định: **≥ 98%** + validation đơn vị (m², VND).
- Phát hiện dấu/chữ ký: **Recall ≥ 98%** (thà báo nhầm còn hơn bỏ sót hồ sơ chưa ký/đóng dấu).

---

### 3.6. Nhóm Pháp lý & Tuân thủ (Compliance)

| Loại tài liệu | Capability chính | Output fields tiêu biểu |
|---|---|---|
| Hợp đồng tín dụng | NER + relationship + clause hierarchy | `parties[], principal, interest_rate, tenor, clauses{}, sign_date` |
| Giấy ủy quyền | NER + seal | `principal, attorney, scope, valid_period` |
| Văn bản pháp lý / Quyết định tòa | Layout text + hierarchy | `doc_no, issuer, subject, effective_date` |
| Tài liệu AML/Sanctions | NER + classification | `entity_names[], match_flag, risk_category` |

**Input**: PDF số hoặc scan, văn bản dài, điều khoản **lồng nhau nhiều cấp** (Điều → Khoản → Điểm).

**Output**: JSON giữ cấu trúc cây của điều khoản (list & hierarchy detection), kèm relationship "điều khoản nào áp dụng cho bên nào".

**Quality Expectation**:
- Lãi suất, kỳ hạn, số tiền gốc: **≥ 99%**.
- Trích đúng cấu trúc điều khoản (hierarchy accuracy): **≥ 95%**.
- Đây là nhóm **không khuyến nghị STP cao** — output chủ yếu để hỗ trợ pháp chế đọc nhanh, mọi nội dung ràng buộc pháp lý cần người xác nhận.

---

### 3.7. Nhóm Nội bộ / Vận hành

| Loại tài liệu | Capability chính | Output fields tiêu biểu |
|---|---|---|
| Chứng từ kế toán nội bộ | Table + K-V | `voucher_no, account_code, debit, credit, narrative` |
| Biên bản họp / Tờ trình | Layout text | `title, date, attendees[], decisions[]` |
| Email / Văn thư đến | Raw text + classification | `sender, subject, date, body, category` |

**Input**: Hỗn hợp số và scan, đa phần text in chất lượng tốt.

**Output**: Markdown/plain text + phân loại tự động để định tuyến (routing) tới phòng ban.

**Quality Expectation**: Raw/Layout text **≥ 97%**; phân loại định tuyến **F1 ≥ 0.9**; nhóm này tolerance cao vì rủi ro thấp.

---

## 4. Đặc tả Input chuẩn

| Thuộc tính | Yêu cầu |
|---|---|
| **Định dạng** | PDF (số & scan), JPG/PNG/TIFF, HEIC; multi-page PDF bắt buộc hỗ trợ |
| **Độ phân giải** | Khuyến nghị ≥ 200 DPI (scan); ảnh chụp ≥ 1.500 px cạnh dài |
| **Ngôn ngữ** | Tiếng Việt có dấu (bắt buộc), tiếng Anh; CJK cho trade finance |
| **Chất lượng** | Pipeline phải xử lý được: nghiêng ≤ 15°, lóa sáng nhẹ, fax/photocopy; tự động deskew + denoise |
| **Metadata kèm theo** | `source_channel` (app/branch/email), `upload_timestamp`, `expected_doc_type` (nếu có) |
| **Giới hạn** | Kích thước file, số trang tối đa, mã hóa khi truyền — theo chính sách bảo mật ngân hàng |

---

## 5. Đặc tả Output chuẩn

Mọi tài liệu trả về **một envelope JSON thống nhất**, bất kể loại:

```json
{
  "document_id": "DOC-20260607-000123",
  "doc_type": "bank_statement",
  "doc_type_confidence": 0.985,
  "language": "vi",
  "page_count": 4,
  "processing": {
    "model_version": "idp-core-v2.3",
    "processed_at": "2026-06-07T10:22:31Z",
    "status": "needs_review"          // auto_approved | needs_review | rejected
  },
  "fields": [
    {
      "name": "account_no",
      "value": "0123456789",
      "confidence": 0.997,
      "page": 1,
      "bbox": [0.12, 0.08, 0.34, 0.11],   // provenance: vị trí trên trang
      "validation": "passed"
    },
    {
      "name": "closing_balance",
      "value": "152300000",
      "confidence": 0.91,
      "page": 4,
      "bbox": [0.61, 0.74, 0.82, 0.77],
      "validation": "passed"             // opening + Σtx = closing
    }
  ],
  "tables": [ { "name": "transactions", "rows": [ /* ... */ ] } ],
  "detections": {
    "signature_present": true,
    "seal_present": true,
    "qr_codes": []
  },
  "pii": {
    "detected": ["id_number", "account_no"],
    "redacted_copy_uri": "s3://.../DOC-...-redacted.pdf"
  },
  "warnings": []
}
```

**Bắt buộc với mọi field**: `value`, `confidence` (0–1), `page`, `bbox` (provenance), `validation`. Không field nào được trả về thiếu confidence — đây là điều kiện để cơ chế human-in-the-loop và audit hoạt động.

---

## 6. Khung Chất lượng (Quality Framework)

### 6.1. Bộ chỉ số đánh giá

| Chỉ số | Định nghĩa | Áp dụng cho |
|---|---|---|
| **Field-level Accuracy** | % field trích đúng hoàn toàn | Mọi field cấu trúc |
| **CER / WER** | Character/Word Error Rate | Text thuần, free text |
| **Table TEDS / structure F1** | Độ đúng cấu trúc bảng | Sao kê, BCTC |
| **Classification F1** | Độ đúng phân loại tài liệu | Stage classification |
| **STP Rate** | % hồ sơ xử lý không cần người | Toàn pipeline |
| **Confidence Calibration (ECE)** | Confidence có phản ánh đúng độ chính xác thực không | Chất lượng metadata |
| **Hallucination Rate** | % field bịa không có trên ảnh gốc | Model VLM-based |

### 6.2. Phân tầng confidence & quy tắc định tuyến

| Tầng | Ngưỡng confidence | Hành động |
|---|---|---|
| **Auto-approve** | ≥ 0.95 *và* validation passed | Xử lý tự động |
| **Review** | 0.70 – 0.95 *hoặc* validation cảnh báo | Người kiểm tra field được highlight |
| **Reject/Re-capture** | < 0.70 hoặc ảnh không đọc được | Yêu cầu chụp/scan lại |

> Với field tiền và field định danh (account, ID, amount), **luôn áp ngưỡng cao hơn** và bắt buộc maker–checker, bất kể confidence.

### 6.3. Bảng kỳ vọng chất lượng tổng hợp

| Nhóm field | Accuracy mục tiêu | Ghi chú |
|---|---|---|
| Khóa định danh (ID, account, tax code, số GCN) | ≥ 99.5% | + check digit/checksum |
| Số tiền & số liệu tài chính | ≥ 99% | + validation logic bắt buộc |
| Ngày tháng, tên | ≥ 98% | |
| Cấu trúc bảng | ≥ 95% | merge/spanning đúng |
| Địa chỉ, free text tiếng Việt | ≥ 95% | |
| Chữ viết tay (séc, UNC) | ≥ 92% | bắt buộc đối chiếu chéo |
| QR/Barcode | ≥ 99.9% | |
| Phát hiện dấu/chữ ký | Recall ≥ 98% | ưu tiên không bỏ sót |

---

## 7. Yêu cầu Xuyên suốt (Cross-cutting)

- **PII & Bảo mật**: phát hiện và masking dữ liệu nhạy cảm (CCCD, số tài khoản, ngày sinh); lưu kèm bản redact; tuân thủ quy định bảo vệ dữ liệu cá nhân.
- **Triển khai**: ưu tiên phương án **on-premise/private** cho tài liệu nhạy cảm — tránh route dữ liệu khách hàng qua hạ tầng vendor công cộng; nếu dùng API ngoài phải có thỏa thuận xử lý dữ liệu rõ ràng.
- **Audit trail**: lưu vết model version, thời điểm xử lý, người review, thay đổi giá trị — phục vụ thanh tra.
- **Chống hallucination**: bắt buộc lớp validation đối chiếu output với ảnh gốc; mọi field không gắn được `bbox` nguồn cần bị đánh dấu nghi ngờ.
- **Adaptability**: pipeline học từ correction của người review (few-shot/fine-tune) để cải thiện theo thời gian.

---

## 8. Khuyến nghị triển khai theo giai đoạn

| Giai đoạn | Phạm vi | Lý do ưu tiên |
|---|---|---|
| **Phase 1** | CCCD/KYC + Hóa đơn GTGT + Sao kê | Định dạng tương đối chuẩn, ROI nhanh, volume lớn |
| **Phase 2** | UNC/Séc + BCTC + Tài sản đảm bảo | Phức tạp hơn (handwriting, bảng), giá trị nghiệp vụ cao |
| **Phase 3** | Trade finance + Hợp đồng pháp lý | Quan hệ chứng từ phức tạp, cần relationship extraction trưởng thành |

---

*Hết báo cáo. Phiên bản 1.0 — đề xuất rà soát lại ngưỡng chất lượng sau giai đoạn pilot với dữ liệu thực tế của ngân hàng.*