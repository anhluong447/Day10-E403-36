# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| ___ | Ingestion / Raw Owner | ___ |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

_________________

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

_________________

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| **Rule 8 – strip_bom_and_control_chars** | sprint1: raw=10, cleaned=6, quar=4 (row 11 BOM chưa có) | sprint2: raw=13, cleaned=7, quar=6 — row 11 (`\ufeffpolicy_refund_v4`) được **giải cứu** vào cleaned thay vì bị quarantine unknown_doc_id | `artifacts/cleaned/cleaned_sprint2.csv` row 7 (doc_id=policy_refund_v4, chunk có "BOM prefix") |
| **Rule 9 – quarantine_future_effective_date** | sprint1: không có row future date | sprint2: row 12 (effective_date=2027-06-01, days_ahead=416) → `reason=future_effective_date` trong quarantine | `artifacts/quarantine/quarantine_sprint2.csv` dòng 5: `days_ahead=416` |
| **Rule 10 – quarantine_chunk_text_too_long** | sprint1: không có row quá dài | sprint2: row 13 (2097 chars > 2000) → `reason=chunk_text_too_long, length=2097` trong quarantine | `artifacts/quarantine/quarantine_sprint2.csv` dòng 6: `length=2097` |
| **E7 – all_allowed_doc_ids_represented (warn)** | baseline: không kiểm tra coverage per doc_id | sprint2 normal run: `missing_doc_ids=[]` WARN PASS; inject scenario (bỏ sla_p1_2026) → `missing_doc_ids=['sla_p1_2026']` WARN | `artifacts/logs/run_sprint2.log`: `expectation[all_allowed_doc_ids_represented] OK (warn) :: missing_doc_ids=[]` |
| **E8 – no_unexpected_clean_marker (halt)** | baseline: không kiểm tra marker artifact | sprint2 normal run: `unexpected_marker_count=0` HALT PASS; inject (marker trong hr_leave_policy) → HALT FAIL | `artifacts/logs/run_sprint2.log`: `expectation[no_unexpected_clean_marker] OK (halt) :: unexpected_marker_count=0` |

**Tổng kết Sprint 2:** `raw_records=13`, `cleaned_records=7`, `quarantine_records=6`  
(+3 raw inject, +1 cleaned từ BOM fix, +2 quarantine từ Rule 9 & 10; run_id=sprint2)

**Rule chính (baseline + mở rộng):**

- **R1** allowlist doc_id (halt): loại unknown_doc_id
- **R2** normalize effective_date (halt): DD/MM/YYYY → ISO; quarantine nếu không parse
- **R3** stale HR effective_date < 2026-01-01 (halt): quarantine bản HR cũ
- **R4** missing chunk_text hoặc missing date (halt): quarantine empty required fields
- **R5** deduplicate chunk_text (warn): giữ bản đầu, quarantine duplicate
- **R6** fix stale refund 14→7 ngày (fix): policy_refund_v4 chứa "14 ngày làm việc" → sửa
- **R8 (mới)** strip BOM & control chars (fix): loại `\ufeff` và control chars trước mọi rule
- **R9 (mới)** future effective_date > 180 ngày (halt): quarantine policy chưa có hiệu lực
- **R10 (mới)** chunk_text > 2000 chars (halt): quarantine dấu hiệu merge lỗi

**Ví dụ 1 lần expectation fail (Sprint 3 inject) và cách xử lý:**

Khi chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`, E3 (`refund_no_stale_14d_window`) FAIL với `violations=1` vì chunk "14 ngày làm việc" không được fix. Pipeline exit 2 (halt) nhưng bị bypass bởi `--skip-validate`. Kết quả: retrieval `q_refund_window` trả về text có "14 ngày" → `hits_forbidden=true`.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

_________________

**Kết quả định lượng (từ CSV / bảng):**

_________________

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

_________________

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- …
