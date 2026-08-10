/* ══════════════════════════════════════════════════════════════════════════
   asset_list.js — เฉพาะหน้า /asset แบบรายการเอกสาร
                   (กรองด้วยการ์ดสถิติ / คำค้น / ประเภท / ช่วงวันที่)

   ต้องโหลด ui.js ก่อนไฟล์นี้ — utility กับ modal ทั้งหมดอยู่ที่นั่น
   ทุกแถวเป็น <tr class="list-row"> ที่มี data-flow / data-type /
   data-date / data-search มาจาก server แล้ว จึงกรองฝั่ง client ได้ทันที
══════════════════════════════════════════════════════════════════════════ */

const AUTO_REFRESH_MS = 300000;   /* รีเฟรชหน้าทุก 5 นาที */
const MS_PER_DAY      = 86400000;

let activeFlow = "";              /* การ์ดสถิติที่เลือกอยู่ ("" = ทั้งหมด) */

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
   FILTER
══════════════════════════════════════ */

function applyListFilter() {
  const term = (document.getElementById("list-search")?.value || "").trim().toLowerCase();
  const type = document.getElementById("list-type")?.value || "";
  const days = parseInt(document.getElementById("list-days")?.value || "", 10);

  let shown = 0;

  document.querySelectorAll(".list-row").forEach(row => {
    const matchFlow = !activeFlow || row.dataset.flow === activeFlow;
    const matchType = !type || row.dataset.type === type;
    const matchTerm = !term || (row.dataset.search || "").includes(term);

    let matchDate = true;
    if (!Number.isNaN(days)) {
      const date = parseDocDate(row.dataset.date);
      matchDate = date ? daysAgo(date) < days : false;
    }

    const show = matchFlow && matchType && matchTerm && matchDate;
    row.style.display = show ? "" : "none";
    if (show) shown++;
  });

  const noMatch = document.getElementById("list-no-match");
  const hasFilter = activeFlow || type || term || !Number.isNaN(days);
  if (noMatch) noMatch.style.display = (shown === 0 && hasFilter) ? "" : "none";

  const countEl = document.getElementById("list-count");
  if (countEl) countEl.textContent = hasFilter ? `พบ ${shown} รายการ` : "";
}

/* คลิกการ์ดสถิติ = กรองตามสถานะงาน (คลิกซ้ำเพื่อยกเลิก) */
function filterByFlow(card) {
  const flow = card.dataset.flow || "";
  activeFlow = (activeFlow === flow && flow !== "") ? "" : flow;

  document.querySelectorAll(".stat-card").forEach(el => {
    el.classList.toggle("active", (el.dataset.flow || "") === activeFlow);
  });
  applyListFilter();
}

function clearListFilter() {
  activeFlow = "";
  ["list-search", "list-type", "list-days"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  document.querySelectorAll(".stat-card").forEach(el => {
    el.classList.toggle("active", !el.dataset.flow);
  });
  applyListFilter();
}

/* ══════════════════════════════════════
   INIT
══════════════════════════════════════ */

document.getElementById("list-search")?.addEventListener("input", applyListFilter);
document.getElementById("list-type")?.addEventListener("change", applyListFilter);
document.getElementById("list-days")?.addEventListener("change", applyListFilter);

setInterval(() => location.reload(), AUTO_REFRESH_MS);
