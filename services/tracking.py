# -*- coding: utf-8 -*-
"""เอกสารทรัพย์สิน (IT_HELPDESK_TRANSFER) — เงื่อนไขลายเซ็นครบ และลำดับผู้ลงนาม"""
import db
import sql

#: สถานะที่แปลว่า "ลายเซ็นครบแล้ว รอ IT ปิดงาน"
WAITING_IT = "WAITING_IT"
DONE       = "DONE"

#: ประเภทเอกสารที่ต้องมีทั้งผู้ส่งและผู้รับ
_NEEDS_SENDER_AND_RECEIVER = ("TRANSFER",)
#: ประเภทเอกสารที่ต้องมีแค่ผู้รับ
_NEEDS_RECEIVER = ("BORROW", "REPAIR")
#: ประเภทเอกสารที่ต้องผ่านผู้อนุมัติสุดท้าย
_NEEDS_MANAGER = ("DISPOSE", "SALE")


def is_complete(row):
    """ลายเซ็นบนเอกสารครบตามประเภทหรือยัง

    TRANSFER : ผู้รับเซ็น + มีชื่อผู้ส่ง
    BORROW / REPAIR : ผู้รับเซ็น
    DISPOSE / SALE  : ผู้อนุมัติสุดท้ายเซ็น หรือสถานะเป็น WAITING_IT แล้ว
    """
    t_type   = (row.get("transfer_type") or "").strip().upper()
    t_status = (row.get("transfer_status") or "").strip().upper()
    has_receiver = bool(row.get("receiver_approved_at"))
    has_sender   = bool((row.get("sender_name") or "").strip())
    has_manager  = bool(row.get("manager_approve_date"))

    if t_type in _NEEDS_SENDER_AND_RECEIVER:
        return has_receiver and has_sender
    if t_type in _NEEDS_RECEIVER:
        return has_receiver
    if t_type in _NEEDS_MANAGER:
        return t_status == WAITING_IT or has_manager
    return False


def fetch_tracking_items(cur):
    """รายการเอกสารที่ยังไม่ปิด พร้อมธง is_complete"""
    cur.execute(sql.TRACKING)
    items = db.rows_to_dicts(cur)
    for item in items:
        complete = is_complete(item)
        item["is_complete"] = complete
        # ถ้า DB ยังเป็น PENDING แต่ลายเซ็นครบแล้ว ให้ตอบกลับเป็น WAITING_IT
        # เพื่อให้ฝั่งหน้าจอแสดงปุ่มปิดงานได้
        if complete and (item.get("transfer_status") or "").upper() not in (WAITING_IT, DONE):
            item["transfer_status"] = WAITING_IT
    return items


# ── ลำดับผู้ลงนามบนเอกสาร ───────────────────────────────────────────────────

def _step(title, by, date_val, done):
    return {
        "title":  title,
        "by":     str(by or "—").strip() or "—",
        "date":   str(date_val or ""),
        "status": "approved" if done else "waiting",
    }


def build_signature_steps(row):
    """แถวจาก sql.TRANSFER_SIGNATURES → ลำดับผู้ลงนามสำหรับ timeline

    หมายเหตุสคีมา: เมื่อ RECEIVER_TYPE = 'supplier' ชื่อ Supplier จริง
    จะถูกเก็บไว้ในคอลัมน์ SENDER_NAME ไม่ใช่ RECEIVER_NAME
    """
    (t_type, sender_name, receiver_name, recv_at, receiver_type,
     mgr_by, mgr_date, fname, lname, req_date, closed_by, closed_at) = row

    t_type        = (t_type or "").strip().upper()
    receiver_type = (receiver_type or "").strip().lower()
    is_supplier   = receiver_type == "supplier"
    it_name       = f"{fname or ''} {lname or ''}".strip()
    display_receiver = receiver_name or ("Supplier" if is_supplier else None)

    steps = [_step("IT ผู้ออกเอกสาร", it_name, req_date, True)]

    if t_type in _NEEDS_SENDER_AND_RECEIVER + _NEEDS_RECEIVER:
        if is_supplier:
            # ไม่มีขั้นผู้ส่ง — SENDER_NAME คือชื่อ Supplier ที่เป็นผู้รับ
            steps.append(_step("ผู้รับ / Supplier", sender_name, recv_at, bool(recv_at)))
        else:
            has_sender = bool(sender_name and str(sender_name).strip())
            steps.append(_step("ผู้ส่ง (Sender)", sender_name, "", has_sender))
            steps.append(_step("ผู้รับ (Receiver)", display_receiver, recv_at, bool(recv_at)))

    elif t_type in _NEEDS_MANAGER:
        receiver_display = sender_name if (is_supplier and sender_name) else display_receiver
        receiver_label   = "ผู้รับ / Supplier" if is_supplier else "ผู้รับ (Receiver)"
        steps.append(_step(receiver_label, receiver_display, recv_at, bool(recv_at)))
        steps.append(_step("ผู้อนุมัติสุดท้าย (Final Approval)", mgr_by, mgr_date, bool(mgr_date)))

    steps.append(_step("IT ปิดงาน", closed_by, closed_at, bool(closed_at)))
    return steps
