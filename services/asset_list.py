# -*- coding: utf-8 -*-
"""หน้า /asset แบบรายการเอกสาร — กรอง เรียง และแบ่งหน้าที่ฝั่งฐานข้อมูล

ทำใน SQL ทั้งหมด (ดู sql.ASSET_LIST_BASE) เพื่อให้รองรับข้อมูลหลักพันแถวได้
โดยหน้าเว็บส่งมาเฉพาะแถวของหน้าที่กำลังเปิดอยู่

SQL เป็นเจ้าของค่า DOC_GROUP / DOC_CODE / WORKFLOW_STATUS / TRACKING_COMPLETE
ฝั่ง Python แค่แปลงรหัสเป็นป้ายภาษาไทย จึงไม่มีตรรกะซ้ำสองที่
"""
from datetime import date, timedelta

import config
import db
import sql
from services import docs

# ── ตัวเลือกที่อนุญาต (whitelist — กันไม่ให้ค่าจาก URL หลุดเข้า SQL) ─────────

PAGE_SIZES = (25, 50, 100, 200)
DEFAULT_PAGE_SIZE = 50

#: sort=<field>&dir=<direction> → ORDER BY ที่ใช้จริง
SORT_ORDERS = {
    ("id", "asc"):    "REQUEST_ID ASC",
    ("id", "desc"):   "REQUEST_ID DESC",
    ("date", "asc"):  "SORT_DATE ASC NULLS LAST, REQUEST_ID ASC",
    ("date", "desc"): "SORT_DATE DESC NULLS LAST, REQUEST_ID DESC",
}

#: ลำดับตั้งต้น — งานที่ต้องลงมือขึ้นก่อน แล้วเรียงตามวันที่แจ้ง
DEFAULT_ORDER = (
    "CASE WORKFLOW_STATUS"
    "  WHEN 'ready' THEN 1 WHEN 'doing' THEN 2 WHEN 'tracking' THEN 3"
    "  WHEN 'waiting' THEN 4 WHEN 'done' THEN 5 ELSE 6 END,"
    " SORT_DATE ASC NULLS LAST"
)

DAY_RANGES = (1, 7, 30, 90)

#: workflow_status → (ป้ายไทย, css class)
WORKFLOW_LABELS = {
    "waiting":  ("รออนุมัติ",     "wait"),
    "ready":    ("พร้อมทำ",       "ready"),
    "doing":    ("กำลังทำ",       "doing"),
    "tracking": ("ติดตามเอกสาร",  "track"),
    "done":     ("เสร็จสิ้น",     "done"),
    "cancel":   ("ยกเลิก",        "cancel"),
}

#: ลำดับสถานะที่แสดงในเมนูซ้าย
STAT_GROUPS = ("waiting", "ready", "doing", "tracking", "done", "cancel")

#: workflow_status → ปุ่มที่แถวนั้นควรมี
ACTIONS = {
    "waiting":  ("approve", "cancel"),
    "ready":    ("start",),
    "doing":    ("close",),
    "tracking": ("close_tracking",),
    "done":     (),
    "cancel":   (),
}

SEARCH_COLUMNS = (
    "TO_CHAR(REQUEST_ID)", "UPPER(REQUESTER_FNAME)", "UPPER(REQUESTER_LNAME)",
    "UPPER(REQUESTER_DEPT)", "UPPER(ASSET_CODE)", "UPPER(ASSET_NAME)",
    "UPPER(REQUEST_REMARK)",
)


# ── อ่านค่าจาก query string ─────────────────────────────────────────────────

def parse_filters(args):
    """แปลง request.args → dict ที่ผ่านการตรวจแล้ว (ค่าผิดจะกลายเป็นค่าตั้งต้น)"""
    def as_int(name, default):
        try:
            return int(args.get(name, default))
        except (TypeError, ValueError):
            return default

    flow = (args.get("flow") or "").strip()
    cat  = (args.get("cat") or "").strip()
    sort = (args.get("sort") or "").strip()
    direction = (args.get("dir") or "desc").strip()
    days = as_int("days", 0)
    size = as_int("size", DEFAULT_PAGE_SIZE)

    return {
        "flow": flow if flow in WORKFLOW_LABELS else "",
        "cat":  cat if _valid_cat(cat) else "",
        "q":    (args.get("q") or "").strip()[:100],
        "days": days if days in DAY_RANGES else 0,
        "sort": sort if (sort, direction) in SORT_ORDERS else "",
        "dir":  direction if direction in ("asc", "desc") else "desc",
        "size": size if size in PAGE_SIZES else DEFAULT_PAGE_SIZE,
        "page": max(1, as_int("page", 1)),
    }


