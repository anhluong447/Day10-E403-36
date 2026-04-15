"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).

Rules mới (Sprint 2):
  Rule 8 — strip_bom_and_control_chars: Loại BOM và control chars trước mọi rule khác.
  Rule 9 — quarantine_future_effective_date: Quarantine chunk có ngày hiệu lực > 180 ngày tương lai.
  Rule 10 — quarantine_chunk_text_too_long: Quarantine chunk_text > MAX_CHUNK_TEXT_LENGTH ký tự.
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

# Rule 9: chunk có effective_date vượt ngưỡng này (tính từ exported_at) bị quarantine.
FUTURE_DATE_THRESHOLD_DAYS = 180

# Rule 10: chunk_text dài hơn ngưỡng này bị quarantine (dấu hiệu merge lỗi / dump toàn doc).
# all-MiniLM-L6-v2 giới hạn 256 tokens (~1 000–1 500 ký tự); 2 000 là margin an toàn.
MAX_CHUNK_TEXT_LENGTH = 2000

# Regex loại BOM (\ufeff) và ASCII control chars (0x00–0x1F) trừ tab (0x09) và newline (0x0A, 0x0D).
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufeff]")

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def _strip_control_chars(s: str) -> str:
    """Rule 8 helper: loại BOM (\\ufeff) và ASCII control chars khỏi chuỗi."""
    return _CONTROL_CHARS.sub("", s)


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.

    Sprint 2 — Rules mới:
    8) Strip BOM và control characters khỏi doc_id và chunk_text trước mọi rule khác.
       metric_impact: Row inject có \\ufeff prefix → doc_id được giải cứu thay vì bị quarantine
       unknown_doc_id; quarantine_records không tăng, cleaned_records tăng 1.
    9) Quarantine: effective_date > FUTURE_DATE_THRESHOLD_DAYS ngày kể từ exported_at.
       metric_impact: Row inject có effective_date=2027-06-01 → quarantine_records tăng 1.
   10) Quarantine: chunk_text > MAX_CHUNK_TEXT_LENGTH ký tự (dấu hiệu merge lỗi / dump toàn doc).
       metric_impact: Row inject có chunk_text dài 2001 chars → quarantine_records tăng 1.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        # --- Rule 8: Strip BOM và control characters ---
        # Phải chạy ĐẦU TIÊN trước tất cả rule khác để tránh doc_id bị sai allowlist do BOM.
        # BOM (\\ufeff) phổ biến khi export CSV từ Excel trên Windows.
        doc_id = _strip_control_chars(raw.get("doc_id", ""))
        text = _strip_control_chars(raw.get("chunk_text", ""))
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        # --- Rule 1: Allowlist doc_id ---
        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        # --- Rule 2 & 3: Chuẩn hoá effective_date ---
        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        # --- Rule 9: Quarantine future effective_date ---
        # Chunk có ngày hiệu lực trong tương lai xa chưa có giá trị trong RAG ngay bây giờ.
        try:
            eff_dt = datetime.strptime(eff_norm, "%Y-%m-%d")
            if exported_at:
                # Normalize exported_at: strip timezone info để so sánh naive vs naive
                exported_str = exported_at.replace("Z", "").split("+")[0].split(".")[0]
                exported_dt = datetime.fromisoformat(exported_str)
            else:
                exported_dt = datetime.now()
            delta_days = (eff_dt - exported_dt).days
            if delta_days > FUTURE_DATE_THRESHOLD_DAYS:
                quarantine.append(
                    {
                        **raw,
                        "reason": "future_effective_date",
                        "days_ahead": delta_days,
                        "effective_date_normalized": eff_norm,
                    }
                )
                continue
        except (ValueError, TypeError):
            pass  # Lỗi parse đã được xử lý ở Rule 2/3 phía trên

        # --- Rule 4 (baseline): Stale HR policy ---
        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        # --- Rule 5 (baseline): Missing chunk_text ---
        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # --- Rule 10: Quarantine chunk_text quá dài ---
        # Chunk > MAX_CHUNK_TEXT_LENGTH ký tự dấu hiệu merge lỗi hoặc dump toàn bộ document.
        # all-MiniLM-L6-v2 giới hạn 256 tokens; chunk quá dài làm giảm chất lượng embedding.
        if len(text) > MAX_CHUNK_TEXT_LENGTH:
            quarantine.append(
                {
                    **raw,
                    "reason": "chunk_text_too_long",
                    "length": len(text),
                }
            )
            continue

        # --- Rule 6 (baseline): Deduplication ---
        key = _norm_text(text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        # --- Rule 7 (baseline): Fix stale refund window ---
        fixed_text = text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at or "",
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
