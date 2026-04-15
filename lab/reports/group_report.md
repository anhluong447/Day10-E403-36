# Bao Cao Nhom — Lab Day 10: Data Pipeline & Data Observability

**Ten nhom:** E403-36  
**Thanh vien:**
| Ten                | Vai tro (Day 10)                 | Email                      |
| ------------------ | -------------------------------- | -------------------------- |
| Phạm Quốc Vương    | Ingest & schema                  | phamvuong2622004@gmail.com |
| Nguyễn Huy Tú      | Clean + validate + embed         | nguyenhuytu724@gmail.com   |
| Nguyễn Thành Trung | Inject corruption & before/after | trung.nt202717@gmail.com   |
| Lương Hoàng Anh    | Monitoring + docs + report       | hitomisaichi@gmail.com     |

**Ngay nop:** 2026-04-15  
**Repo:** Day10-E403-36  
**Do dai khuyen nghi:** 600-1000 tu

---

## 1. Pipeline tong quan

Nguon raw la file `data/raw/policy_export_dirty.csv` — mo phong export batch tu he thong KB/policy noi bo. File chua 13 row voi nhieu loi co chu dich: duplicate, doc_id la, BOM prefix, ngay khong ISO, conflict version HR (10 vs 12 ngay phep), chunk refund stale (14 vs 7 ngay), chunk qua dai, va chunk co ngay tuong lai xa.

Pipeline chay qua 5 buoc: Ingest (doc CSV, dem raw_records) -> Transform/Clean (10 rules: allowlist, normalize date, quarantine HR cu, fix refund, strip BOM, quarantine future date, quarantine chunk dai, dedupe) -> Validate (8 expectations, halt neu severity=halt fail) -> Embed (Chroma upsert theo chunk_id + prune id cu) -> Publish (ghi manifest JSON + freshness check).

`run_id` duoc ghi trong dong dau tien cua log (`artifacts/logs/run_<run_id>.log`) va trong manifest JSON.

**Lenh chay mot dong (copy tu README thuc te cua nhom):**

```bash
python etl_pipeline.py run --run-id sprint4 && python eval_retrieval.py --out artifacts/eval/before_after_eval.csv
```

---

## 2. Cleaning & expectation

Baseline da co 7 rules (R1-R7) va 6 expectations (E1-E6). Nhom them **3 rule moi** (R8, R9, R10) va **2 expectation moi** (E7, E8).

### 2a. Bang metric_impact (bat buoc — chong trivial)

