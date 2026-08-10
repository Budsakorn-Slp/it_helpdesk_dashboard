# -*- coding: utf-8 -*-
"""หน้าเอกสาร /docs — แปลงแถวจาก DB ให้พร้อมแสดงผล (REQUEST_TYPEFORM = 4)"""
import datetime as dt

import config
import db
import sql

#: STEP_TYPE จาก sql.WORKFLOW → ป้ายที่แสดงใน timeline
STEP_LABEL = {
    "receiver": "ผู้รับมอบทรัพย์สิน",
    "manager":  "ผู้จัดการอนุมัติ",
    "it_close": "เจ้าหน้าที่ไอทีปิดงาน",
}
DEFAULT_STEP_LABEL = "ผู้อนุมัติ"

#: STATUS ใน IT_HELPDESK_APPROVER → (ป้าย, css class ของ .tl-item)
WF_STATUS = {
    "approved": ("อนุมัติแล้ว", "done"),
    "approve":  ("อนุมัติแล้ว", "done"),
    "done":     ("เสร็จสิ้น",   "done"),
    "waiting":  ("รออนุมัติ",   "wait"),
    "reject":   ("ไม่อนุมัติ",  "reject"),
}

#: กลุ่มสถิติที่แสดงเป็นการ์ดด้านบนของหน้า
STAT_GROUPS = ("wait", "ready", "active", "doing", "done", "cancel")

TITLE_MAX_LEN = 70


def fmt_datetime(value):
    """DD/MM/YYYY HH:MM — รับได้ทั้ง datetime และ string ที่เก็บมาเป็น VARCHAR2"""
    if value is None:
        return ""
    if isinstance(value, (dt.datetime, dt.date)):
        try:
            return value.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return str(value)
    return str(value).strip()


def _clean_title(asset_name, remark):
    """หัวเรื่อง: ใช้ชื่อครุภัณฑ์ก่อน ถ้าไม่มีใช้บรรทัดแรกของหมายเหตุ (ตัด tag [..] ทิ้ง)"""
    asset = (asset_name or "").strip()
    if asset:
        return asset.split(",")[0].strip()[:TITLE_MAX_LEN]

    remark = (remark or "").strip()
    first = remark.splitlines()[0] if remark else ""
    if first.startswith("["):
        first = first.split("]", 1)[-1].strip()
    return (first or "—")[:TITLE_MAX_LEN]


def _type_key(row):
    return (row.get("transfer_type") or row.get("request_typeproblem") or "").strip()


def map_row(d):
    """1 แถวจาก sql.DOCS_LIST → dict สำหรับตารางในหน้า /docs"""
    s_label, s_cls, s_group = config.doc_status(d.get("request_status"))
    t_label, t_cls = config.transfer_type(_type_key(d))

    fname  = (d.get("requester_fname") or "").strip()
    lname  = (d.get("requester_lname") or "").strip()
    rdate  = (d.get("request_date") or "").strip()
    owner  = (d.get("owner_name") or "").strip()
    code   = (d.get("asset_code") or "").strip()
    aname  = (d.get("asset_name") or "").strip()
    remark = (d.get("request_remark") or "").strip()

    subtitle = f"ครุภัณฑ์ {code.split(',')[0].strip()}" if code else (d.get("transfer_type_name") or "")

    return {
        "id":             d.get("request_id"),
        "date":           rdate.split(" ")[0] if rdate else "—",
        "date_full":      rdate or "—",
        "requester":      f"{fname} {lname}".strip() or "—",
        "dept":           (d.get("requester_dept") or "—").strip() or "—",
        "type_label":     t_label,
        "type_cls":       t_cls,
        "status_label":   s_label,
        "status_cls":     s_cls,
        "status_group":   s_group,
        "owner":          owner,
        "owner_initial":  owner[:2] if owner else "",
        "is_doc_process": bool((d.get("transfer_type") or "").strip()),
        "transfer_type_name": d.get("transfer_type_name") or "",
        "asset_code":     code,
        "asset_name":     aname,
        "title":          _clean_title(aname, remark),
        "subtitle":       subtitle,
        "remark":         remark,
    }


