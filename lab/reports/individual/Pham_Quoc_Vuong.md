# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Phạm Quốc Vương  
**Vai trò:** Ingestion (chạy pipeline + logging + artifact/manifest evidence)  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `etl_pipeline.py` (entrypoint chạy `run`, ghi log, tạo manifest, gọi embed + freshness)  
- `docs/data_contract.md` (bổ sung “source map” theo Sprint 1)

**Kết nối với thành viên khác:**

Tôi phối hợp với bạn phụ trách cleaning/quality để đảm bảo các metric cần cho observability được ghi ra đầy đủ ngay từ Sprint 1: `raw_records`, `cleaned_records`, `quarantine_records`, cùng đường dẫn artifact để mọi người cùng kiểm tra. Tôi cũng thống nhất với nhóm về `run_id=sprint1` để dễ đối chiếu giữa log, manifest và các bước sau (eval retrieval / freshness).

**Bằng chứng (commit / comment trong code):**

Run thực tế: `python etl_pipeline.py run --run-id sprint1`. Log nằm ở `artifacts/logs/run_sprint1.log` và manifest ở `artifacts/manifests/manifest_sprint1.json`. Trong log có các dòng: `run_id=sprint1`, `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

> VD: chọn halt vs warn, chiến lược idempotency, cách đo freshness, format quarantine.

Quyết định quan trọng tôi chọn là coi log/manifest như “hợp đồng quan sát” (observability contract) cho pipeline: ngay khi chạy `run`, tôi đảm bảo pipeline luôn in ra và ghi file log các chỉ số volume cốt lõi (`raw_records/cleaned_records/quarantine_records`) kèm `run_id`, và tạo `manifest_<run_id>.json` chứa lại các số đó để monitoring đọc được về sau. Điều này giúp nhóm debug theo đúng thứ tự slide Day 10: “Freshness/version → Volume/errors → Schema/contract…”. Ngoài ra, pipeline vẫn có thể báo `freshness_check=FAIL` nhưng không làm crash pipeline (vẫn `PIPELINE_OK`) vì đây là tín hiệu giám sát, không phải lỗi kỹ thuật chạy; bước “halt” chỉ dành cho expectation dữ liệu (vd stale refund/HR conflict) để bảo vệ publish boundary.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

> Mô tả triệu chứng → metric/check nào phát hiện → fix.

Lỗi tôi gặp khi chạy Sprint 1 là pipeline dừng ở bước embed do thiếu dependency. Triệu chứng thể hiện ngay trong log `artifacts/logs/run_sprint1.log` với dòng `ERROR: chromadb chưa cài. pip install -r requirements.txt` và tiến trình trả exit code khác 0 (không có `PIPELINE_OK`). Tôi xử lý bằng cách cài đúng dependencies trong `lab/requirements.txt` (đặc biệt `chromadb`), sau đó chạy lại đúng cùng `run_id=sprint1` để giữ traceability. Ở lần chạy lại, log đã có `embed_upsert count=6 collection=day10_kb`, `manifest_written=artifacts\\manifests\\manifest_sprint1.json` và kết thúc bằng `PIPELINE_OK`. Đây là dạng “operational anomaly” (thiếu môi trường) nhưng được phát hiện nhờ log rõ ràng theo run.

---

## 4. Bằng chứng trước / sau (80–120 từ)

> Dán ngắn 2 dòng từ `before_after_eval.csv` hoặc tương đương; ghi rõ `run_id`.

Tôi dùng evidence “trước/sau” ngay trong cùng file log của `run_id=sprint1` (tương đương before/after cho khả năng publish):

- **Trước (fail embed)** — `artifacts/logs/run_sprint1.log`:
  - `ERROR: chromadb chưa cài. pip install -r requirements.txt`
- **Sau (pass embed + publish manifest)** — cùng log, cùng `run_id=sprint1`:
  - `embed_upsert count=6 collection=day10_kb`
  - `manifest_written=artifacts\manifests\manifest_sprint1.json`

Ngoài ra, manifest `artifacts/manifests/manifest_sprint1.json` ghi lại đúng `raw_records=10`, `cleaned_records=6`, `quarantine_records=4` để phục vụ bước freshness/monitoring Sprint 4.

---

## 5. Cải tiến tiếp theo (40–80 từ)

> Nếu có thêm 2 giờ — một việc cụ thể (không chung chung).

Nếu có thêm 2 giờ, tôi sẽ làm “freshness demo” rõ ràng hơn cho nhóm: thêm một tùy chọn cấu hình SLA theo môi trường (dev có thể 9999h để tránh FAIL nhiễu) và chuẩn hóa `exported_at` trong data mẫu để có cả 3 trạng thái PASS/WARN/FAIL. Đồng thời tôi sẽ bổ sung một script nhỏ tạo `run_id` theo format thống nhất và in ra đường dẫn artifact cuối run để người chấm mở đúng file nhanh.
