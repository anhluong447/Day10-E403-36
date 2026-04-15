# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lương Hoàng Anh

**Vai trò:** Monitoring / Docs Owner

**Ngày nộp:** 2026-04-15

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
- Khởi tạo và thiết lập cảnh báo đo độ tươi của dữ liệu: `monitoring/freshness_check.py`.
- Viết tài liệu quy trình vận hành: `docs/runbook.md`.
- Lập sơ đồ kiến trúc hệ thống: `docs/pipeline_architecture.md`.
- Tập hợp bằng chứng và viết báo cáo chất lượng: `docs/quality_report.md`, `reports/group_report.md`.

**Kết nối với thành viên khác:**
Tôi nhận file `manifest_<run_id>.json` từ **Embed Owner** để lấy các timestamp cần thiết cho việc kiểm tra SLA. Tôi cũng phối hợp với **Cleaning Owner** để đưa các mã lỗi Expectation (như `refund_no_stale_14d_window`) vào tài liệu chuẩn đoán sự cố trong Runbook.

**Bằng chứng:**
Chạy lệnh kiểm tra freshness trực tiếp với manifest `artifacts/manifests/manifest_final-fix.json`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

**Quyết định ngưỡng Freshness SLA là 24 giờ:**
Khi điền `contracts/data_contract.yaml`, tôi đã lựa chọn `sla_hours: 24` đo đạc tại thời điểm `"publish"` (sau khi embed xong). 

Lý do: Các văn bản hành chính nhân sự hoặc chính sách hỗ trợ IT Helpdesk (đặc biệt là các thay đổi như SLA P1 hay số ngày hoàn tiền) thường cần thời gian lan truyền, nhưng không được phép chệch quá 1 ngày làm việc để tránh rủi ro Agent tư vấn sai cho User. Bằng việc giám sát thông minh thông số `latest_exported_at` từ file exported thô so với thời gian chạy hiện hành, nhóm vận hành có thể phát hiện ngay nếu Upstream bị ngắt kết nối mà vẫn chạy thành công Embed (tạo ảo giác an toàn).

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Sự cố:** Lệnh tự động cảnh báo Data Stale.

Triệu chứng: Khi chạy kiểm tra `python etl_pipeline.py freshness` trên bản Run `final-fix`, hệ thống bắn ra kết quả lỗi: 
`FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 115.62, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`

Chẩn đoán và khắc phục:
Tôi nhận thấy pipeline không bị hỏng, mà là do bộ dữ liệu xuất mẫu có `exported_at` tĩnh từ ngày 10/04/2026, khiến `age_hours` vượt mức tối đa 24 tiếng. Đây là một cảnh báo chính xác (True Positive) chứ không phải lỗi script. Thay vì "hack" code để hiển thị `PASS` ảo, tôi quyết định giữ nguyên logic, cập nhật vào `docs/runbook.md` để Data Owner nắm được "hành động yêu cầu: Báo cáo với IT xuất file mới".

---

## 4. Bằng chứng trước / sau (80–120 từ)

Trong phần báo cáo Quality, tôi đã quan sát rõ rệt sự thay đổi của cột `hits_forbidden` như chỉ số Observability quan trọng của hệ thống:

- **Bản inject-bad:** Thất bại trong việc thanh lọc dữ liệu bẩn.
  `q_refund_window, Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?, policy_refund_v4, Yêu cầu được gửi trong vòng 14 ngày làm việc... ,yes, yes, , 3`

- **Bản final-fix:** Dữ liệu hoàn toàn sạch, chặn Agent lấy thông tin lỗi thời.
  `q_refund_window, Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?, policy_refund_v4, Yêu cầu được gửi trong vòng 7 ngày làm việc... ,yes, no, , 3`

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ làm việc, tôi sẽ mở rộng cơ chế `monitoring/freshness_check.py` để bắn alert qua webhook thật (tích hợp với Slack/Teams), đồng thời tạo ra một manifest dashboard rút gọn để không còn phải đọc file `.json` thủ công trên môi trường Production.
