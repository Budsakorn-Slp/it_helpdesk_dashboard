# -*- coding: utf-8 -*-
"""หน้า HTML: หน้าแรก, บอร์ด, และไฟล์แนบ"""
import logging
from datetime import date

from flask import Blueprint, abort, render_template, request, send_from_directory

import config
from db import DatabaseError, oracle_msg
from services import asset_list, boards

log = logging.getLogger(__name__)

bp = Blueprint("pages", __name__)

#: บอร์ดที่แสดงเป็นรายการเอกสารแทน kanban (เปิดบอร์ดเดิมได้ด้วย ?view=board)
LIST_VIEW_BOARDS = ("asset",)


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

    if board_key in LIST_VIEW_BOARDS and request.args.get("view") != "board":
        return _render_list(board_key, cfg)

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
        list_view_boards=LIST_VIEW_BOARDS,
        today_str=date.today().strftime("%Y-%m-%d"),
        error=error,
        **data,
    )


def _render_list(board_key, cfg):
    """หน้ารายการเอกสาร — ใช้แทนบอร์ด kanban สำหรับบอร์ดใน LIST_VIEW_BOARDS"""
    error = None
    try:
        rows, stats = asset_list.fetch_rows()
    except (DatabaseError, RuntimeError) as exc:
        error = oracle_msg(exc)
        rows, stats = asset_list.empty()
        log.error("[list:%s] %s", board_key, error)

    return render_template(
        "asset_list.html",
        board_key=board_key,
        cfg=cfg,
        rows=rows,
        stats=stats,
        nav=asset_list.build_nav(rows),
        status_map=config.STATUS_MAP,
        transfer_type_labels=config.TRANSFER_TYPE_LABELS,
        error=error,
    )
