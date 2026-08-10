# -*- coding: utf-8 -*-
"""ประกอบข้อมูลบอร์ด — รวม fetch_general_board / fetch_asset_board เดิมไว้ที่เดียว

ต่างกันแค่บอร์ด asset ที่ต้องดูว่าคำขอมีเอกสารโอนย้ายค้างอยู่หรือไม่
(ดู config.TRACKING_BOARDS)
"""
import config
import db
import sql

#: จำนวนการ์ด "เสร็จแล้ว" ที่โหลดตอนเปิดหน้า
DONE_PAGE_SIZE = 20


def map_workflow_status(req):
    """คำขอ 1 ใบ → คอลัมน์ที่ควรไปอยู่บนบอร์ด"""
    approver = str(req.get("approver_status") or "Waiting").strip()
    status   = str(req.get("request_status") or "0").strip()
    typeform = str(req.get("request_typeform") or "").strip()

    if approver == "Reject" or status == "3":
        return "cancel"
    if status == "5":
        return "done"
    if status == "2":
        return "doing"
    # บอร์ด support ไม่ต้องผ่านการอนุมัติ — ลงมือได้เลย
    if typeform == config.BOARDS["support"]["typeform"]:
        return "ready"
    if approver == "Approve":
        return "ready"
    return "waiting"


def group_by_day(rows):
    """จัดกลุ่มตามวันที่แจ้ง แล้วแยกตามคอลัมน์บอร์ด"""
    grouped = {}
    for r in rows:
        day = (r.get("request_date") or "")[:10]
        bucket = grouped.setdefault(day, {s: [] for s in config.WORKFLOW_STATUSES})
        status = r.get("workflow_status", "waiting")
        bucket.get(status, bucket["waiting"]).append(r)
    return dict(sorted(grouped.items()))


# ── ดึงข้อมูล ────────────────────────────────────────────────────────────────

def _fetch_active(cur, typeform):
    """คำขอที่ยังไม่ปิด + สถานะอนุมัติล่าสุดของแต่ละใบ"""
    cur.execute(sql.BOARD, {"typeform": typeform})
    active = []
    for d in db.rows_to_dicts(cur):
        d["request_status"] = str(d.get("request_status") or "0").strip()
        d["approver_status"] = "Waiting"
        active.append(d)

    cur.execute(sql.LATEST_APPROVER)
    approvals = {str(rid).strip(): str(st or "Waiting").strip() for rid, st in cur.fetchall()}
    for d in active:
        rid = str(d.get("request_id") or "").strip()
        if rid in approvals:
            d["approver_status"] = approvals[rid]
    return active


def _fetch_done(cur, typeform):
    """การ์ด 'เสร็จแล้ว' หน้าแรก + จำนวนทั้งหมด"""
    cur.execute(sql.DONE, {"typeform": typeform, "max_rows": DONE_PAGE_SIZE})
    done = []
    for d in db.rows_to_dicts(cur):
        d["request_status"] = str(d.get("request_status") or "0").strip()
        done.append(d)

    cur.execute(sql.DONE_COUNT, {"typeform": typeform})
    return done, db.scalar(cur, 0)


def _tracking_ids(cur):
    cur.execute(sql.TRANSFER_REQUEST_IDS)
    return {str(row[0]).strip() for row in cur.fetchall()}


def fetch_board(board_key):
    """ข้อมูลทั้งหมดที่หน้าบอร์ดหนึ่งหน้าต้องใช้"""
    cfg = config.BOARDS[board_key]
    typeform = str(cfg["typeform"]).strip()

    with db.db_conn() as conn:
        cur = conn.cursor()
        tracking_ids = _tracking_ids(cur) if board_key in config.TRACKING_BOARDS else set()
        active = _fetch_active(cur, typeform)
        for d in active:
            status = map_workflow_status(d)
            rid = str(d.get("request_id") or "").strip()
            if status not in ("cancel", "done") and rid in tracking_ids:
                status = "tracking"
            d["workflow_status"] = status
        done, done_total = _fetch_done(cur, typeform)

    active.sort(key=lambda r: (
        config.ORDER_PRIORITY.get(r.get("workflow_status"), 99),
        r.get("request_date") or "",
    ))

    return {
        "active":         active,
        "done":           done,
        "done_total":     done_total,
        "waiting_items":  [r for r in active if r.get("workflow_status") == "waiting"],
        "grouped_active": group_by_day(active),
    }


def empty_board():
    """โครงสร้างว่าง — ใช้ตอนต่อฐานข้อมูลไม่ได้ เพื่อให้หน้ายัง render ได้"""
    return {"active": [], "done": [], "done_total": 0,
            "waiting_items": [], "grouped_active": {}}


def fetch_done_page(board_key, offset, limit):
    """โหลดการ์ด 'เสร็จแล้ว' เพิ่ม (server-side paging)"""
    typeform = str(config.BOARDS[board_key]["typeform"]).strip()
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.DONE_PAGE, {
            "typeform":  typeform,
            "offset":    offset,
            "limit_end": offset + limit,
        })
        items = []
        for d in db.rows_to_dicts(cur):
            d["request_status"] = str(d.get("request_status") or "0")
            d = db.blank_none(d)
            d.pop("rn", None)
            items.append(d)
        return items
