# -*- coding: utf-8 -*-
"""หน้าแรก (/) — ภาพรวมเอกสารทุกบอร์ด แบบดูอย่างเดียว

ใช้คิวรีตัวเดียวกับหน้ารายการ (sql.ASSET_LIST_BASE) แต่ส่ง typeform = None
เพื่อดึงทุกบอร์ดมารวมกัน จึงไม่มีตรรกะสถานะซ้ำอีกชุด
"""
import config
from services import asset_list

#: การ์ดสรุปด้านบน — (workflow_status, ป้ายไทย, css class)
#  เรียงตามลำดับการทำงานจริง เพื่อให้อ่านไล่จากซ้ายไปขวาได้
#  ต้องมีครบทุกสถานะ ไม่งั้นผลรวมของการ์ดจะไม่เท่ากับ "เอกสารทั้งหมด"
SUMMARY_CARDS = (
    ("waiting",  "รออนุมัติ",     "wait"),
    ("ready",    "อนุมัติแล้ว",   "ready"),
    ("doing",    "กำลังทำ",       "doing"),
    ("tracking", "ติดตามเอกสาร",  "track"),
    ("done",     "เสร็จสิ้น",     "done"),
    ("cancel",   "ยกเลิก",        "cancel"),
)


def build_cards(counts):
    """ตัวเลขสำหรับการ์ดสรุป — ใบแรกคือยอดรวมทั้งหมด (กดเพื่อล้างตัวกรอง)"""
    cards = [{
        "key": "", "label": "เอกสารทั้งหมด", "cls": "all",
        "count": counts.get("total", 0), "is_total": True,
    }]
    cards += [
        {"key": key, "label": label, "cls": cls,
         "count": counts["flow"].get(key, 0), "is_total": False}
        for key, label, cls in SUMMARY_CARDS
    ]
    return cards


def build_menu():
    """เมนูบอร์ดทั้ง 5 ใน sidebar — ลิงก์ไปหน้าที่ทำงานได้จริง"""
    return [
        {
            "key":   key,
            "title": cfg["title"],
            "sub":   SUBTITLES.get(key, ""),
            "icon":  ICONS.get(key, "ic-detail"),
            "url":   "/" + key,
        }
        for key, cfg in config.BOARDS.items()
    ]


#: คำอธิบายใต้ชื่อเมนู (ให้ตรงกับที่หน้าเดิมเคยแสดง)
SUBTITLES = {
    "network": "แจ้งปัญหาอินเตอร์เน็ต / โทรศัพท์",
    "system":  "ขอสิทธิ์การเข้าถึง",
    "support": "แจ้งปัญหาคอมพิวเตอร์",
    "asset":   "เบิก / ยืม / โอนย้ายทรัพย์สิน",
    "newreq":  "เว็บไซต์และโปรแกรม",
}

ICONS = {
    "network": "ic-globe",
    "system":  "ic-key",
    "support": "ic-monitor",
    "asset":   "ic-box",
    "newreq":  "ic-code",
}


def fetch(filters):
    """การ์ดสรุป + รายการเอกสารของทุกบอร์ด

    typeform = None → sql.ASSET_LIST_BASE จะไม่กรองบอร์ด
    """
    counts = asset_list.fetch_counts(None)
    rows, total, page = asset_list.fetch_page(filters, None)
    return counts, rows, total, page


def empty():
    return asset_list.empty_counts(), [], 0, 1
