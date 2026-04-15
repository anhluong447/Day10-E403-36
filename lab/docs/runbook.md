# Runbook — Lab Day 10 (incident toi gian)

---

## Symptom

User hoac agent tra loi sai thong tin policy. Vi du:
- Tra loi "14 ngay lam viec" thay vi "7 ngay" cho cau hoi hoan tien.
- Tra loi "10 ngay phep nam" thay vi "12 ngay" cho cau hoi nghi phep.
- Agent tra loi dua tren chunk chua co hieu luc (policy tuong lai) hoac chunk merge loi (noi dung vo nghia).

---

## Detection

| Metric / Check | Cach phat hien | Nguong |
|----------------|---------------|--------|
| Freshness check | `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run_id>.json` | PASS: age <= 24h; FAIL: age > 24h |
| Expectation suite | Xem log `artifacts/logs/run_<run_id>.log` — tim dong `expectation[...] FAIL` | Bat ky FAIL severity=halt -> pipeline halt (exit 2) |
| Retrieval eval | `python eval_retrieval.py --out artifacts/eval/eval_check.csv` — kiem tra cot `hits_forbidden` | `hits_forbidden=yes` -> chunk stale dang trong top-k |
| Quarantine ratio | `quarantine_records / raw_records` trong manifest | > 50% -> bat thuong, can kiem tra nguon export |

### Freshness check — giai thich PASS/WARN/FAIL

- **PASS:** `age_hours <= sla_hours` (mac dinh 24h). Du lieu fresh, khong can hanh dong.
- **WARN:** Manifest ton tai nhung khong co timestamp (`no_timestamp_in_manifest`). Kiem tra format manifest.
- **FAIL:** `age_hours > sla_hours` hoac manifest khong ton tai. Du lieu stale — can re-export tu he nguon va rerun pipeline.

Vi du thuc te (run sprint3-clean):
```
FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 121.2, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```
-> Du lieu export ngay 2026-04-10, chay pipeline ngay 2026-04-15. Khoang cach ~121h >> 24h SLA.

---

## Diagnosis

| Buoc | Viec lam | Ket qua mong doi |
|------|----------|------------------|
| 1 | Kiem tra `artifacts/manifests/manifest_<run_id>.json` | Xac nhan `no_refund_fix`, `skipped_validate`, `raw_records`, `cleaned_records`. Neu `skipped_validate=true` -> pipeline da bypass halt. |
| 2 | Mo `artifacts/quarantine/quarantine_<run_id>.csv` | Kiem tra cot `reason`: nhieu row `unknown_doc_id`? `stale_hr_policy`? `duplicate`? Xac dinh pattern loi. |
| 3 | Mo `artifacts/logs/run_<run_id>.log` | Tim cac dong `expectation[...] FAIL` va `WARN`. Xac nhan expectation nao fail va severity. |
| 4 | Chay `python eval_retrieval.py --out artifacts/eval/debug_eval.csv` | Kiem tra `hits_forbidden` va `contains_expected` cho tung cau hoi. Neu `hits_forbidden=yes` -> chunk stale van trong vector store. |
| 5 | Kiem tra `artifacts/cleaned/cleaned_<run_id>.csv` | Tim chunk co noi dung stale (vd "14 ngay lam viec", "10 ngay phep nam"). Doi chieu voi canonical source trong `data/docs/`. |

---

## Mitigation

1. **Rerun pipeline chuan:**
   ```bash
   python etl_pipeline.py run --run-id hotfix-<timestamp>
   ```
   Pipeline se: fix refund 14->7, quarantine HR cu, embed cleaned data, prune chunk stale tu vector store.

2. **Kiem tra lai eval:**
   ```bash
   python eval_retrieval.py --out artifacts/eval/after_hotfix.csv
   ```
   Xac nhan `hits_forbidden=no` cho tat ca cau hoi.

3. **Neu van con chunk stale trong Chroma:** Xoa collection va rerun:
   ```bash
   rm -rf chroma_db/
   python etl_pipeline.py run --run-id rebuild-<timestamp>
   ```

4. **Tam thoi:** Thong bao team/user rang data dang duoc cap nhat. Neu agent dang serve, can xem xet tam dung hoac them disclaimer.

---

## Prevention

- **Tu dong re-export:** Dat lich export tu he nguon moi 12-24h de freshness luon PASS.
- **CI/CD kiem tra expectation:** Them pipeline CI chay `etl_pipeline.py run` va fail build neu expectation halt.
- **Alert khi freshness FAIL:** Tich hop freshness check vao cron job, gui alert Slack/email khi FAIL.
- **Them expectation moi:** Khi phat hien failure mode moi, them rule trong `cleaning_rules.py` va expectation trong `expectations.py`. Dam bao moi rule co `metric_impact` do duoc.
- **Review quarantine dinh ky:** Dat lich review quarantine CSV hang tuan de phat hien false positive va cap nhat rules.

---

## Peer review — 3 cau hoi (Phan E slide Day 10)

1. **Du lieu cua ban "fresh" den muc nao?** Freshness check hien tai dua tren `latest_exported_at` trong manifest. SLA = 24h. Neu export > 24h truoc -> FAIL. Can tu dong re-export de dam bao.

2. **Neu mot nguon du lieu thay doi schema, ban phat hien bang cach nao?** Expectation suite kiem tra format (E5: ISO date, E2: doc_id khong rong, E4: chunk_text du dai). Neu schema thay doi (vd them cot, doi ten cot), `load_raw_csv` van doc nhung cleaning rules se quarantine row khong hop le. Can them expectation kiem tra column names.

3. **Lam sao biet agent dang tra loi dua tren du lieu cu?** Chay `eval_retrieval.py` kiem tra `hits_forbidden` (keyword cam trong top-k). Ket hop freshness check de biet data co stale khong. Trong production, can log retrieval context va so sanh voi canonical source.
