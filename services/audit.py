# -*- coding: utf-8 -*-
"""บันทึกการเปลี่ยนแปลงลง IT_HELPDESK_LOG"""
import sql

#: ACTION_TYPE ที่ระบบใช้
IT_APPROVE    = "IT_APPROVE"
IT_CANCEL     = "IT_CANCEL"
START_JOB     = "START_JOB"
CLOSE_JOB     = "CLOSE_JOB"
CHANGE_STATUS = "CHANGE_STATUS"
COST_CENTER   = "COST_CENTER"


def log(cur, action_type, req_id=None, old_status=None, new_status=None,
        action_by=None, action_note=None):
    """เขียน 1 แถวลง audit log — ต้องเรียกภายใน transaction เดียวกับงานหลัก"""
    cur.execute(sql.INSERT_LOG, {
        "req_id":      req_id if req_id is not None else 0,
        "action_type": action_type,
        "old_status":  old_status,
        "new_status":  new_status,
        "action_by":   action_by,
        "action_note": action_note,
    })
