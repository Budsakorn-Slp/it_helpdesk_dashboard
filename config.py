# -*- coding: utf-8 -*-
"""ค่าตั้งต้นของระบบ — อ่านค่าที่เปลี่ยนตามเครื่อง (dev/prod) จาก .env

ไฟล์นี้เป็นแหล่งความจริงเดียวของค่าคงที่ทั้งระบบ (สถานะ / บอร์ด / ประเภทเอกสาร)
โมดูลอื่นต้อง import จากที่นี่ ห้ามประกาศซ้ำ
"""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _env(key, default=""):
    """อ่านค่าจาก environment — ถ้าตั้งไว้เป็นค่าว่างให้ถือว่าไม่ได้ตั้ง

    จำเป็นเพราะ .env มักเขียน KEY= ทิ้งไว้เฉย ๆ ซึ่ง os.getenv จะคืน ""
    ไม่ใช่ค่า default ที่ต้องการ
    """
    value = os.getenv(key)
    return value.strip() if value and value.strip() else default


def _env_bool(key, default=False):
    return _env(key, str(default)).lower() in ("1", "true", "yes", "on")


# ── Oracle ───────────────────────────────────────────────────────────────────
# ไม่ใส่ค่า default ของ user/password ในโค้ด — ต้องมาจาก .env เท่านั้น (ดู .env.example)
ORACLE_USER     = _env("ORACLE_USER")
ORACLE_PASSWORD = _env("ORACLE_PASSWORD")
ORACLE_DSN      = _env("ORACLE_DSN")

# โฟลเดอร์ Oracle Instant Client (thick mode — จำเป็นสำหรับ Oracle 11g)
#   dev  (Windows) : C:\instantclient_11_2
#   prod (Linux)   : /opt/oracle/instantclient_21_21
ORACLE_LIB_DIR = _env("ORACLE_LIB_DIR")

# บังคับเลือก driver ได้ด้วย ORACLE_DRIVER=oracledb|cx_Oracle
# ถ้าไม่ระบุ จะลอง oracledb ก่อนแล้วค่อย fallback ไป cx_Oracle
ORACLE_DRIVER = _env("ORACLE_DRIVER")

# ── Flask ────────────────────────────────────────────────────────────────────
HOST  = _env("FLASK_HOST", "0.0.0.0")
PORT  = int(_env("FLASK_PORT", "5093"))
DEBUG = _env_bool("FLASK_DEBUG", False)

# โฟลเดอร์ไฟล์แนบ — ใช้ร่วมกับระบบ it_helpdesk ที่อยู่ระดับเดียวกัน
UPLOAD_FOLDER = os.path.abspath(_env(
    "UPLOAD_FOLDER",
    os.path.join(BASE_DIR, "..", "it_helpdesk", "static", "uploads"),
))

# ── สถานะคำขอ (IT_HELPDESK_REQUEST.REQUEST_STATUS) ───────────────────────────
STATUS_MAP = {
    "0":  "รอดำเนินการ",
    "1":  "พร้อมทำ",
    "2":  "กำลังทำ",
    "3":  "ยกเลิก",
    "4":  "รออนุมัติ",
    "5":  "เสร็จ",
    "7":  "รอสั่งซื้อ",
    "8":  "รอยืนยัน",
    "10": "ส่งซ่อม",
    "11": "ยืม",
}

# REQUEST_STATUS → IT_HELPDESK_APPROVER.STATUS ที่ควรจะเป็นคู่กัน
APPROVER_STATUS_BY_REQUEST_STATUS = {
    "5":  "Done",
    "3":  "Reject",
    "2":  "Approve",   # กำลังทำ — IT รับงานแล้ว
    "1":  "Approve",   # พร้อมทำ — อนุมัติแล้ว
    "4":  "Waiting",   # รออนุมัติ
    "0":  "Waiting",   # รอดำเนินการ
    "7":  "Waiting",   # รอสั่งซื้อ
    "8":  "Waiting",   # รอยืนยัน
    "10": "Waiting",   # ส่งซ่อม
    "11": "Waiting",   # ยืม
}

# ── บอร์ด (แต่ละบอร์ด = REQUEST_TYPEFORM หนึ่งค่า) ──────────────────────────
BOARDS = {
    "network": {"title": "Network / Internet",       "typeform": "2", "color": "#1a5276"},
    "system":  {"title": "System / โปรแกรม",         "typeform": "3", "color": "#1a3a6e"},
    "support": {"title": "Support / คอมพิวเตอร์",    "typeform": "1", "color": "#154360"},
    "asset":   {"title": "เบิก / ยืม / โอนย้าย",     "typeform": "4", "color": "#6c3483"},
    "newreq":  {"title": "ขอแก้ไข / ขอโปรแกรมใหม่",  "typeform": "5", "color": "#1a6b3c"},
}

