# -*- coding: utf-8 -*-
"""หน้า HTML: หน้าแรก, บอร์ด, และไฟล์แนบ"""
import logging
from datetime import date

from flask import Blueprint, abort, render_template, request, send_from_directory, url_for

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


def _list_url_builder(board_key, filters):
    """สร้างตัวช่วยทำ URL ให้ template — คงตัวกรองอื่นไว้เสมอ

    ค่าที่เป็นค่าตั้งต้นจะไม่ใส่ลง URL เพื่อให้ลิงก์สั้นและอ่านง่าย
    """
    def build(**overrides):
        args = {
            "flow": filters["flow"],
            "cat":  filters["cat"],
            "q":    filters["q"],
            "days": filters["days"],
            "sort": filters["sort"],
            "dir":  filters["dir"],
            "size": filters["size"],
            "page": 1,          # เปลี่ยนตัวกรองแล้วต้องกลับหน้า 1
        }
        args.update(overrides)

        clean = {k: v for k, v in args.items() if v not in ("", None, 0)}
        if not clean.get("sort"):
            clean.pop("dir", None)          # ทิศทางไม่มีความหมายถ้าไม่ได้เรียง
        if clean.get("size") == asset_list.DEFAULT_PAGE_SIZE:
            clean.pop("size", None)
        if clean.get("page") == 1:
            clean.pop("page", None)
        return url_for("pages.board", board_key=board_key, **clean)

    return build


def _render_list(board_key, cfg):
    """หน้ารายการเอกสาร — กรอง เรียง และแบ่งหน้าที่ฝั่งฐานข้อมูล

    ตัวกรองทั้งหมดอยู่ใน query string จึงบุ๊กมาร์กและกดปุ่มย้อนกลับได้
    """
    filters = asset_list.parse_filters(request.args)

    error = None
    try:
        counts = asset_list.fetch_counts()
        rows, total, filters["page"] = asset_list.fetch_page(filters)
    except (DatabaseError, RuntimeError) as exc:
        error = oracle_msg(exc)
        counts, rows, total = asset_list.empty_counts(), [], 0
        log.error("[list:%s] %s", board_key, error)

    return render_template(
        "asset_list.html",
        board_key=board_key,
        cfg=cfg,
        rows=rows,
        filters=filters,
        list_url=_list_url_builder(board_key, filters),
        pager=asset_list.build_pager(filters["page"], filters["size"], total),
        counts=counts,
        status_nav=asset_list.build_status_nav(counts),
        nav=asset_list.build_nav(counts),
        status_map=config.STATUS_MAP,
        transfer_type_labels=config.TRANSFER_TYPE_LABELS,
        error=error,
    )
