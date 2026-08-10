# -*- coding: utf-8 -*-
"""API ของคำขอ 1 ใบ: รายละเอียด, คอมเมนต์, ลำดับอนุมัติ และการกระทำกับงาน"""
from datetime import datetime

from flask import Blueprint

import config
import db
import sql
from services import audit, employees, tracking
from web import api, err_resp, json_body, ok_resp

bp = Blueprint("request_api", __name__, url_prefix="/api")

DONE_STATUS   = "5"
CANCEL_STATUS = "3"
DOING_STATUS  = "2"
READY_STATUS  = "1"


def _set_approver(cur, req_id, status, actor, type_="IT"):
    """อัปเดตแถวอนุมัติ ถ้ายังไม่มีให้สร้างใหม่"""
    cur.execute(sql.UPDATE_APPROVER, {"status": status, "actor": actor, "req_id": req_id})
    if cur.rowcount == 0:
        cur.execute(sql.INSERT_APPROVER,
                    {"req_id": req_id, "actor": actor, "status": status, "type": type_})


def _current_status(cur, req_id):
    cur.execute(sql.REQUEST_STATUS_OF, {"req_id": req_id})
    return db.scalar(cur)


# ── รายละเอียด ───────────────────────────────────────────────────────────────

@bp.get("/detail/<req_id>")
@api()
def api_detail(req_id):
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.REQUEST_DETAIL, {"req_id": req_id})
        d = db.row_to_dict(cur)
        if not d:
            return err_resp("ไม่พบ REQUEST_ID")

        d["request_status"] = str(d.get("request_status") or "0")
        d = db.blank_none(d)

        cur.execute(sql.TRANSFER_FOR_REQUEST, {"req_id": req_id})
        transfer = db.row_to_dict(cur)
        d["is_tracking"]       = bool(transfer)
        d["transfer_complete"] = tracking.is_complete(transfer) if transfer else False

        cur.execute(sql.LATEST_APPROVER_FOR_REQUEST, {"req_id": req_id})
        approver = db.scalar(cur)
        d["approver_status"] = str(approver or "Waiting").strip()

    return ok_resp(data=d)


@bp.get("/approvers/<req_id>")
@api(items=[])
def api_approvers(req_id):
    """คำขอที่มีเอกสารโอนย้าย → แสดงลายเซ็นบนเอกสาร
    คำขอทั่วไป → แสดง approver chain ตามปกติ
    """
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.TRANSFER_SIGNATURES, {"req_id": req_id})
        signature_row = cur.fetchone()
        if signature_row:
            return ok_resp(items=tracking.build_signature_steps(signature_row))

        cur.execute(sql.WORKFLOW, {"req_id": req_id})
        items = [
            {"title": step or "-", "by": name or "-",
             "date": str(when or ""), "status": status or "waiting"}
            for step, name, when, status in cur.fetchall()
        ]
    return ok_resp(items=items)


# ── คอมเมนต์ ─────────────────────────────────────────────────────────────────

@bp.get("/comments/<req_id>")
@api(comments=[])
def api_comments(req_id):
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.COMMENTS, {"req_id": req_id})
        comments = [db.blank_none(d) for d in db.rows_to_dicts(cur)]
    return ok_resp(comments=comments)


@bp.post("/comment")
@api()
def api_comment():
    (req_id, comment, comment_by), error = json_body(
        "request_id", "comment", "comment_by", required=("request_id", "comment", "comment_by"))
    if error:
        return err_resp("กรุณากรอกคอมเมนต์และเลือกชื่อผู้คอมเมนต์")

    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.INSERT_COMMENT,
                    {"req_id": req_id, "comment_text": comment, "comment_by": comment_by})
        cur.execute(sql.UPDATE_LATEST_COMMENT,
                    {"comment_text": comment, "comment_by": comment_by, "req_id": req_id})
        conn.commit()
    return ok_resp(comment_date=datetime.now().strftime("%d/%m/%Y %H:%M"))


# ── การกระทำกับงาน ───────────────────────────────────────────────────────────

