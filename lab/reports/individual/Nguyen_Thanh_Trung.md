# Bao Cao Ca Nhan — Lab Day 10: Data Pipeline & Observability

**Ho va ten:** Nguyen Thanh Trung
**Vai tro:** Embed & Eval Owner (Sprint 3)  
**Ngay nop:** 2026-04-15  
**Do dai yeu cau:** 400-650 tu

---

## 1. Toi phu trach phan nao?

**File / module:**

- `etl_pipeline.py`: Chay pipeline inject corruption (Sprint 3) voi `--no-refund-fix --skip-validate`
- `eval_retrieval.py`: Chay eval before/after de chung minh anh huong retrieval len vector store
- `docs/quality_report.md`: Viet quality report so sanh so lieu inject-bad vs sprint3-clean

**Ket noi voi thanh vien khac:**

Toi nhan cleaned data va expectation suite tu Cleaning & Quality Owner (Sprint 2), sau do thuc hien inject corruption de kiem chung pipeline co phat hien va ngan chan du lieu xau hay khong. Ket qua eval cua toi la bang chung before/after cho group report.

**Bang chung (commit / comment trong code):**

- `artifacts/eval/after_inject_bad.csv` — eval khi embed du lieu xau (run_id=inject-bad)
- `artifacts/eval/after_clean_fix.csv` — eval khi embed du lieu sach (run_id=sprint3-clean)
- `artifacts/logs/run_inject-bad.log` — log pipeline inject, E3 FAIL
- `artifacts/logs/run_sprint3-clean.log` — log pipeline clean, all expectations OK
- `docs/quality_report.md` — quality report so sanh before/after

---

## 2. Mot quyet dinh ky thuat

**Quyet dinh: Dung `--no-refund-fix` ket hop `--skip-validate` de inject corruption co kiem soat.**

Thay vi chinh sua truc tiep file CSV de tao du lieu xau, toi dung 2 flag co san cua pipeline. `--no-refund-fix` tat Rule 7 (giu nguyen "14 ngay lam viec" trong chunk refund stale). `--skip-validate` bypass pipeline halt khi expectation E3 (`refund_no_stale_14d_window`) FAIL, cho phep embed du lieu loi vao Chroma.

Cach nay co loi diem: inject co the lap lai (reproducible) bang mot dong lenh, khong can chinh sua file nao, va pipeline van ghi day du log + manifest de audit. Dong thoi chung minh duoc rang expectation suite da phat hien dung loi (`violations=1`) — chi la bi bypass co chu dich.

---

## 3. Mot loi hoac anomaly da xu ly

**Trieu chung:** Sau khi chay inject-bad, eval retrieval cho cau hoi `q_refund_window` tra ve `hits_forbidden=yes`. Nghia la trong top-3 chunks tra ve cho cau hoi "bao nhieu ngay de yeu cau hoan tien", co chunk chua "14 ngay lam viec" — thong tin sai so voi policy hien hanh (7 ngay).

**Metric phat hien:** 
- Expectation E3 (`refund_no_stale_14d_window`) FAIL voi `violations=1` trong log.
- `eval_retrieval.py` bao `hits_forbidden=yes` cho `q_refund_window`.

**Fix:** Chay lai pipeline chuan (`python etl_pipeline.py run --run-id sprint3-clean`). Rule 7 fix "14 ngay" -> "7 ngay". Co che prune xoa chunk stale khoi vector store (`embed_prune_removed=1` trong log). Eval lai: `hits_forbidden=no`. Agent se khong con tra loi sai.

---

## 4. Bang chung truoc / sau

**Run inject-bad (du lieu xau, run_id=inject-bad):**
```
q_refund_window, contains_expected=yes, hits_forbidden=yes
q_leave_version, contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes
```

**Run sprint3-clean (du lieu sach, run_id=sprint3-clean):**
```
q_refund_window, contains_expected=yes, hits_forbidden=no
q_leave_version, contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes
```

Diem khac biet then chot: `hits_forbidden` chuyen tu **yes -> no** cho `q_refund_window` sau khi pipeline fix va prune chunk stale.

---

## 5. Cai tien tiep theo

Neu co them 2 gio, toi se viet mot script automated regression test: chay ca 2 scenario (inject-bad va clean), tu dong parse 2 file eval CSV, va assert rang `hits_forbidden=yes` khong xuat hien trong ban clean. Dieu nay cho phep CI phat hien regression truoc khi deploy, thay vi kiem tra thu cong.
