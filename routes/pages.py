# -*- coding: utf-8 -*-
"""หน้า HTML: หน้าแรก, บอร์ด, และไฟล์แนบ"""
import logging
from datetime import date

from flask import Blueprint, abort, render_template, send_from_directory

import config
from db import DatabaseError, oracle_msg
from services import boards

log = logging.getLogger(__name__)

bp = Blueprint("pages", __name__)


@bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(config.UPLOAD_FOLDER, filename)


@bp.route("/")
def index():
    return render_template("index.html", boards=config.BOARDS)


@bp.route("/<board_key>")
def board(board_key):
    cfg = config.BOARDS.get(board_key)
    if not cfg:
        abort(404)

    error = None
    try:
        data = boards.fetch_board(board_key)
    except (DatabaseError, RuntimeError) as exc:
        error = oracle_msg(exc)
        data = boards.empty_board()
        log.error("[board:%s] %s", board_key, error)

    return render_template(
        "board.html",
        board_key=board_key,
        cfg=cfg,
        status_map=config.STATUS_MAP,
        transfer_type_labels=config.TRANSFER_TYPE_LABELS,
        today_str=date.today().strftime("%Y-%m-%d"),
        error=error,
        **data,
    )
