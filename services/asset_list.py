# -*- coding: utf-8 -*-
"""หน้า /asset แบบรายการเอกสาร

รวมข้อมูล 3 ทางเข้าด้วยกันเป็นตารางเดียว:
  1. รายละเอียดเอกสาร (ประเภท / ทรัพย์สิน / หัวเรื่อง)  ← sql.DOCS_LIST
  2. สถานะการอนุมัติล่าสุด                              ← sql.LATEST_APPROVER
  3. ลายเซ็นบนเอกสารครบหรือยัง                          ← sql.LATEST_TRANSFER_SIGNATURE

จากนั้นคำนวณ workflow_status เพื่อให้แต่ละแถวรู้ว่าควรมีปุ่มดำเนินการอะไร
"""
import config
import db
import sql
from services import boards, docs, tracking

#: workflow_status → ปุ่มที่แถวนั้นควรมี (ฝั่ง template ใช้ตัดสิน)
ACTIONS = {
    "waiting":  ("approve", "cancel"),
    "ready":    ("start",),
    "doing":    ("close",),
    "tracking": ("close_tracking",),
    "done":     (),
    "cancel":   (),
}

#: workflow_status → (ป้ายไทย, css class)
WORKFLOW_LABELS = {
    "waiting":  ("รออนุมัติ", "wait"),
    "ready":    ("พร้อมทำ",   "ready"),
    "doing":    ("กำลังทำ",   "doing"),
    "tracking": ("ติดตามเอกสาร", "track"),
    "done":     ("เสร็จสิ้น", "done"),
    "cancel":   ("ยกเลิก",    "cancel"),
}

#: ลำดับที่แสดงในตาราง — งานที่ต้องลงมือขึ้นก่อน
ROW_ORDER = {"ready": 1, "doing": 2, "tracking": 3, "waiting": 4, "done": 5, "cancel": 6}

#: กลุ่มที่นับเป็นการ์ดสถิติด้านบน
STAT_GROUPS = ("waiting", "ready", "doing", "tracking", "done", "cancel")


def _signatures(cur):
    """REQUEST_ID → (มีเอกสารโอนย้ายไหม, ลายเซ็นครบไหม)"""
    cur.execute(sql.LATEST_TRANSFER_SIGNATURE)
    return {
        str(row["request_id"]).strip(): tracking.is_complete(row)
        for row in db.rows_to_dicts(cur)
    }


def _approvals(cur):
    cur.execute(sql.LATEST_APPROVER)
    return {str(rid).strip(): str(st or "Waiting").strip() for rid, st in cur.fetchall()}


def fetch_rows():
    """ทุกเอกสาร typeform 4 พร้อมสถานะและปุ่มที่ทำได้ + ตัวเลขการ์ดสถิติ"""
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.DOCS_LIST, {"typeform": config.ASSET_TYPEFORM})
        raw = db.rows_to_dicts(cur)
        approvals  = _approvals(cur)
        signatures = _signatures(cur)

    rows = []
    for d in raw:
        rid = str(d.get("request_id") or "").strip()
        status = str(d.get("request_status") or "0").strip()

        workflow = boards.map_workflow_status({
            "approver_status":  approvals.get(rid, "Waiting"),
            "request_status":   status,
            "request_typeform": config.ASSET_TYPEFORM,
        })
        # เอกสารที่ยังเดินอยู่ ให้ถือเป็น "ติดตามเอกสาร" เหมือนบอร์ดเดิม
        is_tracking = rid in signatures
        if is_tracking and workflow not in ("cancel", "done"):
            workflow = "tracking"

        row = docs.map_row(d)
        row["request_status"]    = status
        row["workflow_status"]   = workflow
        row["is_tracking"]       = is_tracking
        row["tracking_complete"] = signatures.get(rid, False)
        row["actions"]           = ACTIONS.get(workflow, ())

        label, cls = WORKFLOW_LABELS.get(workflow, (row["status_label"], row["status_cls"]))
        row["flow_label"] = label
        row["flow_cls"]   = cls
        rows.append(row)

    rows.sort(key=lambda r: (ROW_ORDER.get(r["workflow_status"], 99), r.get("date_full") or ""))

    stats = {"all": len(rows), **{g: 0 for g in STAT_GROUPS}}
    for r in rows:
        if r["workflow_status"] in stats:
            stats[r["workflow_status"]] += 1

    return rows, stats


def empty():
    """โครงสร้างว่าง — ใช้ตอนต่อฐานข้อมูลไม่ได้"""
    return [], {"all": 0, **{g: 0 for g in STAT_GROUPS}}
