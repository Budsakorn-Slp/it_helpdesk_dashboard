/* ══════════════════════════════════════════════════════════════════════════
   asset_list.js — เฉพาะหน้า /asset แบบรายการเอกสาร
                   (เมนูซ้ายแบบพับได้ + กรองด้วยการ์ดสถิติ / คำค้น / ช่วงวันที่)

   ต้องโหลด ui.js ก่อนไฟล์นี้ — utility กับ modal ทั้งหมดอยู่ที่นั่น

   ทุกแถวเป็น <tr class="list-row"> ที่ server ใส่ data-* มาให้แล้ว:
     data-nav    "<group>:<code>"  เช่น transfer:TRANSFER, request:WITHDRAW
     data-group  transfer | request
     data-flow   สถานะงาน (ready/doing/waiting/tracking/done/cancel)
     data-date   วันที่แจ้ง DD/MM/YYYY HH:MM
     data-search ข้อความรวมสำหรับค้นหา
══════════════════════════════════════════════════════════════════════════ */

const AUTO_REFRESH_MS = 300000;   /* รีเฟรชหน้าทุก 5 นาที */
const MS_PER_DAY      = 86400000;
const NAV_STATE_KEY   = "assetNavOpen";     /* จำว่าหมวดไหนกางอยู่ */
const NAV_HIDDEN_KEY  = "assetNavHidden";   /* จำว่าซ่อนแถบเมนูไว้ไหม */
const SORT_KEY        = "assetSort";        /* จำการเรียงล่าสุด */

let activeFlow = "";   /* สถานะที่เลือกในเมนู ("" = ทุกสถานะ) */
let activeNav  = "";   /* หมวดเอกสารในเมนู ("" = ทั้งหมด) */
let sortField  = "";   /* "" = ลำดับตั้งต้นจาก server, "id" | "date" */
let sortDir    = "desc";

/* ── แปลง "DD/MM/YYYY HH:MM" เป็น Date (คืน null ถ้ารูปแบบไม่ตรง) ── */
function parseDocDate(text) {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})/.exec((text || "").trim());
  if (!m) return null;
  const [, day, month, year] = m;
  return new Date(Number(year), Number(month) - 1, Number(day));
}

function daysAgo(date) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.floor((today - date) / MS_PER_DAY);
}

/* ══════════════════════════════════════
   เมนูซ้าย — พับ / กาง
══════════════════════════════════════ */

/* คีย์ของ node ที่กางอยู่ เก็บลง localStorage เพื่อจำข้ามการรีเฟรช */
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
  const narrow = window.matchMedia("(max-width: 980px)").matches;
  if (narrow) {
    document.body.classList.toggle("nav-open");
    return;
  }
  const hidden = document.body.classList.toggle("nav-hidden");
  try { localStorage.setItem(NAV_HIDDEN_KEY, hidden ? "1" : "0"); } catch (e) { /* โหมดส่วนตัว */ }
}

/* คลิกหมวดในเมนู = กรองตารางตามหมวดนั้น (คลิกซ้ำเพื่อกลับไปทั้งหมด) */
function filterByNav(btn) {
  const key = btn.dataset.key || "";
  activeNav = (activeNav === key && key !== "") ? "" : key;

  markNavActive();

  /* กางหมวดแม่ให้เห็นตัวที่เลือกอยู่เสมอ */
  if (activeNav) {
    let node = btn.closest(".nav-node")?.parentElement?.closest(".nav-node");
    while (node) {
      node.classList.add("open");
      node = node.parentElement?.closest(".nav-node");
    }
    saveOpenNodes();
  }
  if (window.matchMedia("(max-width: 980px)").matches) {
    document.body.classList.remove("nav-open");
  }
  applyListFilter();
}

