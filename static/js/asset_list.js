/* ══════════════════════════════════════════════════════════════════════════
   asset_list.js — เฉพาะหน้า /asset แบบรายการเอกสาร

   การกรอง เรียง และแบ่งหน้า ทำที่ฝั่ง server ทั้งหมด (ดู services/asset_list.py)
   เพราะข้อมูลอาจมีหลักพันแถว หน้าเว็บจึงรับมาเฉพาะแถวของหน้าที่เปิดอยู่
   ตัวกรองทุกตัวอยู่ใน query string จึงบุ๊กมาร์กและกดย้อนกลับได้

   ไฟล์นี้เหลือแค่เรื่องที่ต้องทำฝั่ง browser จริง ๆ:
     - พับ/กาง และซ่อน/แสดงเมนูซ้าย (จำสถานะไว้ใน localStorage)
     - ส่งฟอร์มค้นหาอัตโนมัติหลังหยุดพิมพ์

   ต้องโหลด ui.js ก่อนไฟล์นี้ — utility กับ modal ทั้งหมดอยู่ที่นั่น
══════════════════════════════════════════════════════════════════════════ */

const AUTO_REFRESH_MS = 300000;   /* รีเฟรชหน้าทุก 5 นาที (คงตัวกรองเดิมไว้) */
const SEARCH_DELAY_MS = 500;      /* หยุดพิมพ์แล้วรอเท่านี้ก่อนค้นหา */
const NAV_STATE_KEY   = "assetNavOpen";     /* จำว่าหมวดไหนกางอยู่ */
const NAV_HIDDEN_KEY  = "assetNavHidden";   /* จำว่าซ่อนแถบเมนูไว้ไหม */

/* ══════════════════════════════════════
   เมนูซ้าย — พับ / กาง
══════════════════════════════════════ */

function openNodeKeys() {
  try {
    return new Set(JSON.parse(localStorage.getItem(NAV_STATE_KEY) || "[]"));
  } catch (e) {
    return new Set();
  }
}

function saveOpenNodes() {
  const keys = [...document.querySelectorAll(".nav-node.has-children.open")]
    .map(n => n.querySelector(".nav-item")?.dataset.key)
    .filter(Boolean);
  try { localStorage.setItem(NAV_STATE_KEY, JSON.stringify(keys)); } catch (e) { /* โหมดส่วนตัว */ }
}

function toggleNavNode(btn) {
  btn.closest(".nav-node")?.classList.toggle("open");
  saveOpenNodes();
}

/* ซ่อน / แสดงแถบเมนูทั้งแถบ */
function toggleNav() {
  if (window.matchMedia("(max-width: 980px)").matches) {
    document.body.classList.toggle("nav-open");
    return;
  }
  const hidden = document.body.classList.toggle("nav-hidden");
  try { localStorage.setItem(NAV_HIDDEN_KEY, hidden ? "1" : "0"); } catch (e) { /* โหมดส่วนตัว */ }
}

/* ══════════════════════════════════════
   INIT
══════════════════════════════════════ */

(function initNav() {
  const saved = openNodeKeys();

  document.querySelectorAll(".nav-node.has-children").forEach(node => {
    const key = node.querySelector(".nav-item")?.dataset.key;
    /* ครั้งแรกที่เข้า (ยังไม่เคยบันทึก) ให้กางไว้ทั้งหมดเพื่อให้เห็นโครงสร้าง */
    node.classList.toggle("open", saved.size ? saved.has(key) : true);
  });

  /* หมวดที่กำลังถูกเลือกอยู่ ต้องกางให้เห็นเสมอ */
  const active = document.querySelector(".nav-label.active");
  let parent = active?.closest(".nav-node")?.parentElement?.closest(".nav-node");
  while (parent) {
    parent.classList.add("open");
    parent = parent.parentElement.closest(".nav-node");
  }

  try {
    if (localStorage.getItem(NAV_HIDDEN_KEY) === "1") {
      document.body.classList.add("nav-hidden");
    }
  } catch (e) { /* โหมดส่วนตัว */ }
})();

/* ค้นหาอัตโนมัติหลังหยุดพิมพ์ — ไม่ต้องกดปุ่มเอง */
(function initSearch() {
  const box = document.getElementById("list-search");
  if (!box) return;

  let timer = null;
  box.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => box.form?.submit(), SEARCH_DELAY_MS);
  });
  /* กด Enter ให้ค้นทันที ไม่ต้องรอ */
  box.addEventListener("keydown", e => {
    if (e.key === "Enter") clearTimeout(timer);
  });
})();

setInterval(() => location.reload(), AUTO_REFRESH_MS);
