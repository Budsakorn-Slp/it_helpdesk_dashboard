# -*- coding: utf-8 -*-
"""ชั้นเชื่อมต่อฐานข้อมูล Oracle

รองรับทั้ง `oracledb` (ตัวใหม่ ใช้บน prod) และ `cx_Oracle` (ตัวเดิม ใช้บน dev)
โดยเลือกอัตโนมัติ — จึงไม่ต้องมีไฟล์แอปแยกสำหรับ dev/prod อีกต่อไป
ต่างกันแค่ค่าใน .env (ORACLE_LIB_DIR / ORACLE_DRIVER)
"""
import importlib
import logging
from contextlib import contextmanager

import config

log = logging.getLogger(__name__)

# ── เลือกและเตรียม driver ────────────────────────────────────────────────────
#
# ทั้งสอง driver ต้องใช้ thick mode เพราะ Oracle 11g ไม่รองรับโหมด thin
# แต่รองรับ Instant Client คนละรุ่นกัน:
#     cx_Oracle 8.3 → Instant Client 11.2 ขึ้นไป   (เครื่อง dev)
#     oracledb  4.x → Instant Client 19.1 ขึ้นไป   (server prod)
# จึงต้อง "ลองเปิด thick mode จริง" แล้วเลือกตัวที่ผ่าน ไม่ใช่เดาจากชื่อ

_CANDIDATES = [config.ORACLE_DRIVER] if config.ORACLE_DRIVER else ["cx_Oracle", "oracledb"]

_THICK_MODE = False
_INIT_NOTES = []


def _select_driver():
    """คืน (ชื่อ driver, module, เปิด thick mode สำเร็จหรือไม่)"""
    global _THICK_MODE
    usable = []

    for name in _CANDIDATES:
        try:
            module = importlib.import_module(name)
        except ImportError as exc:
            _INIT_NOTES.append(f"{name}: ไม่ได้ติดตั้ง ({exc})")
            continue
        usable.append((name, module))

        if not config.ORACLE_LIB_DIR:
            _INIT_NOTES.append(f"{name}: ไม่ได้ตั้ง ORACLE_LIB_DIR — ใช้ค่า default")
            return name, module

        try:
            module.init_oracle_client(lib_dir=config.ORACLE_LIB_DIR)
            _THICK_MODE = True
            return name, module
        except Exception as exc:   # client ไม่รองรับ / path ผิด → ลองตัวถัดไป
            _INIT_NOTES.append(f"{name}: {exc}")

    if not usable:
        raise ImportError(
            "ไม่พบ Oracle driver — ติดตั้งด้วย `pip install -r requirements.txt`\n"
            + "\n".join(_INIT_NOTES)
        )
    # ไม่มีตัวไหนเปิด thick mode ได้ — ยังให้แอปขึ้นได้ แล้วค่อยแจ้ง error ตอนต่อ DB
    return usable[0][0], usable[0][1]


DRIVER_NAME, oracle = _select_driver()

#: exception ฐานของ driver ที่เลือก — ใช้ except ตัวนี้แทนการอ้าง cx_Oracle ตรง ๆ
DatabaseError = oracle.Error


def init_client():
    """รายงานผลการเลือก driver — เรียกครั้งเดียวตอน start app"""
    for note in _INIT_NOTES:
        log.info("[db] %s", note)
    if _THICK_MODE:
        log.info("[db] ใช้ %s (thick mode) @ %s", DRIVER_NAME, config.ORACLE_LIB_DIR)
    else:
        log.warning(
            "[db] ใช้ %s แต่เปิด thick mode ไม่ได้ — ถ้าเป็น Oracle 11g จะต่อไม่ติด "
            "ตรวจค่า ORACLE_LIB_DIR ใน .env", DRIVER_NAME,
        )


# ── การเชื่อมต่อ ─────────────────────────────────────────────────────────────

def get_conn():
    if not (config.ORACLE_USER and config.ORACLE_PASSWORD and config.ORACLE_DSN):
        raise RuntimeError(
            "ยังไม่ได้ตั้งค่าการเชื่อมต่อ Oracle — คัดลอก .env.example เป็น .env "
            "แล้วกรอก ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN"
        )
    return oracle.connect(
        user=config.ORACLE_USER,
        password=config.ORACLE_PASSWORD,
        dsn=config.ORACLE_DSN,
    )


@contextmanager
def db_conn():
    """เปิด connection, rollback เมื่อ error, ปิดให้เสมอ"""
    conn = get_conn()
    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


@contextmanager
def db_cursor(commit=False):
    """ทางลัดที่ใช้บ่อยที่สุด — ได้ cursor มาเลย และ commit ให้ถ้าสั่ง"""
    with db_conn() as conn:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()


# ── ตัวช่วยแปลงผลลัพธ์ ───────────────────────────────────────────────────────

def rows_to_dicts(cur):
    """ทุกแถวของ cursor → list ของ dict (คีย์เป็นตัวพิมพ์เล็ก)"""
    cols = [d[0].lower() for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def row_to_dict(cur):
    """แถวแรกของ cursor → dict (คืน None ถ้าไม่มีแถว)"""
    cols = [d[0].lower() for d in cur.description]
    row = cur.fetchone()
    return dict(zip(cols, row)) if row else None


def scalar(cur, default=None):
    """ค่าแรกของแถวแรก"""
    row = cur.fetchone()
    return row[0] if row else default


def blank_none(d):
    """แทน None ด้วย '' — ให้ฝั่ง JS ไม่ต้องเช็ค null"""
    return {k: ("" if v is None else v) for k, v in d.items()}


def oracle_msg(exc):
    """ข้อความ error ของ Oracle ที่อ่านรู้เรื่อง"""
    try:
        return exc.args[0].message
    except (AttributeError, IndexError):
        return str(exc)