def map_detail(d):
    """1 แถวจาก sql.DOCS_DETAIL → หัวเอกสารสำหรับ modal"""
    s_label, s_cls, _ = config.doc_status(d.get("request_status"))
    t_label, t_cls    = config.transfer_type(_type_key(d))

    fname = (d.get("requester_fname") or "").strip()
    lname = (d.get("requester_lname") or "").strip()
    owner = (d.get("owner_name") or "").strip()

    return {
        "id":            d.get("request_id"),
        "date":          fmt_datetime(d.get("request_date")) or "—",
        "type_label":    t_label,
        "type_cls":      t_cls,
        "status_label":  s_label,
        "status_cls":    s_cls,
        "requester":     f"{fname} {lname}".strip() or "—",
        "dept":          (d.get("requester_dept") or "—").strip() or "—",
        "tel":           (d.get("requester_tel") or "").strip(),
        "email":         (d.get("requester_email") or "").strip(),
        "empcode":       (d.get("requester_empcode") or "").strip(),
        "remark":        (d.get("request_remark") or "").strip() or "—",
        "owner":         owner,
        "owner_initial": owner[:2] if owner else "",
        "transfer_type_name": d.get("transfer_type_name") or "",
    }


def map_workflow(rows):
    """แถวจาก sql.WORKFLOW → timeline ของหน้า /docs"""
    steps = []
    for w in rows:
        step   = str(w.get("step_type") or "").strip()
        status = str(w.get("status") or "").strip().lower()
        label, css = WF_STATUS.get(status, (status or "—", "wait"))
        steps.append({
            "label":        STEP_LABEL.get(step, DEFAULT_STEP_LABEL),
            "name":         w.get("approver_name") or "—",
            "date":         fmt_datetime(w.get("approve_date")),
            "status_label": label,
            "cls":          css,
        })
    return steps


def _map_asset_rows(rows):
    """แถวจาก IT_HELPDESK_ASSET → รูปแบบเดียวกับตารางทรัพย์สิน"""
    out = []
    for a in rows:
        code = (a.get("asset_code") or "").strip()
        name = (a.get("asset_name") or "").strip()
        if not (code or name):
            continue
        out.append({
            "code":    code or "—",
            "name":    name or "—",
            "serial":  "",                                  # ตาราง ASSET ไม่มีคอลัมน์ serial
            "remark":  (a.get("asset_remark") or "").strip(),
            "item_no": a.get("item_no"),
        })
    return out


def _split_assets(code, name, serial):
    """เอกสารเก่าเก็บ ASSET_CODE/NAME/SERIAL คั่นด้วย comma → แตกเป็นหลายแถว"""
    def parts(value):
        value = (value or "").strip()
        return [p.strip() for p in value.split(",")] if value else []

    codes, names, serials = parts(code), parts(name), parts(serial)
    out = []
    for i in range(max(len(codes), len(names), len(serials))):
        c  = codes[i]   if i < len(codes)   else ""
        nm = names[i]   if i < len(names)   else ""
        s  = serials[i] if i < len(serials) else ""
        if c or nm or s:
            out.append({"code": c or "—", "name": nm or "—", "serial": s})
    return out


# ── ดึงข้อมูล ────────────────────────────────────────────────────────────────

def fetch_docs():
    """รายการเอกสารทั้งหมด + ตัวเลขการ์ดสถิติ"""
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.DOCS_LIST, {"typeform": config.ASSET_TYPEFORM})
        rows = [map_row(d) for d in db.rows_to_dicts(cur)]

    stats = {"all": len(rows), **{g: 0 for g in STAT_GROUPS}}
    for r in rows:
        if r["status_group"] in stats:
            stats[r["status_group"]] += 1
    return rows, stats


def fetch_doc_detail(req_id):
    """รายละเอียดเอกสาร 1 ใบ — คืน None ถ้าไม่พบ"""
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.DOCS_DETAIL, {"req_id": req_id})
        row = db.row_to_dict(cur)
        if not row:
            return None

        cur.execute(sql.DOCS_ASSETS, {"req_id": req_id})
        assets = _map_asset_rows(db.rows_to_dicts(cur))
        if not assets:   # fallback สำหรับเอกสารเก่า
            assets = _split_assets(row.get("asset_code"),
                                   row.get("asset_name"),
                                   row.get("asset_serial"))

        cur.execute(sql.WORKFLOW, {"req_id": req_id})
        workflow = map_workflow(db.rows_to_dicts(cur))

    return {"doc": map_detail(row), "assets": assets, "workflow": workflow}
