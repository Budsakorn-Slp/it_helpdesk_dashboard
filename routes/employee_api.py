# -*- coding: utf-8 -*-
"""API รายชื่อพนักงาน IT"""
from flask import Blueprint

import db
from services import employees
from web import api, ok_resp

bp = Blueprint("employee_api", __name__, url_prefix="/api")


@bp.get("/employees")
@api(employees=[])
def api_employees():
    """ชื่อ IT สำหรับ modal รับงาน / ปิดงาน / อนุมัติ / ยกเลิก"""
    with db.db_conn() as conn:
        return ok_resp(employees=employees.names(conn.cursor()))


@bp.get("/it_employees")
@api(items=[])
def api_it_employees():
    """รหัส + ชื่อ IT ที่สถานะ Current — ใช้เป็นผู้ดำเนินการตอนเปลี่ยนสถานะ"""
    with db.db_conn() as conn:
        return ok_resp(items=employees.current(conn.cursor()))