/* แถวเข้ากับหมวดที่เลือกไหม
   key ว่าง        = ทุกหมวด
   "doc"           = เอกสารทั้งหมด (ทุกใบโอนย้าย)
   "transfer"      = ใบโอนย้ายทั้งหมด
   "request"       = คำขอทั่วไปทั้งหมด
   "<group>:<code>"= ประเภทเดียว */
function matchesNav(row) {
  if (!activeNav) return true;
  if (activeNav === "doc") return row.dataset.group === "transfer";
  if (activeNav.includes(":")) return row.dataset.nav === activeNav;
  return row.dataset.group === activeNav;
}

/* ══════════════════════════════════════
   SORT — เลขที่ / วันที่แจ้ง
══════════════════════════════════════ */

/* ค่าที่ใช้เทียบของแต่ละแถว
   id   : ตัวเลข
   date : สตริง YYYYMMDDHHMM ที่ server เตรียมมาให้ (เทียบตรง ๆ ได้) */
function sortValue(row, field) {
  if (field === "id") return Number(row.dataset.id) || 0;
  return row.dataset.sortDate || "";
}

function compareRows(a, b) {
  if (!sortField) return Number(a.dataset.seq) - Number(b.dataset.seq);

  const av = sortValue(a, sortField);
  const bv = sortValue(b, sortField);
  let diff = av < bv ? -1 : av > bv ? 1 : 0;

  /* ค่าเท่ากัน (เช่นแจ้งเวลาเดียวกัน) ให้เรียงต่อด้วยเลขที่เพื่อไม่ให้สลับไปมา */
  if (diff === 0 && sortField !== "id") {
    diff = (Number(a.dataset.id) || 0) - (Number(b.dataset.id) || 0);
  }
  return sortDir === "asc" ? diff : -diff;
}

function applySort() {
  const tbody = document.getElementById("list-body");
  if (!tbody) return;

  [...tbody.querySelectorAll(".list-row")]
    .sort(compareRows)
    .forEach(row => tbody.appendChild(row));

  /* แถว "ไม่พบเอกสารที่ตรงกับเงื่อนไข" ต้องอยู่ท้ายสุดเสมอ */
  const noMatch = document.getElementById("list-no-match");
  if (noMatch) tbody.appendChild(noMatch);

  markSortArrows();
}

function markSortArrows() {
  const asc = sortDir === "asc";
  document.querySelectorAll("th.sortable").forEach(th => th.classList.remove("sorted"));

  [["id", "sort-arrow-id"], ["date", "sort-arrow-date"]].forEach(([field, arrowId]) => {
    const arrow = document.getElementById(arrowId);
    if (!arrow) return;
    const active = sortField === field;
    arrow.textContent = active ? (asc ? "▲" : "▼") : "⇅";
    if (active) arrow.closest("th")?.classList.add("sorted");
  });
}

/* คลิกหัวคอลัมน์ = สลับ มากไปน้อย ⇄ น้อยไปมาก
   คอลัมน์ใหม่เริ่มที่ "มากไปน้อย" เพราะรายการใหม่สุดควรอยู่บน */
function sortBy(field) {
  if (sortField === field) {
    sortDir = sortDir === "desc" ? "asc" : "desc";
  } else {
    sortField = field;
    sortDir = "desc";
  }
  try {
    localStorage.setItem(SORT_KEY, JSON.stringify({ field: sortField, dir: sortDir }));
  } catch (e) { /* โหมดส่วนตัว */ }
  applySort();
}

/* ══════════════════════════════════════
   FILTER
══════════════════════════════════════ */

