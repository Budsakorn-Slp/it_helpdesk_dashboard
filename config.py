# -*- coding: utf-8 -*-
"""ค่าตั้งต้นของระบบ — อ่านค่าที่เปลี่ยนตามเครื่อง (dev/prod) จาก .env

ไฟล์นี้เป็นแหล่งความจริงเดียวของค่าคงที่ทั้งระบบ (สถานะ / บอร์ด / ประเภทเอกสาร)
โมดูลอื่นต้อง import จากที่นี่ ห้ามประกาศซ้ำ
"""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _env_bool(key, default=False):
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


# ── Oracle ───────────────────────────────────────────────────────────────────
# ไม่ใส่ค่า default ของ user/password ในโค้ด — ต้องมาจาก .env เท่านั้น (ดู .env.example)
ORACLE_USER     = os.getenv("ORACLE_USER", "")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "")
ORACLE_DSN      = os.getenv("ORACLE_DSN", "")

# โฟลเดอร์ Oracle Instant Client (thick mode — จำเป็นสำหรับ Oracle 11g)
#   dev  (Windows) : C:\instantclient_11_2
#   prod (Linux)   : /opt/oracle/instantclient_21_21
ORACLE_LIB_DIR = os.getenv("ORACLE_LIB_DIR", "")

# บังคับเลือก driver ได้ด้วย ORACLE_DRIVER=oracledb|cx_Oracle
# ถ้าไม่ระบุ จะลอง oracledb ก่อนแล้วค่อย fallback ไป cx_Oracle
ORACLE_DRIVER = os.getenv("ORACLE_DRIVER", "").strip()

# ── Flask ────────────────────────────────────────────────────────────────────
HOST  = os.getenv("FLASK_HOST", "0.0.0.0")
PORT  = int(os.getenv("FLASK_PORT", "5093"))
DEBUG = _env_bool("FLASK_DEBUG", False)

# โฟลเดอร์ไฟล์แนบ — ใช้ร่วมกับระบบ it_helpdesk ที่อยู่ระดับเดียวกัน
UPLOAD_FOLDER = os.getenv(
    "UPLOAD_FOLDER",
    os.path.abspath(os.path.join(BASE_DIR, "..", "it_helpdesk", "static", "uploads")),
)

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

# ลำดับการเรียงการ์ดในบอร์ด
ORDER_PRIORITY = {"ready": 1, "doing": 2, "tracking": 3, "done": 4, "waiting": 5, "cancel": 6}

WORKFLOW_STATUSES = ("ready", "doing", "done", "waiting", "cancel", "tracking")

# ── ประเภทเอกสารทรัพย์สิน (IT_HELPDESK_TRANSFER.TRANSFER_TYPE) ──────────────
# label = ป้ายภาษาไทย, cls = css class ที่ใช้ในหน้า /docs
TRANSFER_TYPES = {
    "TRANSFER":      {"label": "โอนย้าย",  "cls": "transfer"},
    "BORROW":        {"label": "ยืม",      "cls": "borrow"},
    "BORROW_DIRECT": {"label": "ยืม",      "cls": "borrow"},
    "WITHDRAW":      {"label": "เบิก",     "cls": "withdraw"},
    "DISPOSE":       {"label": "ตัดบัญชี", "cls": "dispose"},
    "SALE":          {"label": "ขาย",      "cls": "sale"},
    "REPAIR":        {"label": "ส่งซ่อม",  "cls": "repair"},
}
DEFAULT_TRANSFER_TYPE = {"label": "เบิก", "cls": "withdraw"}

TRANSFER_TYPE_LABELS = {k: v["label"] for k, v in TRANSFER_TYPES.items()}

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


def transfer_type(key):
    """TRANSFER_TYPE / REQUEST_TYPEPROBLEM → (label, css class)"""
    info = TRANSFER_TYPES.get(str(key or "").strip().upper(), DEFAULT_TRANSFER_TYPE)
    return info["label"], info["cls"]
