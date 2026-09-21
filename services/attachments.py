# -*- coding: utf-8 -*-
"""ไฟล์แนบของคำขอ

รวมสองที่เก็บให้เป็นรายการเดียวเพื่อให้ฝั่งหน้าจอแสดงผลแบบเดียวกัน:
  1. IT_HELPDESK_REQUEST.REQUEST_FILE  ของเดิม แนบได้ไฟล์เดียว
  2. IT_HELPDESK_ATTACHMENT            ของใหม่ แนบได้หลายไฟล์ (ใบโอนย้ายใช้ตัวนี้)
"""
import os

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
