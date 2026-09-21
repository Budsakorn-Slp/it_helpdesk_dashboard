# -*- coding: utf-8 -*-
"""ประเภทเอกสาร (IT_HELPDESK_TYPE) และการส่งต่อไปทีมอื่น

ความสัมพันธ์กับตารางคำขอ:
    IT_HELPDESK_TYPE.ID   →  IT_HELPDESK_REQUEST.REQUEST_TYPEFORM
    IT_HELPDESK_TYPE.NAME →  IT_HELPDESK_REQUEST.REQUEST_CATEGORY
การเปลี่ยนประเภทจึงต้องอัปเดตสองคอลัมน์นี้พร้อมกันเสมอ

หมายเหตุ: อย่าสับสนกับ IT_HELPDESK_APPROVER.FORWARD_FROM/FORWARD_AT
ซึ่งระบบฟอร์มใช้สำหรับ "โอนสิทธิ์อนุมัติให้พนักงานอีกคน" คนละเรื่องกัน
การส่งต่อทีมของหน้านี้เก็บประวัติไว้ใน IT_HELPDESK_LOG เท่านั้น
"""
import config
import db
import sql

#: ประเภทที่ส่งต่อได้ = ประเภทที่มีบอร์ดรองรับใน dashboard
#  (ประเภท 6 "ขอสั่งซื้อ" เป็นฟอร์มภายนอก ไม่มีบอร์ด จึงไม่ให้ส่งไป)
SELECTABLE_TYPE_IDS = tuple(cfg["typeform"] for cfg in config.BOARDS.values())


def fetch_selectable(cur):
    """ประเภทเอกสารที่เลือกส่งต่อได้ — เรียงตาม ID"""
    cur.execute(sql.IT_TYPES)
    return [
        {"id": str(row["id"]), "name": (row["name"] or "").strip(),
         "icon": row["icon"], "color": row["color"]}
        for row in db.rows_to_dicts(cur)
        if str(row["id"]) in SELECTABLE_TYPE_IDS
    ]


def lookup(cur, type_id):
    """ประเภทตาม ID — คืน None ถ้าไม่มีหรือปิดใช้งานอยู่"""
    cur.execute(sql.IT_TYPE_BY_ID, {"type_id": type_id})
    row = db.row_to_dict(cur)
    if not row:
        return None
    return {"id": str(row["id"]), "name": (row["name"] or "").strip()}


def current_of(cur, req_id):
    """ประเภท/หมวด/สถานะปัจจุบันของคำขอ — คืน None ถ้าไม่พบคำขอ"""
    cur.execute(sql.REQUEST_TYPE_OF, {"req_id": req_id})
    return db.row_to_dict(cur)


def board_of(type_id):
    """type id → board_key ที่เอกสารจะไปโผล่ (None ถ้าไม่มีบอร์ดรองรับ)"""
    for key, cfg in config.BOARDS.items():
        if cfg["typeform"] == str(type_id):
            return key
    return None
