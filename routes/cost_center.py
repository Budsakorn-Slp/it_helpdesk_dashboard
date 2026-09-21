# -*- coding: utf-8 -*-
"""หน้าและ API จัดการ Cost Center (IT_HELPDESK_DEPARTMENT)"""
from flask import Blueprint, render_template, request

import db
import sql
from services import audit, employees
from web import api, err_resp, ok_resp

bp = Blueprint("cost_center", __name__)

VALID_STATUS = ("Active", "Block")
LOG_LIMIT = 20
#: source=bulk (นำเข้าไฟล์) ทับของเดิมได้เลย, single (กรอกทีละรายการ) ต้องส่ง
#  overwrite=True มายืนยันอีกครั้ง — กัน Cost Center ที่พิมพ์ผิดไปทับแผนกอื่น
BULK_SOURCE = "bulk"


def _text_row(d):
    """แถวจาก DB → dict ของ str ที่ตัดช่องว่างแล้ว (None → "")"""
    return {k: ("" if v is None else str(v).strip()) for k, v in d.items()}


@bp.get("/cost-center")
def page():
    return render_template("cost_center.html")


@bp.get("/api/cost-center")
@api(items=[])
def api_list():
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.COST_CENTERS)
        items = [_text_row(d) for d in db.rows_to_dicts(cur)]
    return ok_resp(items=items)


@bp.post("/api/cost-center")
@api()
def api_save():
    data = request.get_json(silent=True) or {}

    def field(name, default=""):
        return str(data.get(name, default) or default).strip()

    company    = field("company")
    costcenter = field("costcenter")
    costdep    = field("costdep")
    dept       = field("dept")
    desc       = field("desc")
    code       = field("code")
    operator   = field("operator")
    source     = field("source", "single")
    status     = field("status", "Active").capitalize()
    overwrite  = source == BULK_SOURCE or bool(data.get("overwrite"))

    if not (company and costcenter and costdep and dept):
        return err_resp("กรุณากรอกข้อมูลที่จำเป็นให้ครบ")
    if status not in VALID_STATUS:
        return err_resp(f'COST_STATUS "{status}" ไม่ถูกต้อง — ต้องเป็น Active หรือ Block')

    params = {
        "company":    company,
        "costcenter": costcenter,
        "costdep":    costdep,
        "dept":       dept,
        "p_desc":     desc or None,
        "status":     status,
        "code":       code or None,
    }

    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.COST_CENTER_ONE, {"costcenter": costcenter})
        current = db.row_to_dict(cur)
        exists = current is not None

        # ยังไม่ยืนยัน → ส่งค่าเดิมกลับไปให้หน้าเว็บถามก่อนว่าจะทับหรือไม่
        if exists and not overwrite:
            return err_resp(
                f'Cost Center "{costcenter}" มีอยู่ในระบบแล้ว — ยืนยันเพื่ออัปเดตทับข้อมูลเดิม',
                duplicate=True,
                current=_text_row(current),
            )

        actor_name = employees.resolve_name(cur, operator)

        cur.execute(sql.UPDATE_COST_CENTER if exists else sql.INSERT_COST_CENTER, params)
        action = "อัปเดต" if exists else "บันทึก"

        audit.log(
            cur, audit.COST_CENTER,
            action_by=actor_name,
            action_note=(
                f"Cost Center: {costcenter} | รหัสแผนก: {costdep} | ชื่อแผนก: {dept} | "
                f"บริษัท: {company} | รายละเอียด: {desc} | สถานะ: {status} | "
                f"source: {source} | mode: {action}"
            ),
        )
        conn.commit()

    return ok_resp(msg=f'{action} Cost Center "{costcenter}" เรียบร้อย', updated=exists)


@bp.get("/api/cost-center/logs")
@api(items=[])
def api_logs():
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.LOGS_BY_TYPE, {"action_type": audit.COST_CENTER, "max_rows": LOG_LIMIT})
        items = [_text_row(d) for d in db.rows_to_dicts(cur)]
    return ok_resp(items=items)
