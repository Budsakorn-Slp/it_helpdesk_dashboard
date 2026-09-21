# -*- coding: utf-8 -*-
"""API ของบอร์ด: ข้อมูลบอร์ด, โหลด 'เสร็จแล้ว' เพิ่ม, และเอกสารติดตาม"""
from flask import Blueprint, request

import config
import db
import sql
from services import attachments, audit, boards, tracking
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


#: ชื่อ field ของไฟล์ที่แนบมาตอนปิดงานทั้งที่ลายเซ็นในระบบยังไม่ครบ
SIGNED_DOC_FIELD = "signed_doc"


def _close_tracking_input():
    """อ่าน request_id / it_name ได้ทั้งแบบ JSON และ multipart (ตอนแนบไฟล์)

    คืน (req_id, it_name, error)
    """
    if request.files:
        req_id  = str(request.form.get("request_id") or "").strip()
        it_name = str(request.form.get("it_name") or "").strip()
        missing = [f for f, v in (("request_id", req_id), ("it_name", it_name)) if not v]
        error = ("ข้อมูลไม่ครบ: " + ", ".join(missing)) if missing else None
        return req_id, it_name, error

    (req_id, it_name), error = json_body("request_id", "it_name",
                                         required=("request_id", "it_name"))
    return req_id, it_name, error


@bp.post("/close_tracking")
@api()
def api_close_tracking():
    """ปิดงานเอกสารติดตาม

    ปกติปิดได้เมื่อลายเซ็นในระบบครบแล้ว แต่มีกรณีที่ผู้เซ็นลงนามบนกระดาษจริง
    โดยไม่ได้กดยืนยันในไลน์ ลายเซ็นในระบบจึงไม่ครบทั้งที่งานเสร็จแล้ว
    กรณีนี้ IT ปิดงานเองได้ แต่ต้องแนบรูปเอกสารที่มีลายเซ็นมาเป็นหลักฐาน
    """
    req_id, it_name, error = _close_tracking_input()
    if error:
        return err_resp(error)

    signed_doc = request.files.get(SIGNED_DOC_FIELD)

    with db.db_conn() as conn:
        cur = conn.cursor()

        # ตัดสินจากข้อมูลใน DB ไม่ใช่จากที่หน้าจอส่งมา — กันการปิดงานข้ามเงื่อนไข
        cur.execute(sql.TRANSFER_FOR_REQUEST, {"req_id": req_id})
        transfer = db.row_to_dict(cur)
        complete = tracking.is_complete(transfer) if transfer else False

        if not complete and not signed_doc:
            return err_resp("ลายเซ็นบนเอกสารยังไม่ครบ — ต้องแนบรูปเอกสารที่มีลายเซ็นจึงจะปิดงานได้")

        note = "ปิดงานเอกสารติดตาม"
        if signed_doc:
            try:
                saved = attachments.save(cur, req_id, signed_doc, it_name)
            except attachments.UploadError as exc:
                return err_resp(str(exc))
            if not complete:
                note = f"ปิดงานเอกสารติดตาม (ลายเซ็นในระบบไม่ครบ — แนบเอกสารลายเซ็น {saved['label']})"
            else:
                note = f"ปิดงานเอกสารติดตาม (แนบเอกสารลายเซ็น {saved['label']})"

        cur.execute(sql.REQUEST_STATUS_OF, {"req_id": req_id})
        old_status = str(db.scalar(cur, "") or "").strip()

        cur.execute(sql.CLOSE_JOB, {"it_name": it_name, "req_id": req_id})
        cur.execute(sql.UPDATE_APPROVER, {"status": "Done", "actor": it_name, "req_id": req_id})
        if cur.rowcount == 0:
            cur.execute(sql.INSERT_APPROVER,
                        {"req_id": req_id, "actor": it_name, "status": "Done", "type": "IT"})

        # ACTION_NOTE เป็น VARCHAR2(500) — ชื่อไฟล์ยาว ๆ ทำให้เกินได้
        audit.log(cur, audit.CLOSE_JOB, req_id=req_id, old_status=old_status,
                  new_status="5", action_by=it_name, action_note=note[:500])
        conn.commit()
    return ok_resp()