# typeform ของบอร์ด asset — ใช้ทั้งหน้าบอร์ดและหน้าเอกสาร /docs
ASSET_TYPEFORM = BOARDS["asset"]["typeform"]

# บอร์ดที่ต้องดึงสถานะเอกสาร (IT_HELPDESK_TRANSFER) มาประกอบ
TRACKING_BOARDS = ("asset",)

# ── มุมมองของแต่ละบอร์ด ─────────────────────────────────────────────────────
#
#   default  = มุมมองที่เปิดขึ้นมาตอนแรก  "board" (kanban) หรือ "list" (ตาราง)
#   tracking = บอร์ดนี้มีใบโอนย้ายให้ติดตามหรือไม่
#              ถ้าไม่มี หน้ารายการจะซ่อนสถานะ "ติดตามเอกสาร" เมนูหมวดหมู่เอกสาร
#              และคอลัมน์ประเภท (เพราะไม่มีข้อมูลประเภทให้แสดง)
#
# ทุกบอร์ดสลับมุมมองได้เสมอด้วย ?view=board หรือ ?view=list
VIEW_BOARD = "board"
VIEW_LIST  = "list"

LIST_VIEWS = {
    # ทีมที่ทำงานบนกระดานเป็นหลัก — เปิดมาเป็น kanban
    "support": {"tracking": False, "default": VIEW_BOARD},
    "network": {"tracking": False, "default": VIEW_BOARD},
    "system":  {"tracking": False, "default": VIEW_BOARD},
    # งานเอกสารที่มีจำนวนมาก — เปิดมาเป็นตาราง
    "asset":   {"tracking": True,  "default": VIEW_LIST},   # บอร์ดเดียวที่มีใบโอนย้าย
    "newreq":  {"tracking": False, "default": VIEW_LIST},
}


def list_view(board_key):
    """ค่าตั้งมุมมองของบอร์ดนี้ (None ถ้าบอร์ดนี้ไม่มีหน้ารายการ)"""
    return LIST_VIEWS.get(board_key)


def resolve_view(board_key, requested):
    """ตัดสินว่าจะแสดงมุมมองไหน — ค่าจาก URL มาก่อน ถ้าไม่ระบุใช้ค่าตั้งต้นของบอร์ด"""
    view = LIST_VIEWS.get(board_key)
    if not view:
        return VIEW_BOARD
    if requested in (VIEW_BOARD, VIEW_LIST):
        return requested
    return view["default"]


def board_of_typeform(typeform):
    """REQUEST_TYPEFORM → board_key (None ถ้าไม่มีบอร์ดรองรับ)"""
    typeform = str(typeform or "").strip()
    for key, cfg in BOARDS.items():
        if cfg["typeform"] == typeform:
            return key
    return None

# ลำดับการเรียงการ์ดในบอร์ด
ORDER_PRIORITY = {"ready": 1, "doing": 2, "tracking": 3, "done": 4, "waiting": 5, "cancel": 6}

WORKFLOW_STATUSES = ("ready", "doing", "done", "waiting", "cancel", "tracking")

# ── การจัดหมวดเอกสารทรัพย์สิน ───────────────────────────────────────────────
#
# ฟอร์ม /form/4 ให้เลือก "ประเภทการดำเนินการ" ก่อน (เบิก / ยืม / โอนย้าย)
# แล้วเก็บไว้ที่ IT_HELPDESK_REQUEST.REQUEST_TYPEPROBLEM
#
# คำขอจะนับเป็น "ใบโอนย้าย" ก็ต่อเมื่อ **มีแถวใน IT_HELPDESK_TRANSFER** เท่านั้น
#   • เบิก (WITHDRAW) และยืมแบบตรง ไม่สร้างใบโอนย้าย → เป็นคำขอทั่วไป
#   • เมื่อติ๊กโอนย้าย ระบบจะสร้างใบโอนย้าย แล้วแยกเป็น 5 ประเภทด้านล่าง
#
# ป้ายภาษาไทยตรงกับ IT_HELPDESK_TRANSFER.TRANSFER_TYPE_NAME ในฐานข้อมูล

GROUP_TRANSFER = "transfer"   # มีใบโอนย้าย
GROUP_REQUEST  = "request"    # คำขอทั่วไป ไม่มีใบโอนย้าย

#: 5 ประเภทของใบโอนย้าย (IT_HELPDESK_TRANSFER.TRANSFER_TYPE)
TRANSFER_DOC_TYPES = {
    "TRANSFER": {"label": "โอนย้ายระหว่างหน่วยงาน", "cls": "transfer"},
    "DISPOSE":  {"label": "ตัดบัญชี / สูญหาย",      "cls": "dispose"},
    "SALE":     {"label": "เพื่อขาย",               "cls": "sale"},
    "REPAIR":   {"label": "ส่งซ่อม",                "cls": "repair"},
    "BORROW":   {"label": "ยืม",                    "cls": "borrow"},
}