| Rule / Expectation moi (ten ngan) | Truoc (so lieu) | Sau / khi inject (so lieu) | Chung cu (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| **Rule 8 – strip_bom_and_control_chars** | sprint1: raw=10, cleaned=6, quar=4 (row 11 BOM chua co) | sprint2: raw=13, cleaned=7, quar=6 — row 11 (`\ufeffpolicy_refund_v4`) duoc giai cuu vao cleaned thay vi bi quarantine unknown_doc_id | `artifacts/cleaned/cleaned_sprint2.csv` row 7 (doc_id=policy_refund_v4, chunk co "BOM prefix") |
| **Rule 9 – quarantine_future_effective_date** | sprint1: khong co row future date | sprint2: row 12 (effective_date=2027-06-01, days_ahead=416) -> `reason=future_effective_date` trong quarantine | `artifacts/quarantine/quarantine_sprint2.csv`: `days_ahead=416` |
| **Rule 10 – quarantine_chunk_text_too_long** | sprint1: khong co row qua dai | sprint2: row 13 (2097 chars > 2000) -> `reason=chunk_text_too_long, length=2097` trong quarantine | `artifacts/quarantine/quarantine_sprint2.csv`: `length=2097` |
| **E7 – all_allowed_doc_ids_represented (warn)** | baseline: khong kiem tra coverage per doc_id | sprint2: `missing_doc_ids=[]` PASS | `artifacts/logs/run_sprint2.log` |
| **E8 – no_unexpected_clean_marker (halt)** | baseline: khong kiem tra marker artifact | sprint2: `unexpected_marker_count=0` PASS | `artifacts/logs/run_sprint2.log` |

**Tong ket Sprint 2:** `raw_records=13`, `cleaned_records=7`, `quarantine_records=6`

**Vi du 1 lan expectation fail (Sprint 3 inject) va cach xu ly:**

Khi chay `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`, E3 (`refund_no_stale_14d_window`) FAIL voi `violations=1` vi chunk "14 ngay lam viec" khong duoc fix. Pipeline halt nhung bi bypass boi `--skip-validate`. Ket qua: retrieval `q_refund_window` tra ve `hits_forbidden=yes`.

---

## 3. Before / after anh huong retrieval

### Kich ban inject (Sprint 3)

Chay pipeline voi 2 flag de co tinh embed du lieu xau:
```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
```

Sau do chay lai pipeline chuan:
```bash
python etl_pipeline.py run --run-id sprint3-clean
python eval_retrieval.py --out artifacts/eval/after_clean_fix.csv
```

### Ket qua dinh luong

| Cau hoi | Metric | Inject-bad | Sprint3-clean | Nhan xet |
|---------|--------|-----------|---------------|----------|
| q_refund_window | hits_forbidden | **yes** | **no** | Chunk stale "14 ngay" xuat hien trong top-k khi inject; bi loai sau fix + prune |
| q_refund_window | contains_expected | yes | yes | Ca hai co "7 ngay" trong top-k, nhung inject con co ca "14 ngay" |
| q_leave_version | hits_forbidden | no | no | Rule 4 (HR stale) hoat dong doc lap, bao ve ca 2 scenario |
| q_leave_version | top1_doc_expected | yes | yes | Top-1 la hr_leave_policy ca 2 lan |
| q_p1_sla | contains_expected | yes | yes | Khong bi anh huong boi inject |
| q_lockout | contains_expected | yes | yes | Khong bi anh huong boi inject |

**Diem then chot:** `embed_prune_removed=1` trong log sprint3-clean — chung to pipeline xoa chunk stale (co "14 ngay lam viec") khoi vector store khi rerun. Day la co che "publish boundary" dam bao agent chi doc du lieu cleaned moi nhat.

---

## 4. Freshness & monitoring

**SLA duoc chon:** 24 gio (mac dinh trong `.env` va `data_contract.yaml`).

**Ket qua freshness check (run sprint3-clean):**
```
FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 121.2, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

**Y nghia:**
- **PASS** (age <= 24h): Du lieu fresh, pipeline hoat dong binh thuong.
- **WARN**: Manifest ton tai nhung thieu timestamp — kiem tra format.
- **FAIL** (age > 24h): Du lieu stale. Trong truong hop nay, export tu 2026-04-10 nhung chay pipeline ngay 2026-04-15 (~5 ngay truoc) -> FAIL. Trong production can tu dong re-export de dam bao freshness.

Chi tiet giai thich trong `docs/runbook.md`.

---

## 5. Lien he Day 09

Pipeline Day 10 lam moi corpus cho retrieval cua multi-agent Day 09. Sau khi embed thanh cong, Chroma collection `day10_kb` chua cleaned chunks san sang cho agent truy van. Khac biet chinh: Day 09 embed truc tiep tu file text; Day 10 qua ETL pipeline co cleaning + validation + quarantine truoc khi embed — dam bao agent khong doc du lieu stale hoac corrupt.

---

## 6. Rui ro con lai & viec chua lam

- Freshness FAIL vi du lieu mau co `exported_at` co dinh — trong thuc te can tu dong re-export.
- Chua co alerting tu dong (Slack/email) khi expectation fail hoac freshness fail.
- Inject chi test 1 scenario (refund stale). Co the mo rong: inject duplicate them, sai doc_id moi, chunk co marker trong doc khong phai refund.
- `chunk_id` phu thuoc `seq` — neu thu tu row thay doi, id thay doi va prune xoa het. Can xem xet content-only hash.
- Chua co rollback mechanism — neu pipeline embed du lieu loi, can xoa collection va rebuild.
