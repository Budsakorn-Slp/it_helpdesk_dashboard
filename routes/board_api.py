# -*- coding: utf-8 -*-
"""API ของบอร์ด: ข้อมูลบอร์ด, โหลด 'เสร็จแล้ว' เพิ่ม, และเอกสารติดตาม"""
from flask import Blueprint, request

import config
import db
import sql
from services import audit, boards, tracking
from web import api, err_resp, json_body, ok_resp

bp = Blueprint("board_api", __name__, url_prefix="/api")

MAX_DONE_PAGE_SIZE = 50


@bp.get("/board/<board_key>")
@api()
def api_board(board_key):
    if board_key not in config.BOARDS:
        return err_resp("ไม่พบบอร์ดนี้")
    return ok_resp(**boards.fetch_board(board_key))


@bp.get("/done_page/<board_key>")
@api(items=[])
def api_done_page(board_key):
    if board_key not in config.BOARDS:
        return err_resp("ไม่พบบอร์ดนี้", items=[])
    try:
        offset = max(0, int(request.args.get("offset", 0)))
        limit  = min(MAX_DONE_PAGE_SIZE, max(1, int(request.args.get("limit", boards.DONE_PAGE_SIZE))))
    except ValueError:
        offset, limit = 0, boards.DONE_PAGE_SIZE

    items = boards.fetch_done_page(board_key, offset, limit)
    return ok_resp(items=items, offset=offset + len(items))


@bp.get("/tracking")
@api(items=[])
def api_tracking():
    with db.db_conn() as conn:
        return ok_resp(items=tracking.fetch_tracking_items(conn.cursor()))


@bp.post("/close_tracking")
@api()
def api_close_tracking():
    (req_id, it_name), error = json_body("request_id", "it_name", required=("request_id", "it_name"))
    if error:
        return err_resp(error)

    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.REQUEST_STATUS_OF, {"req_id": req_id})
        old_status = str(db.scalar(cur, "") or "").strip()

        cur.execute(sql.CLOSE_JOB, {"it_name": it_name, "req_id": req_id})
        cur.execute(sql.UPDATE_APPROVER, {"status": "Done", "actor": it_name, "req_id": req_id})
        if cur.rowcount == 0:
            cur.execute(sql.INSERT_APPROVER,
                        {"req_id": req_id, "actor": it_name, "status": "Done", "type": "IT"})

        audit.log(cur, audit.CLOSE_JOB, req_id=req_id, old_status=old_status,
                  new_status="5", action_by=it_name, action_note="ปิดงานเอกสารติดตาม")
        conn.commit()
    return ok_resp()
