# -*- coding: utf-8 -*-
"""ไฟล์แนบของคำขอ

รวมสองที่เก็บให้เป็นรายการเดียวเพื่อให้ฝั่งหน้าจอแสดงผลแบบเดียวกัน:
  1. IT_HELPDESK_REQUEST.REQUEST_FILE  ของเดิม แนบได้ไฟล์เดียว
  2. IT_HELPDESK_ATTACHMENT            ของใหม่ แนบได้หลายไฟล์ (ใบโอนย้ายใช้ตัวนี้)
"""
import os
from datetime import datetime

from werkzeug.utils import secure_filename

import config
import db
import sql
from services import docs

#: นามสกุลที่แสดงเป็นรูปตัวอย่างได้
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")

_SIZE_UNITS = ("B", "KB", "MB", "GB")


def is_image(file_name):
    return (file_name or "").lower().endswith(IMAGE_EXTENSIONS)


def format_size(size):
    """ไบต์ → ข้อความอ่านง่าย (คืน '' ถ้าไม่รู้ขนาด)"""
    try:
        value = float(size)
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    for unit in _SIZE_UNITS:
        if value < 1024 or unit == _SIZE_UNITS[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return ""


def _entry(file_name, orig_name=None, size=None, by=None, at=None):
    name = (file_name or "").strip()
    if not name:
        return None
    label = (orig_name or "").strip() or os.path.basename(name)
    return {
        "name":      name,                    # ชื่อไฟล์บนดิสก์ — ใช้ต่อท้าย /uploads/
        "label":     label,                   # ชื่อที่แสดงให้ผู้ใช้เห็น
        "size":      format_size(size),
        "by":        (by or "").strip(),
        "at":        docs.fmt_datetime(at),
        "is_image":  is_image(name),
    }


def fetch(cur, req_id, legacy_file=None):
    """รายการไฟล์แนบทั้งหมดของคำขอ (ของเดิมมาก่อน แล้วตามด้วยของใหม่ตามเวลาอัปโหลด)"""
    items = []

    legacy = _entry(legacy_file)
    if legacy:
        items.append(legacy)

    try:
        cur.execute(sql.REQUEST_ATTACHMENTS, {"req_id": req_id})
        rows = db.rows_to_dicts(cur)
    except db.DatabaseError:
        # ระบบที่ยังไม่ได้สร้างตาราง IT_HELPDESK_ATTACHMENT ก็ยังใช้งานได้
        return items

    seen = {legacy["name"]} if legacy else set()
    for row in rows:
        entry = _entry(row.get("file_name"), row.get("orig_name"),
                       row.get("file_size"), row.get("uploaded_by"), row.get("uploaded_at"))
        if entry and entry["name"] not in seen:
            seen.add(entry["name"])
            items.append(entry)
    return items


# ── อัปโหลดไฟล์แนบ ───────────────────────────────────────────────────────────
#
# ใช้ตอน IT ปิดงานเอกสารติดตามที่ลายเซ็นในระบบยังไม่ครบ — ต้องแนบรูปเอกสาร
# ที่เซ็นจริงมาเป็นหลักฐานแทน ไฟล์เก็บที่เดียวกับระบบ it_helpdesk
# (config.UPLOAD_FOLDER) และตั้งชื่อตามแบบเดิมคือ <เวลา>_<ชื่อไฟล์เดิม>

#: นามสกุลที่รับได้ — รูปถ่ายเอกสาร หรือไฟล์สแกนเป็น PDF
ALLOWED_UPLOAD_EXTENSIONS = IMAGE_EXTENSIONS + (".pdf",)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # 10 MB


class UploadError(ValueError):
    """ไฟล์ที่แนบมาไม่ผ่านเงื่อนไข — ข้อความใน exception ส่งให้ผู้ใช้อ่านได้เลย"""


def _file_size(storage):
    """ขนาดไฟล์เป็นไบต์ โดยไม่ต้องอ่านทั้งไฟล์เข้าหน่วยความจำ"""
    stream = storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    return size


def save(cur, req_id, storage, uploaded_by=""):
    """เซฟไฟล์ลงดิสก์ + บันทึกลง IT_HELPDESK_ATTACHMENT

    ต้องเรียกภายใน transaction เดียวกับงานหลัก (ผู้เรียกเป็นคน commit)
    คืน dict แบบเดียวกับ fetch() — ถ้าไฟล์ไม่ผ่านเงื่อนไขจะโยน UploadError
    """
    orig_name = (getattr(storage, "filename", "") or "").strip()
    if not orig_name:
        raise UploadError("ไม่พบไฟล์ที่แนบมา")

    ext = os.path.splitext(orig_name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise UploadError(
            "แนบได้เฉพาะไฟล์รูปหรือ PDF (" + ", ".join(ALLOWED_UPLOAD_EXTENSIONS) + ")"
        )

    size = _file_size(storage)
    if size <= 0:
        raise UploadError("ไฟล์ที่แนบมาว่างเปล่า")
    if size > MAX_UPLOAD_BYTES:
        raise UploadError(f"ไฟล์ใหญ่เกิน {format_size(MAX_UPLOAD_BYTES)}")

    # secure_filename ตัดอักขระไทยทิ้งทั้งหมด ชื่อไฟล์ภาษาไทยจึงเหลือแค่นามสกุล
    # และทำให้ไฟล์ที่เซฟไม่มีนามสกุล → เบราว์เซอร์แสดงรูปไม่ได้
    # จึงทำความสะอาดเฉพาะส่วนชื่อ แล้วต่อนามสกุลจริงกลับเข้าไปเสมอ
    stem = secure_filename(os.path.splitext(orig_name)[0]) or "attachment"
    file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{stem}{ext}"

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    storage.save(os.path.join(config.UPLOAD_FOLDER, file_name))

    cur.execute(sql.INSERT_ATTACHMENT, {
        "req_id":      req_id,
        "file_name":   file_name,
        "orig_name":   orig_name[:400],
        "file_size":   size,
        "uploaded_by": (uploaded_by or "")[:200],
    })
    return _entry(file_name, orig_name, size, uploaded_by)
