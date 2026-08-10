# -*- coding: utf-8 -*-
"""ตัวช่วยฝั่ง HTTP — รูปแบบ JSON response และการดักจับ error ที่ใช้ร่วมกันทุก route"""
import logging
from functools import wraps

from flask import jsonify, request

from db import DatabaseError, oracle_msg

log = logging.getLogger(__name__)


def ok_resp(**payload):
    return jsonify({"ok": True, **payload})


def err_resp(msg, **payload):
    return jsonify({"ok": False, "msg": msg, **payload})


def api(**on_error):
    """ครอบ route ให้แปลง error ของ Oracle เป็น JSON `{ok: false}` อัตโนมัติ

    คีย์ที่ส่งเข้ามาจะถูกแนบไปกับ response ตอน error เพื่อให้ฝั่ง JS
    ยังได้โครงสร้างเดิม เช่น `@api(items=[])`
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except DatabaseError as exc:
                log.error("[%s] %s", fn.__name__, oracle_msg(exc))
                return err_resp(oracle_msg(exc), **on_error)
            except RuntimeError as exc:      # เช่น ยังไม่ได้ตั้งค่า .env
                log.error("[%s] %s", fn.__name__, exc)
                return err_resp(str(exc), **on_error)
        return wrapper
    return decorator


def json_body(*fields, required=()):
    """อ่าน JSON body → tuple ของค่าที่ strip แล้ว

    คืน (values, error_message) โดย error_message เป็น None ถ้าครบ
    """
    data = request.get_json(silent=True) or {}
    values = tuple(str(data.get(f) or "").strip() for f in fields)
    missing = [f for f, v in zip(fields, values) if f in required and not v]
    return values, ("ข้อมูลไม่ครบ: " + ", ".join(missing)) if missing else None
