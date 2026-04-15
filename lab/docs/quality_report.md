# Quality report — Lab Day 10 (nhom)

**run_id (inject):** inject-bad  
**run_id (clean):** sprint3-clean  
**Ngay:** 2026-04-15

---

## 1. Tom tat so lieu

| Chi so | Inject-bad | Sprint3-clean | Ghi chu |
|--------|-----------|---------------|---------|
| raw_records | 13 | 13 | Cung bo du lieu dau vao |
| cleaned_records | 7 | 7 | So luong cleaned giong nhau |
| quarantine_records | 6 | 6 | Cung 6 row bi quarantine |
| Expectation halt? | YES (refund_no_stale_14d_window FAIL) | NO (all pass) | --no-refund-fix giu lai "14 ngay lam viec" |
| skipped_validate | true | false | Inject dung --skip-validate de ep embed du lieu xau |

---

## 2. Before / after retrieval (bat buoc)

> File eval:
> - **Before (inject):** `artifacts/eval/after_inject_bad.csv`
> - **After (clean):** `artifacts/eval/after_clean_fix.csv`

### Cau hoi then chot: refund window (`q_refund_window`)

**Truoc (inject-bad, --no-refund-fix --skip-validate):**

| Truong | Gia tri |
|--------|---------|
| top1_doc_id | policy_refund_v4 |
| top1_preview | Yeu cau duoc gui trong vong 7 ngay lam viec ke tu thoi diem xac nhan don hang. |
| contains_expected | yes |
| **hits_forbidden** | **yes** |

> Giai thich: Mac du top-1 chunk co "7 ngay", top-k (k=3) van chua chunk stale "14 ngay lam viec" vi khong ap dung refund fix. Day chinh la van de: agent co the tra loi sai neu dung context tu chunk stale.

**Sau (sprint3-clean, pipeline chuan):**

| Truong | Gia tri |
|--------|---------|
| top1_doc_id | policy_refund_v4 |
| top1_preview | Yeu cau duoc gui trong vong 7 ngay lam viec ke tu thoi diem xac nhan don hang. |
| contains_expected | yes |
| **hits_forbidden** | **no** |

> Giai thich: Pipeline chuan fix "14 ngay" -> "7 ngay" va embed_prune_removed=1 (xoa chunk_id stale khoi vector store). Top-k khong con chua thong tin sai.

### Merit: versioning HR — `q_leave_version`

**Truoc (inject-bad):**

| Truong | Gia tri |
|--------|---------|
| top1_doc_id | hr_leave_policy |
| contains_expected | yes (co "12 ngay") |
| hits_forbidden | no |
| top1_doc_expected | yes |

**Sau (sprint3-clean):**

| Truong | Gia tri |
|--------|---------|
| top1_doc_id | hr_leave_policy |
| contains_expected | yes (co "12 ngay") |
| hits_forbidden | no |
| top1_doc_expected | yes |

> Giai thich: Ca hai scenario deu pass cho `q_leave_version` vi Rule 4 (quarantine hr_leave_policy voi effective_date < 2026-01-01) da loai ban HR cu (10 ngay phep) o buoc clean truoc khi embed. Rule nay hoat dong doc lap voi --no-refund-fix, nen khong bi anh huong boi inject. Day chung minh tang bao ve cua pipeline: moi rule bao ve mot loai corruption cu the.

---

## 3. Freshness & monitor

Ca hai run deu tra ve **FAIL** cho freshness check:
- `latest_exported_at`: 2026-04-10T08:00:00
- `age_hours`: ~121h (>5 ngay)
- `sla_hours`: 24.0
- `reason`: freshness_sla_exceeded

> Giai thich: Du lieu raw duoc export ngay 2026-04-10, nhung pipeline chay ngay 2026-04-15. Khoang cach >24h vuot SLA. Trong moi truong production, can tu dong re-export hoac canh bao team de dam bao du lieu luon fresh.

---

## 4. Corruption inject (Sprint 3)

### Phuong phap inject

Chay pipeline voi 2 flag:
```bash
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
```

- `--no-refund-fix`: Tat Rule 7, giu nguyen chunk chua "14 ngay lam viec" (thong tin sai) trong cleaned data.
- `--skip-validate`: Bo qua pipeline halt khi expectation `refund_no_stale_14d_window` FAIL, cho phep embed du lieu loi vao Chroma.

### Ket qua inject

1. **Expectation `refund_no_stale_14d_window` FAIL** (violations=1): Pipeline phat hien dung chunk stale nhung bi bypass boi --skip-validate.
2. **Retrieval `q_refund_window` hits_forbidden=yes**: Top-3 chunks chua ca "7 ngay" lan "14 ngay lam viec", nghia la agent co the tra loi sai cho khach hang.
3. **embed_prune_removed=1** khi chay lai pipeline chuan: Chunk stale (co "14 ngay") bi xoa khoi vector store, chung minh co che prune hoat dong.

### Cach phat hien

- Expectation suite phat hien ngay tai buoc validate (truoc embed).
- Eval retrieval (`eval_retrieval.py`) phat hien qua `hits_forbidden` column — quet toan bo top-k de tim keyword cam.
- Log ghi ro `WARN: expectation failed but --skip-validate` lam bang chung audit.

---

## 5. Han che & viec chua lam

- Freshness check FAIL vi du lieu mau co ngay export co dinh (2026-04-10) — trong thuc te can tu dong re-export.
- Inject chi tat 1 rule (refund fix); co the mo rong inject nhieu scenario hon (duplicate them, sai doc_id, v.v.).
- Chua co alerting tu dong khi expectation fail — hien chi ghi log.
- q_leave_version khong bi anh huong boi inject vi Rule 4 (HR stale) hoat dong doc lap — can thiet ke inject rieng cho scenario nay (vi du: them row hr_leave_policy voi "10 ngay phep" va effective_date >= 2026).
