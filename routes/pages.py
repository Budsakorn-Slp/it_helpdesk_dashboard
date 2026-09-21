# -*- coding: utf-8 -*-
"""หน้า HTML: หน้าแรก, บอร์ด, และไฟล์แนบ"""
import logging
from datetime import date

from flask import Blueprint, abort, render_template, request, send_from_directory, url_for

import config
from db import DatabaseError, oracle_msg
from services import asset_list, boards, dashboard

log = logging.getLogger(__name__)

bp = Blueprint("pages", __name__)


@bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(config.UPLOAD_FOLDER, filename)


@bp.route("/")
def index():
    """หน้าแรก — ภาพรวมเอกสารทุกบอร์ด ดูอย่างเดียว แก้ไขไม่ได้"""
    filters = asset_list.parse_filters(request.args, tracking=True)

    error = None
    try:
        counts, rows, total, filters["page"] = dashboard.fetch(filters)
    except (DatabaseError, RuntimeError) as exc:
        error = oracle_msg(exc)
        counts, rows, total, filters["page"] = dashboard.empty()
        log.error("[dashboard] %s", error)

    return render_template(
        "dashboard.html",
        rows=rows,
        filters=filters,
        list_url=_list_url_builder(None, filters),
        pager=asset_list.build_pager(filters["page"], filters["size"], total),
        counts=counts,
        cards=dashboard.build_cards(counts),
        menu=dashboard.build_menu(),
        status_map=config.STATUS_MAP,
        transfer_type_labels=config.TRANSFER_TYPE_LABELS,
        error=error,
    )


@bp.route("/<board_key>")
def board(board_key):
    cfg = config.BOARDS.get(board_key)
    if not cfg:
        abort(404)

    if config.resolve_view(board_key, request.args.get("view")) == config.VIEW_LIST:
        return _render_list(board_key, cfg, config.list_view(board_key))

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
        list_view_boards=tuple(config.LIST_VIEWS),
        today_str=date.today().strftime("%Y-%m-%d"),
        error=error,
        **data,
    )


def _list_url_builder(board_key, filters):
    """สร้างตัวช่วยทำ URL ให้ template — คงตัวกรองอื่นไว้เสมอ

    board_key = None หมายถึงหน้าแรก (/) ที่รวมทุกบอร์ด
    ค่าที่เป็นค่าตั้งต้นจะไม่ใส่ลง URL เพื่อให้ลิงก์สั้นและอ่านง่าย

    บอร์ดที่ตั้งต้นเป็น kanban ต้องพา view=list ไปทุกลิงก์
    ไม่งั้นพอกดกรองหรือเปลี่ยนหน้าจะเด้งกลับไปหน้าบอร์ด
    """
    keep_view = (board_key is not None
                 and config.resolve_view(board_key, None) != config.VIEW_LIST)

    def build(**overrides):
        args = {
            "flow": filters["flow"],
            "cat":  filters["cat"],
            "fwd":  filters["fwd"],
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
        if board_key is None:
            return url_for("pages.index", **clean)
        if keep_view:
            clean["view"] = config.VIEW_LIST
        return url_for("pages.board", board_key=board_key, **clean)

    return build


def _render_list(board_key, cfg, view):
    """หน้ารายการเอกสาร — กรอง เรียง และแบ่งหน้าที่ฝั่งฐานข้อมูล

    ตัวกรองทั้งหมดอยู่ใน query string จึงบุ๊กมาร์กและกดปุ่มย้อนกลับได้
    view = ค่าตั้งของบอร์ดนี้จาก config.LIST_VIEWS
    """
    tracking = bool(view.get("tracking"))
    typeform = cfg["typeform"]
    filters = asset_list.parse_filters(request.args, tracking=tracking)

    error = None
    try:
        counts = asset_list.fetch_counts(typeform)
        rows, total, filters["page"] = asset_list.fetch_page(filters, typeform)
    except (DatabaseError, RuntimeError) as exc:
        error = oracle_msg(exc)
        counts, rows, total = asset_list.empty_counts(), [], 0
        log.error("[list:%s] %s", board_key, error)

    # บอร์ดที่ตั้งต้นเป็น kanban ต้องคง view=list ไว้ในฟอร์มค้นหาและปุ่มล้างตัวกรอง
    keep_view = config.resolve_view(board_key, None) != config.VIEW_LIST
    reset_args = {"view": config.VIEW_LIST} if keep_view else {}

    return render_template(
        "asset_list.html",
        board_key=board_key,
        cfg=cfg,
        tracking=tracking,
        rows=rows,
        filters=filters,
        keep_view=keep_view,
        reset_url=url_for("pages.board", board_key=board_key, **reset_args),
        list_url=_list_url_builder(board_key, filters),
        pager=asset_list.build_pager(filters["page"], filters["size"], total),
        counts=counts,
        status_nav=asset_list.build_status_nav(counts, tracking),
        nav=asset_list.build_nav(counts) if tracking else [],
        status_map=config.STATUS_MAP,
        transfer_type_labels=config.TRANSFER_TYPE_LABELS,
        error=error,
    )