def _valid_cat(cat):
    """หมวดที่อนุญาต: doc | transfer | request | <group>:<code>"""
    if cat in ("doc", config.GROUP_TRANSFER, config.GROUP_REQUEST):
        return True
    if ":" not in cat:
        return False
    group, code = cat.split(":", 1)
    if group == config.GROUP_TRANSFER:
        return code in config.TRANSFER_DOC_TYPES
    if group == config.GROUP_REQUEST:
        return code in config.PLAIN_REQUEST_TYPES or code == "OTHER"
    return False


# ── สร้างเงื่อนไข WHERE ─────────────────────────────────────────────────────

def _build_where(filters):
    """คืน (ข้อความ SQL ต่อท้าย WHERE, พารามิเตอร์)  — ค่าทั้งหมดผูกเป็น bind"""
    clauses, params = [], {}

    if filters["flow"]:
        clauses.append("WORKFLOW_STATUS = :flow")
        params["flow"] = filters["flow"]

    cat = filters["cat"]
    if cat == "doc" or cat == config.GROUP_TRANSFER:
        clauses.append("DOC_GROUP = :doc_group")
        params["doc_group"] = config.GROUP_TRANSFER
    elif cat == config.GROUP_REQUEST:
        clauses.append("DOC_GROUP = :doc_group")
        params["doc_group"] = config.GROUP_REQUEST
    elif cat:
        group, code = cat.split(":", 1)
        clauses.append("DOC_GROUP = :doc_group AND DOC_CODE = :doc_code")
        params["doc_group"], params["doc_code"] = group, code

    if filters["q"]:
        like = " OR ".join(f"{col} LIKE :q" for col in SEARCH_COLUMNS)
        clauses.append(f"({like})")
        params["q"] = f"%{filters['q'].upper()}%"

    if filters["days"]:
        start = date.today() - timedelta(days=filters["days"] - 1)
        clauses.append("SORT_DATE >= :date_from")
        params["date_from"] = start.strftime("%Y%m%d") + "00:00"

    return ("".join(f" AND {c}" for c in clauses), params)


def _order_by(filters):
    return SORT_ORDERS.get((filters["sort"], filters["dir"]), DEFAULT_ORDER)


# ── ดึงข้อมูล ────────────────────────────────────────────────────────────────

def _map_row(d):
    """แถวจาก SQL → dict สำหรับตาราง (ป้ายไทยมาจาก config, สถานะมาจาก SQL)"""
    group = (d.get("doc_group") or config.GROUP_REQUEST).strip()
    code  = (d.get("doc_code") or "OTHER").strip()
    workflow = (d.get("workflow_status") or "waiting").strip()

    row = docs.map_row(d)
    row["doc_group"]  = group
    row["doc_code"]   = code
    row["type_label"], row["type_cls"] = config.type_label(group, code)

    row["request_status"]    = str(d.get("request_status") or "0").strip()
    row["sort_date"]         = d.get("sort_date") or ""
    row["workflow_status"]   = workflow
    row["is_tracking"]       = group == config.GROUP_TRANSFER
    row["tracking_complete"] = bool(d.get("tracking_complete"))
    row["actions"]           = ACTIONS.get(workflow, ())
    row["flow_label"], row["flow_cls"] = WORKFLOW_LABELS.get(
        workflow, (row["status_label"], row["status_cls"]))
    return row