@bp.post("/start")
@api()
def api_start():
    (req_id, worker), error = json_body("request_id", "worker", required=("request_id", "worker"))
    if error:
        return err_resp(error)

    with db.db_conn() as conn:
        cur = conn.cursor()
        old_status = _current_status(cur, req_id)
        cur.execute(sql.START_JOB, {"worker": worker, "req_id": req_id})
        audit.log(cur, audit.START_JOB, req_id=req_id, old_status=old_status,
                  new_status=DOING_STATUS, action_by=worker, action_note="รับงาน")
        conn.commit()
    return ok_resp()


@bp.post("/close")
@api()
def api_close():
    (req_id, it_name), error = json_body("request_id", "it_name", required=("request_id",))
    if error:
        return err_resp(error)

    with db.db_conn() as conn:
        cur = conn.cursor()
        old_status = _current_status(cur, req_id)
        # it_name ว่าง → SQL จะ fallback ไปใช้ REQUEST_ACTION (ผู้รับผิดชอบเดิม)
        cur.execute(sql.CLOSE_JOB, {"it_name": it_name or None, "req_id": req_id})
        _set_approver(cur, req_id, "Done", it_name or "SYSTEM")
        audit.log(cur, audit.CLOSE_JOB, req_id=req_id, old_status=old_status,
                  new_status=DONE_STATUS, action_by=it_name or "SYSTEM", action_note="ปิดงาน")
        conn.commit()
    return ok_resp()


@bp.post("/approve_it")
@api()
def api_approve_it():
    (req_id, it_name), error = json_body("request_id", "it_name", required=("request_id",))
    if error:
        return err_resp(error)

    actor = it_name or "IT"
    with db.db_conn() as conn:
        cur = conn.cursor()
        old_status = _current_status(cur, req_id)
        _set_approver(cur, req_id, "Approve", actor)
        cur.execute(sql.APPROVE_JOB, {"req_id": req_id})
        audit.log(cur, audit.IT_APPROVE, req_id=req_id, old_status=old_status,
                  new_status=READY_STATUS, action_by=actor, action_note="IT อนุมัติ")
        conn.commit()
    return ok_resp()


@bp.post("/cancel_it")
@api()
def api_cancel_it():
    (req_id, it_name), error = json_body("request_id", "it_name", required=("request_id",))
    if error:
        return err_resp(error)

    with db.db_conn() as conn:
        cur = conn.cursor()
        old_status = _current_status(cur, req_id)
        _set_approver(cur, req_id, "Reject", it_name)
        cur.execute(sql.CANCEL_JOB, {"it_name": it_name, "req_id": req_id})
        audit.log(cur, audit.IT_CANCEL, req_id=req_id, old_status=old_status,
                  new_status=CANCEL_STATUS, action_by=it_name, action_note="IT ยกเลิก")
        conn.commit()
    return ok_resp()


@bp.post("/change_status")
@api()
def api_change_status():
    (req_id, new_status, action_by, action_note), error = json_body(
        "request_id", "new_status", "action_by", "action_note",
        required=("request_id", "new_status", "action_by"))
    if error:
        return err_resp(error)
    if new_status not in config.STATUS_MAP:
        return err_resp(f'สถานะ "{new_status}" ไม่ถูกต้อง')

    with db.db_conn() as conn:
        cur = conn.cursor()
        old_status = _current_status(cur, req_id)
        if old_status is None:
            return err_resp("ไม่พบคำขอนี้")
        old_status = str(old_status or "").strip()

        actor_name = employees.resolve_name(cur, action_by)

        statement = sql.CHANGE_STATUS_CLOSING if new_status == DONE_STATUS else sql.CHANGE_STATUS
        cur.execute(statement,
                    {"new_status": new_status, "actor_name": actor_name, "req_id": req_id})

        _set_approver(cur, req_id,
                      config.APPROVER_STATUS_BY_REQUEST_STATUS.get(new_status, "Waiting"),
                      actor_name)

        audit.log(cur, audit.CHANGE_STATUS, req_id=req_id, old_status=old_status,
                  new_status=new_status, action_by=actor_name, action_note=action_note)
        conn.commit()
    return ok_resp(actor_name=actor_name)
