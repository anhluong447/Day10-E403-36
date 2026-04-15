# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Huy Tú  
**Vai trò:** Cleaning / Quality Owner (Sprint 2)  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `transform/cleaning_rules.py`
- `quality/expectations.py`
- `contracts/data_contract.yaml`
- `data/raw/policy_export_dirty.csv`

**Kết nối với thành viên khác:**

Tôi phụ trách phần làm sạch và validation trong Sprint 2, tức là chặn dữ liệu bẩn trước khi bạn phụ trách embed đưa vào Chroma. Tôi phối hợp với bạn Ingestion để dùng cùng `run_id=sprint2` cho log và manifest, giúp đối chiếu được `raw_records`, `cleaned_records`, `quarantine_records`. Tôi cũng phối hợp với bạn làm Sprint 3 để chuẩn bị các row inject có chủ đích trong `policy_export_dirty.csv`, từ đó chứng minh rule mới thực sự có tác động đo được.

**Bằng chứng (commit / comment trong code):**

Commit chính của tôi là `b72dc4b800a804e99a2db42ff5a2642b83bb5cc1`. Commit này thêm Rule 8, Rule 9, Rule 10 trong `transform/cleaning_rules.py`, thêm E7 và E8 trong `quality/expectations.py`, đồng thời cập nhật `contracts/data_contract.yaml` với `owner_team: "CS IT Helpdesk Team"` và `max_length: 2000`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định kỹ thuật quan trọng nhất của tôi là buộc Rule 8 `strip_bom_and_control_chars` phải chạy trước Rule 1 allowlist `doc_id`. Nếu để allowlist chạy trước, row 11 có `doc_id=﻿policy_refund_v4` sẽ bị hiểu sai là `unknown_doc_id` chỉ vì BOM prefix từ export Excel trên Windows. Khi đặt Rule 8 ở đầu pipeline, tôi “cứu” được row hợp lệ này trước khi validation tiếp tục. Đây không chỉ là xử lý format, mà là quyết định về thứ tự rule để tránh false quarantine. Bằng chứng nằm ở `artifacts/cleaned/cleaned_sprint2.csv`, nơi row BOM vẫn xuất hiện trong cleaned với nội dung “Chunk bình thường nhưng doc_id có BOM...”. Tôi cũng đồng bộ quyết định này vào `contracts/data_contract.yaml` để rule được mô tả như một phần của data contract, không chỉ là code tạm thời.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Anomaly tôi xử lý là dữ liệu “trông hợp lệ” nhưng không nên được publish vào RAG. Cụ thể, tôi thêm hai trường hợp inject vào `policy_export_dirty.csv`: row 12 có `effective_date=2027-06-01` và row 13 có `chunk_text` dài 2097 ký tự. Nếu không có Rule 9 và Rule 10, hai row này vẫn có thể đi qua pipeline vì không vi phạm allowlist hay format ngày. Tôi dùng `quarantine_sprint2.csv` để xác nhận fix: row 12 bị gắn `reason=future_effective_date` với `days_ahead=416`, còn row 13 bị gắn `reason=chunk_text_too_long` với `length=2097`. Đây là kiểu lỗi observability quan trọng: dữ liệu chưa sai cú pháp nhưng sai ngữ cảnh vận hành, và nếu embed vào vector store thì agent có thể đọc policy chưa có hiệu lực hoặc chunk merge lỗi.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Tôi dùng chính `artifacts/logs/run_sprint2.log` làm bằng chứng trước/sau cho tác động của rule mới:

- **Trước khi siết đủ rule Sprint 2:** `raw_records=13`, `cleaned_records=9`, `quarantine_records=4`
- **Sau khi hoàn thiện Rule 9 và Rule 10:** `raw_records=13`, `cleaned_records=7`, `quarantine_records=6`

Hai record bị chuyển từ cleaned sang quarantine chính là row future date và row oversized chunk. Ngoài ra, `artifacts/cleaned/cleaned_sprint2.csv` vẫn giữ được row BOM hợp lệ, còn `artifacts/quarantine/quarantine_sprint2.csv` ghi rõ:

- `12,...,future_effective_date,...,days_ahead=416`
- `13,...,chunk_text_too_long,...,length=2097`

Cuối run, expectation mới đều pass: `all_allowed_doc_ids_represented` báo `missing_doc_ids=[]` và `no_unexpected_clean_marker` báo `unexpected_marker_count=0`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ viết một bộ test regression cho `cleaning_rules.py` theo từng inject row thay vì chỉ kiểm tra qua log chạy tay. Tôi muốn có test khẳng định 3 trường hợp: BOM row phải vào cleaned, future date phải vào quarantine, và oversized chunk phải bị chặn ở ngưỡng `max_length=2000`, để tránh người sau sửa rule làm mất tác động Sprint 2.