function applyListFilter() {
  const term = (document.getElementById("list-search")?.value || "").trim().toLowerCase();
  const days = parseInt(document.getElementById("list-days")?.value || "", 10);

  let shown = 0;

  document.querySelectorAll(".list-row").forEach(row => {
    const matchFlow = !activeFlow || row.dataset.flow === activeFlow;
    const matchTerm = !term || (row.dataset.search || "").includes(term);

    let matchDate = true;
    if (!Number.isNaN(days)) {
      const date = parseDocDate(row.dataset.date);
      matchDate = date ? daysAgo(date) < days : false;
    }

    const show = matchFlow && matchTerm && matchDate && matchesNav(row);
    row.style.display = show ? "" : "none";
    if (show) shown++;
  });

  const hasFilter = activeFlow || activeNav || term || !Number.isNaN(days);

  const noMatch = document.getElementById("list-no-match");
  if (noMatch) noMatch.style.display = (shown === 0 && hasFilter) ? "" : "none";

  const countEl = document.getElementById("list-count");
  if (countEl) countEl.textContent = hasFilter ? `พบ ${shown} รายการ` : "";
}

/* คลิกสถานะในเมนู = กรองตามสถานะงาน (คลิกซ้ำเพื่อยกเลิก) */
function filterByFlow(btn) {
  const flow = btn.dataset.flow || "";
  activeFlow = (activeFlow === flow && flow !== "") ? "" : flow;

  markNavActive();
  if (window.matchMedia("(max-width: 980px)").matches) {
    document.body.classList.remove("nav-open");
  }
  applyListFilter();
}

/* ไฮไลต์รายการในเมนูให้ตรงกับตัวกรองที่เลือกอยู่
   ปุ่ม "ทั้งหมด" จะสว่างก็ต่อเมื่อไม่ได้กรองอะไรเลย */
function markNavActive() {
  document.querySelectorAll(".nav-label[data-flow]").forEach(el => {
    el.classList.toggle("active", el.dataset.flow === activeFlow && activeFlow !== "");
  });
  document.querySelectorAll(".nav-label[data-key]:not(.nav-all)").forEach(el => {
    el.classList.toggle("active", (el.dataset.key || "") === activeNav && activeNav !== "");
  });
  document.querySelector(".nav-all")?.classList.toggle("active", !activeFlow && !activeNav);
}

/* ปุ่ม "ทั้งหมด" — ล้างทุกตัวกรองในคลิกเดียว */
function resetAll() {
  clearListFilter();
  if (window.matchMedia("(max-width: 980px)").matches) {
    document.body.classList.remove("nav-open");
  }
}

function clearListFilter() {
  activeFlow = "";
  activeNav  = "";
  sortField  = "";
  sortDir    = "desc";
  ["list-search", "list-days"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  try { localStorage.removeItem(SORT_KEY); } catch (e) { /* โหมดส่วนตัว */ }
  markNavActive();
  applySort();
  applyListFilter();
}

/* ══════════════════════════════════════
   INIT
══════════════════════════════════════ */

(function initNav() {
  const saved = openNodeKeys();
  const nodes = document.querySelectorAll(".nav-node.has-children");

  nodes.forEach(node => {
    const key = node.querySelector(".nav-item")?.dataset.key;
    /* ครั้งแรกที่เข้า (ยังไม่เคยบันทึก) ให้กางไว้ทั้งหมดเพื่อให้เห็นโครงสร้าง */
    node.classList.toggle("open", saved.size ? saved.has(key) : true);
  });

  try {
    if (localStorage.getItem(NAV_HIDDEN_KEY) === "1") {
      document.body.classList.add("nav-hidden");
    }
  } catch (e) { /* โหมดส่วนตัว */ }
})();

/* คืนค่าการเรียงที่เลือกไว้ครั้งก่อน */
(function initSort() {
  try {
    const saved = JSON.parse(localStorage.getItem(SORT_KEY) || "null");
    if (saved && (saved.field === "id" || saved.field === "date")) {
      sortField = saved.field;
      sortDir = saved.dir === "asc" ? "asc" : "desc";
    }
  } catch (e) { /* โหมดส่วนตัว */ }
  applySort();
})();

document.getElementById("list-search")?.addEventListener("input", applyListFilter);
document.getElementById("list-days")?.addEventListener("change", applyListFilter);

setInterval(() => location.reload(), AUTO_REFRESH_MS);