#: BORROW_DIRECT เป็นรหัสเก่าของ "ยืม" — นับรวมเป็นหมวดเดียวกัน
TRANSFER_TYPE_ALIASES = {"BORROW_DIRECT": "BORROW"}

#: ประเภทคำขอที่ไม่ได้สร้างใบโอนย้าย
PLAIN_REQUEST_TYPES = {
    "WITHDRAW": {"label": "เบิก", "cls": "withdraw"},
    "BORROW":   {"label": "ยืม",  "cls": "borrow"},
}
UNKNOWN_REQUEST_TYPE = {"label": "ไม่ระบุ", "cls": "unknown"}

#: ป้ายที่ฝั่ง JS ใช้ (กล่องติดตามเอกสารในบอร์ด)
TRANSFER_TYPE_LABELS = {
    **{k: v["label"] for k, v in TRANSFER_DOC_TYPES.items()},
    **{alias: TRANSFER_DOC_TYPES[target]["label"]
       for alias, target in TRANSFER_TYPE_ALIASES.items()},
}


def canonical_transfer_type(code):
    """รวมรหัสที่มีความหมายเดียวกันให้เหลือรหัสเดียว"""
    code = str(code or "").strip().upper()
    return TRANSFER_TYPE_ALIASES.get(code, code)


def classify_document(transfer_type, typeproblem):
    """จัดหมวดคำขอ 1 ใบ → (group, code, label, cls)

    transfer_type = TRANSFER_TYPE จาก IT_HELPDESK_TRANSFER (None ถ้าไม่มีใบโอนย้าย)
    typeproblem   = REQUEST_TYPEPROBLEM ที่ผู้ใช้เลือกในฟอร์ม
    """
    doc_code = canonical_transfer_type(transfer_type)
    if doc_code:
        info = TRANSFER_DOC_TYPES.get(doc_code)
        if info:
            return GROUP_TRANSFER, doc_code, info["label"], info["cls"]
        # ประเภทใหม่ที่ยังไม่รู้จัก — ยังถือเป็นใบโอนย้าย แต่แสดงรหัสดิบ
        return GROUP_TRANSFER, doc_code, doc_code, "transfer"

    code = canonical_transfer_type(typeproblem)
    info = PLAIN_REQUEST_TYPES.get(code)
    if info:
        return GROUP_REQUEST, code, info["label"], info["cls"]
    return GROUP_REQUEST, "OTHER", UNKNOWN_REQUEST_TYPE["label"], UNKNOWN_REQUEST_TYPE["cls"]

# ── สไตล์สถานะสำหรับหน้า /docs ─────────────────────────────────────────────
# REQUEST_STATUS → (css pill, กลุ่มที่ใช้นับการ์ดสถิติ)
DOC_STATUS_STYLE = {
    "0":  ("wait",   "wait"),
    "1":  ("ready",  "ready"),
    "2":  ("doing",  "active"),
    "3":  ("cancel", "cancel"),
    "4":  ("wait",   "wait"),
    "5":  ("done",   "done"),
    "7":  ("wait",   "wait"),
    "8":  ("wait",   "wait"),
    "10": ("doing",  "doing"),
    "11": ("doing",  "doing"),
}
DEFAULT_DOC_STATUS = ("ไม่ทราบสถานะ", "wait", "wait")

# หน้า /docs ใช้คำเต็มกว่าบอร์ดในบางสถานะ
DOC_STATUS_LABEL_OVERRIDE = {"5": "เสร็จสิ้น"}


def doc_status(code):
    """REQUEST_STATUS → (label, css pill, กลุ่มสถิติ) สำหรับหน้า /docs"""
    code = str(code or "0").strip()
    if code not in DOC_STATUS_STYLE:
        return DEFAULT_DOC_STATUS
    cls, group = DOC_STATUS_STYLE[code]
    label = DOC_STATUS_LABEL_OVERRIDE.get(code) or STATUS_MAP.get(code, "ไม่ทราบสถานะ")
    return label, cls, group


def type_label(group, code):
    """(group, code) ที่ SQL คำนวณมา → (ป้ายไทย, css class)"""
    if group == GROUP_TRANSFER:
        info = TRANSFER_DOC_TYPES.get(code)
        return (info["label"], info["cls"]) if info else (code or "-", "transfer")
    info = PLAIN_REQUEST_TYPES.get(code)
    return ((info["label"], info["cls"]) if info
            else (UNKNOWN_REQUEST_TYPE["label"], UNKNOWN_REQUEST_TYPE["cls"]))


def transfer_type(transfer_type_code, typeproblem=None):
    """TRANSFER_TYPE (+ REQUEST_TYPEPROBLEM สำรอง) → (label, css class)"""
    _, _, label, cls = classify_document(transfer_type_code, typeproblem)
    return label, cls
