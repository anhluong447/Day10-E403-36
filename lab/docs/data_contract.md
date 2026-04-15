## 1. Nguon du lieu (source map)

| Nguon | Phuong thuc ingest | Failure mode chinh | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` (export tu he nguon KB/policy) | Batch export (CSV) -> ingest file | Duplicate dong; `doc_id` la; `effective_date` thieu/khong ISO; conflict version (HR 10 vs 12 ngay); chunk refund stale (14 vs 7 ngay); BOM prefix tu Excel; chunk qua dai (merge loi) | `raw_records`, `cleaned_records`, `quarantine_records`; alert neu `quarantine_records/raw_records` tang dot bien hoac expectation `refund_no_stale_14d_window` FAIL |
| `data/docs/*.txt` (canonical policy docs) | Source-of-truth noi bo (file) -> dung de doi chieu version khi can | Canonical cap nhat nhung export raw chua cap nhat; mismatch `doc_id`; drift noi dung (stale chunk van xuat hien) | Retrieval eval `hits_forbidden`/`topk_has_stale`; alert neu chunk chua marker stale (vd "14 ngay lam viec", "10 ngay phep nam") xuat hien trong top-k |

---

## 2. Schema cleaned

| Cot | Kieu | Bat buoc | Ghi chu |
|-----|------|----------|---------|
| chunk_id | string | Co | ID on dinh: `{doc_id}_{seq}_{sha256[:16]}`. Dung lam Chroma document ID de upsert idempotent. |
| doc_id | string | Co | Phai thuoc allowlist (`policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`). Row ngoai allowlist bi quarantine. |
| chunk_text | string | Co | Noi dung chunk sau clean. Min 8 ky tu, max 2000 ky tu. Marker `[cleaned: ...]` chi duoc xuat hien trong `policy_refund_v4`. |
| effective_date | date (YYYY-MM-DD) | Co | Chuan hoa tu nhieu format (ISO, DD/MM/YYYY). Phai < 180 ngay tuong lai so voi exported_at. HR policy phai >= 2026-01-01. |
| exported_at | datetime (ISO 8601) | Co | Thoi diem export tu he nguon. Dung tinh freshness va kiem tra future date. |

---

## 3. Quy tac quarantine vs drop

- **Quarantine (khong drop):** Moi row bi loai deu ghi vao `artifacts/quarantine/quarantine_<run_id>.csv` voi cot `reason` giai thich cu the.
- **Khong co drop:** Pipeline khong xoa vinh vien bat ky record nao. Quarantine la "holding area" de audit va co the merge lai neu can.
- **Ai approve merge lai:** Data owner (Cleaning & Quality Owner) review quarantine CSV. Neu row bi quarantine sai (false positive), sua rule va rerun pipeline.
- **Quarantine reasons hien tai:** `unknown_doc_id`, `missing_effective_date`, `invalid_effective_date_format`, `future_effective_date`, `stale_hr_policy_effective_date`, `missing_chunk_text`, `chunk_text_too_long`, `duplicate_chunk_text`.

---

## 4. Phien ban & canonical

- **Source of truth cho policy refund:** `data/docs/policy_refund_v4.txt` — version 4, cua so hoan tien la **7 ngay lam viec**.
- **Source of truth cho HR leave:** `data/docs/hr_leave_policy.txt` — ban 2026, nhan vien duoi 3 nam kinh nghiem duoc **12 ngay phep nam**.
- **Versioning rule:** `effective_date >= 2026-01-01` cho HR policy. Cac ban cu (2025) bi quarantine voi reason `stale_hr_policy_effective_date`.
- **Dong bo allowlist:** Khi them doc moi, phai cap nhat dong thoi: `cleaning_rules.py` (ALLOWED_DOC_IDS), `expectations.py` (_ALLOWED_DOC_IDS), `data_contract.yaml` (allowed_doc_ids + canonical_sources).
