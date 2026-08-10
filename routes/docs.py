# -*- coding: utf-8 -*-
"""หน้าเอกสาร "เบิก / ยืม / โอนย้ายทรัพย์สิน" — REQUEST_TYPEFORM = 4"""
import logging

from flask import Blueprint, render_template

from db import DatabaseError, oracle_msg
from services import docs
from web import api, err_resp, ok_resp

log = logging.getLogger(__name__)

bp = Blueprint("docs", __name__)


@bp.get("/docs")
def page():
    try:
        rows, stats = docs.fetch_docs()
        error = None
    except (DatabaseError, RuntimeError) as exc:
        rows, stats, error = [], {"all": 0, **{g: 0 for g in docs.STAT_GROUPS}}, oracle_msg(exc)
        log.error("[docs] %s", error)
    return render_template("docs_type4.html", rows=rows, stats=stats, error=error)


@bp.get("/api/docs_detail/<req_id>")
@api()
def api_detail(req_id):
    detail = docs.fetch_doc_detail(req_id)
    if not detail:
        return err_resp("ไม่พบเอกสาร")
    return ok_resp(**detail)
