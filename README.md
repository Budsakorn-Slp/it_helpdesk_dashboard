# IT Helpdesk Dashboard

บอร์ดมอนิเตอร์งาน IT Helpdesk — แสดงคำขอจากตาราง Oracle `IT_HELPDESK_*`
แยกเป็นบอร์ดตามประเภทงาน พร้อมหน้าจัดการเอกสารทรัพย์สินและ Cost Center

## ความต้องการของระบบ

| อย่าง | รุ่น |
| --- | --- |
| Python | 3.9 ขึ้นไป |
| Oracle Database | 11g ขึ้นไป |
| Oracle Instant Client | **ต้องมี** (โหมด thick) — 11.2 ขึ้นไปถ้าใช้ `cx_Oracle`, 19.1 ขึ้นไปถ้าใช้ `oracledb` |

## ติดตั้งและรัน

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (Linux: source .venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env            # Linux: cp .env.example .env
# แก้ .env ให้ตรงกับเครื่อง แล้วรัน
python app.py
```

เปิด <http://127.0.0.1:5093>

บน production ใช้ WSGI server แทนการรัน `python app.py`:

```bash
gunicorn "app:create_app()" -b 0.0.0.0:5093
```

## การตั้งค่า

ทุกอย่างที่ต่างกันระหว่าง dev/prod อยู่ใน `.env` ไฟล์เดียว (ดูตัวอย่างใน `.env.example`)
**ห้าม commit ไฟล์ `.env`** — อยู่ใน `.gitignore` แล้ว

`db.py` เลือก Oracle driver ให้เองโดยลองเปิด thick mode จริง แล้วใช้ตัวที่ผ่าน
บังคับได้ด้วย `ORACLE_DRIVER=cx_Oracle` หรือ `ORACLE_DRIVER=oracledb`

## โครงสร้างโค้ด

```text
app.py              จุดเริ่มของแอป (create_app) — ใช้ไฟล์เดียวทั้ง dev และ prod
config.py           ค่าคงที่ทั้งระบบ + ค่าที่อ่านจาก .env  ← แหล่งความจริงเดียว
db.py               เลือก driver, จัดการ connection, แปลงผลลัพธ์
web.py              รูปแบบ JSON response + decorator ดักจับ error
sql.py              SQL ทุกคำสั่งของระบบ

services/           business logic (ไม่ผูกกับ HTTP)
  boards.py           ประกอบข้อมูลบอร์ด, จัดสถานะ, จัดกลุ่มตามวัน
  tracking.py         เงื่อนไขลายเซ็นครบ + ลำดับผู้ลงนามบนเอกสาร
  docs.py             แปลงข้อมูลหน้า /docs
  employees.py        พนักงาน IT
  audit.py            เขียน IT_HELPDESK_LOG

routes/             HTTP layer (Flask blueprint)
  pages.py            /  /<board_key>  /uploads/<file>
  board_api.py        /api/board  /api/done_page  /api/tracking  /api/close_tracking
  request_api.py      /api/detail /comment /approvers /start /close /approve_it /cancel_it /change_status
  employee_api.py     /api/employees  /api/it_employees
  cost_center.py      /cost-center + API
  docs.py             /docs + /api/docs_detail

templates/          HTML (ไม่มี CSS/JS ฝังใน)
static/css, static/js
```

## บอร์ดและ REQUEST_TYPEFORM

| URL | บอร์ด | typeform |
| --- | --- | --- |
| `/support` | Support / คอมพิวเตอร์ | 1 |
| `/network` | Network / Internet | 2 |
| `/system` | System / โปรแกรม | 3 |
| `/asset` | เบิก / ยืม / โอนย้าย | 4 |
| `/newreq` | ขอแก้ไข / ขอโปรแกรมใหม่ | 5 |
| `/docs` | หน้าเอกสารทรัพย์สิน (typeform 4) | 4 |
| `/cost-center` | จัดการ Cost Center | — |

## ตารางที่ใช้

```text
IT_HELPDESK_REQUEST      คำขอหลัก
 ├─ IT_HELPDESK_APPROVER  สถานะการอนุมัติ
 ├─ IT_HELPDESK_COMMENT   คอมเมนต์ของ IT
 └─ IT_HELPDESK_TRANSFER  เอกสารเบิก/ยืม/โอนย้าย
      └─ IT_HELPDESK_ASSET  ทรัพย์สินในเอกสาร (ผูกด้วย TRANSFER_ID)

IT_HELPDESK_ITEMPLOYEE   รายชื่อพนักงาน IT
IT_HELPDESK_DEPARTMENT   Cost Center
IT_HELPDESK_LOG          บันทึกการเปลี่ยนแปลง
SBP_EMPLOYEE             ชื่อผู้อนุมัติ
```

หมายเหตุสคีมาที่ต้องระวัง: `REQUEST_DATE` / `DATE_START` / `DATE_FINISH`
เก็บเป็น `VARCHAR2` รูปแบบ `DD/MM/YYYY HH24:MI` ไม่ใช่ `DATE`
