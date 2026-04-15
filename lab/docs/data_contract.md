# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` (export từ hệ nguồn KB/policy) | Batch export (CSV) → ingest file | Duplicate dòng; `doc_id` lạ; `effective_date` thiếu/không ISO; conflict version (HR 10 vs 12 ngày); chunk refund stale (14 vs 7 ngày) | `raw_records`, `cleaned_records`, `quarantine_records`; alert nếu `quarantine_records/raw_records` tăng đột biến hoặc expectation `refund_no_stale_14d_window` FAIL |
| `data/docs/*.txt` (canonical policy docs) | Source-of-truth nội bộ (file) → dùng để đối chiếu version khi cần | Canonical cập nhật nhưng export raw chưa cập nhật; mismatch `doc_id`; drift nội dung (stale chunk vẫn xuất hiện) | Retrieval eval `hits_forbidden`/`topk_has_stale`; alert nếu chunk chứa marker stale (vd “14 ngày làm việc”, “10 ngày phép năm”) xuất hiện trong top-k |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | … |
| doc_id | string | Có | … |
| chunk_text | string | Có | … |
| effective_date | date | Có | … |
| exported_at | datetime | Có | … |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?
