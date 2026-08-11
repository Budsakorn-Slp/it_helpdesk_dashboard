# -*- coding: utf-8 -*-
"""หน้า /asset แบบรายการเอกสาร

รวมข้อมูล 3 ทางเข้าด้วยกันเป็นตารางเดียว:
  1. รายละเอียดเอกสาร (ประเภท / ทรัพย์สิน / หัวเรื่อง)  ← sql.DOCS_LIST
  2. สถานะการอนุมัติล่าสุด                              ← sql.LATEST_APPROVER
  3. ลายเซ็นบนเอกสารครบหรือยัง                          ← sql.LATEST_TRANSFER_SIGNATURE

จากนั้นคำนวณ workflow_status เพื่อให้แต่ละแถวรู้ว่าควรมีปุ่มดำเนินการอะไร
"""
import re

import config
import db
import sql
from services import boards, docs, tracking

#: REQUEST_DATE เก็บเป็น VARCHAR2 'DD/MM/YYYY HH24:MI' — เรียงตรง ๆ ไม่ได้
_DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2}):(\d{2}))?")


def date_sort_key(text):
    """'DD/MM/YYYY HH:MM' → 'YYYYMMDDHHMM' ที่เรียงด้วยการเทียบสตริงได้"""
    m = _DATE_RE.match((text or "").strip())
    if not m:
        return ""
    day, month, year, hour, minute = m.groups()
    return f"{year}{month}{day}{hour or '00'}{minute or '00'}"

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

#: ลำดับสถานะที่แสดงในเมนูซ้าย
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
        row["sort_date"]         = date_sort_key(d.get("request_date"))
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


# ── เมนูซ้าย ─────────────────────────────────────────────────────────────────

def build_status_nav(stats):
    """หมวด "สถานะงาน" ในเมนูซ้าย — เรียงตามลำดับการทำงานจริง"""
    return [
        {
            "key":   key,
            "label": WORKFLOW_LABELS[key][0],
            "cls":   WORKFLOW_LABELS[key][1],
            "count": stats.get(key, 0),
        }
        for key in STAT_GROUPS
    ]


def build_nav(rows):
    """โครงเมนูซ้ายพร้อมจำนวนเอกสารในแต่ละหมวด

    โครงสร้างตามที่ระบบเอกสารใช้จริง:
        เอกสาร
          └ ใบโอนย้าย            (คำขอที่มีแถวใน IT_HELPDESK_TRANSFER)
              ├ โอนย้ายระหว่างหน่วยงาน
              ├ ตัดบัญชี / สูญหาย
              ├ เพื่อขาย
              ├ ส่งซ่อม
              └ ยืม
        คำขอทั่วไป               (เบิก / ยืม ที่ไม่ได้ออกใบโอนย้าย)
    """
    def count(group=None, code=None):
        return sum(
            1 for r in rows
            if (group is None or r["doc_group"] == group)
            and (code is None or r["doc_code"] == code)
        )

    transfer_children = [
        {
            "key":   f"{config.GROUP_TRANSFER}:{code}",
            "label": info["label"],
            "cls":   info["cls"],
            "count": count(config.GROUP_TRANSFER, code),
        }
        for code, info in config.TRANSFER_DOC_TYPES.items()
    ]

    plain_children = [
        {
            "key":   f"{config.GROUP_REQUEST}:{code}",
            "label": info["label"],
            "cls":   info["cls"],
            "count": count(config.GROUP_REQUEST, code),
        }
        for code, info in config.PLAIN_REQUEST_TYPES.items()
    ]
    other = count(config.GROUP_REQUEST, "OTHER")
    if other:
        plain_children.append({
            "key":   f"{config.GROUP_REQUEST}:OTHER",
            "label": config.UNKNOWN_REQUEST_TYPE["label"],
            "cls":   config.UNKNOWN_REQUEST_TYPE["cls"],
            "count": other,
        })

    return [
        {
            "key":      "doc",
            "label":    "เอกสาร",
            "icon":     "ic-folder",
            "count":    count(config.GROUP_TRANSFER),
            "children": [
                {
                    "key":      config.GROUP_TRANSFER,
                    "label":    "ใบโอนย้าย",
                    "icon":     "ic-detail",
                    "count":    count(config.GROUP_TRANSFER),
                    "children": transfer_children,
                },
            ],
        },
        {
            "key":      config.GROUP_REQUEST,
            "label":    "คำขอทั่วไป",
            "icon":     "ic-inbox",
            "hint":     "ไม่ได้ออกใบโอนย้าย",
            "count":    count(config.GROUP_REQUEST),
            "children": plain_children,
        },
    ]
