@echo off
REM ── รันโปรเจกต์ IT Helpdesk Dashboard ──
REM ดับเบิลคลิกไฟล์นี้ หรือพิมพ์ run ใน cmd ก็ได้
REM หยุดด้วย Ctrl+C

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] ไม่พบ .venv — สร้างใหม่ด้วยคำสั่ง:
    echo     "%%USERPROFILE%%\.pyenv\pyenv-win\versions\3.9.13\python.exe" -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist ".env" (
    echo [ERROR] ไม่พบไฟล์ .env — คัดลอกจากตัวอย่างก่อน:
    echo     copy .env.example .env
    pause
    exit /b 1
)

echo กำลังเริ่ม IT Helpdesk Dashboard ...
echo เปิดที่ http://127.0.0.1:5093
echo หยุดด้วย Ctrl+C
echo.

".venv\Scripts\python.exe" app.py
pause