def fetch_page(filters):
    """แถวของหน้าที่เปิดอยู่, จำนวนทั้งหมดที่ตรงกับตัวกรอง, และเลขหน้าที่ใช้จริง

    ถ้า page ที่ขอมาเกินจำนวนหน้าที่มี จะถูกดึงกลับมาหน้าสุดท้าย
    เพื่อไม่ให้เจอตารางว่างทั้งที่ยังมีข้อมูล
    """
    where, params = _build_where(filters)
    params["typeform"] = config.ASSET_TYPEFORM

    page_sql = f"""
        SELECT * FROM (
            SELECT b.*, ROW_NUMBER() OVER (ORDER BY {_order_by(filters)}) AS RN
            FROM ({sql.ASSET_LIST_BASE}) b
            WHERE 1 = 1{where}
        ) WHERE RN > :offset AND RN <= :limit_end
    """
    count_sql = f"SELECT COUNT(*) FROM ({sql.ASSET_LIST_BASE}) b WHERE 1 = 1{where}"

    size = filters["size"]
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(count_sql, params)
        total = db.scalar(cur, 0)

        total_pages = max(1, -(-total // size))
        page = min(max(1, filters["page"]), total_pages)

        offset = (page - 1) * size
        cur.execute(page_sql, {**params, "offset": offset, "limit_end": offset + size})
        rows = [_map_row(d) for d in db.rows_to_dicts(cur)]

    return rows, total, page


def fetch_counts():
    """จำนวนเอกสารแยกตามสถานะและหมวด — ใช้ทำตัวเลขบนเมนู (ไม่ขึ้นกับตัวกรอง)"""
    flow_counts, cat_counts, group_counts, total = {}, {}, {}, 0
    with db.db_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql.ASSET_LIST_STATS, {"typeform": config.ASSET_TYPEFORM})
        for workflow, group, code, count in cur.fetchall():
            flow_counts[workflow] = flow_counts.get(workflow, 0) + count
            cat_counts[(group, code)] = cat_counts.get((group, code), 0) + count
            group_counts[group] = group_counts.get(group, 0) + count
            total += count
    return {"flow": flow_counts, "cat": cat_counts, "group": group_counts, "total": total}


def empty_counts():
    """โครงสร้างว่าง — ใช้ตอนต่อฐานข้อมูลไม่ได้"""
    return {"flow": {}, "cat": {}, "group": {}, "total": 0}


# ── เมนูซ้าย ─────────────────────────────────────────────────────────────────

def build_status_nav(counts):
    """หมวด "สถานะงาน" — เรียงตามลำดับการทำงานจริง"""
    return [
        {
            "key":   key,
            "label": WORKFLOW_LABELS[key][0],
            "cls":   WORKFLOW_LABELS[key][1],
            "count": counts["flow"].get(key, 0),
        }
        for key in STAT_GROUPS
    ]


def build_nav(counts):
    """โครงเมนูหมวดหมู่เอกสาร

        เอกสาร
          └ ใบโอนย้าย            (คำขอที่มีแถวใน IT_HELPDESK_TRANSFER)
              ├ โอนย้ายระหว่างหน่วยงาน
              ├ ตัดบัญชี / สูญหาย
              ├ เพื่อขาย
              ├ ส่งซ่อม
              └ ยืม
        คำขอทั่วไป               (เบิก / ยืม ที่ไม่ได้ออกใบโอนย้าย)
    """
    cat, group = counts["cat"], counts["group"]

    def child(g, code, info):
        return {
            "key":   f"{g}:{code}",
            "label": info["label"],
            "cls":   info["cls"],
            "count": cat.get((g, code), 0),
        }

    transfer_children = [
        child(config.GROUP_TRANSFER, code, info)
        for code, info in config.TRANSFER_DOC_TYPES.items()
    ]

    plain_children = [
        child(config.GROUP_REQUEST, code, info)
        for code, info in config.PLAIN_REQUEST_TYPES.items()
    ]
    other = cat.get((config.GROUP_REQUEST, "OTHER"), 0)
    if other:
        plain_children.append(child(config.GROUP_REQUEST, "OTHER", config.UNKNOWN_REQUEST_TYPE))

    transfer_total = group.get(config.GROUP_TRANSFER, 0)

    return [
        {
            "key":      "doc",
            "label":    "เอกสาร",
            "icon":     "ic-folder",
            "count":    transfer_total,
            "children": [{
                "key":      config.GROUP_TRANSFER,
                "label":    "ใบโอนย้าย",
                "icon":     "ic-detail",
                "count":    transfer_total,
                "children": transfer_children,
            }],
        },
        {
            "key":      config.GROUP_REQUEST,
            "label":    "คำขอทั่วไป",
            "icon":     "ic-inbox",
            "count":    group.get(config.GROUP_REQUEST, 0),
            "children": plain_children,
        },
    ]


# ── แบ่งหน้า ─────────────────────────────────────────────────────────────────

PAGE_WINDOW = 2   # แสดงเลขหน้ารอบ ๆ หน้าปัจจุบันข้างละกี่หน้า


def build_pager(page, size, total):
    """ข้อมูลสำหรับแถบเลขหน้า — ใส่ None แทนช่วงที่ข้าม (แสดงเป็น …)

    หมายเหตุ: ห้ามตั้งชื่อคีย์ว่า items/keys/values เพราะ Jinja จะไปเจอ
    เมธอดของ dict แทนค่าที่ต้องการ
    """
    total_pages = max(1, -(-total // size))     # ปัดขึ้น
    page = min(page, total_pages)

    wanted = {1, total_pages}
    wanted.update(range(page - PAGE_WINDOW, page + PAGE_WINDOW + 1))
    numbers = sorted(n for n in wanted if 1 <= n <= total_pages)

    pages, previous = [], 0
    for n in numbers:
        if previous and n - previous > 1:
            pages.append(None)
        pages.append(n)
        previous = n

    first = (page - 1) * size + 1 if total else 0
    return {
        "page":        page,
        "size":        size,
        "total":       total,
        "total_pages": total_pages,
        "pages":       pages,
        "has_prev":    page > 1,
        "has_next":    page < total_pages,
        "first_row":   first,
        "last_row":    min(page * size, total),
        "sizes":       PAGE_SIZES,
    }
