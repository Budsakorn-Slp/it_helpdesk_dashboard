# -*- coding: utf-8 -*-
"""พนักงาน IT (IT_HELPDESK_ITEMPLOYEE)"""
import db
import sql


def names(cur):
    """ชื่อจริงของพนักงาน IT ทุกคน — ใช้เติม dropdown ใน modal"""
    cur.execute(sql.IT_EMPLOYEE_NAMES)
    return [row[0] for row in cur.fetchall() if row[0]]


def current(cur):
    """พนักงาน IT ที่ยังทำงานอยู่ พร้อมรหัส — ใช้เป็นผู้ดำเนินการ"""
    cur.execute(sql.IT_EMPLOYEES)
    return [
        {"emp_id": str(emp_id), "first_name": str(first_name).strip()}
        for emp_id, first_name in cur.fetchall()
        if emp_id and first_name
    ]


def resolve_name(cur, emp_id):
    """รหัสพนักงาน → ชื่อ-นามสกุล (คืนรหัสเดิมถ้าหาไม่เจอ)

    ใช้เก็บ "ชื่อ" ลงคอลัมน์ UPDATED_BY / ACTION_BY แทนการเก็บรหัส
    """
    if not emp_id:
        return ""
    cur.execute(sql.IT_EMPLOYEE_FULLNAME, {"emp_id": emp_id})
    name = db.scalar(cur)
    return str(name).strip() if name else emp_id
