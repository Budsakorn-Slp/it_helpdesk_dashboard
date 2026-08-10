/* ══════════════════════════════════════════════════════════════════════════
   board.js — เฉพาะหน้าบอร์ด kanban
              (คอลัมน์งาน, โหลดเพิ่ม, กล่องติดตามเอกสาร, ตัวกรอง)

   ต้องโหลด ui.js ก่อนไฟล์นี้ — utility กับ modal ทั้งหมดอยู่ที่นั่น

   ค่าคงที่จาก template: BOARD_KEY, DONE_OFFSET_INIT, DONE_TOTAL_INIT
══════════════════════════════════════════════════════════════════════════ */

const AUTO_REFRESH_MS = 300000;  /* รีเฟรชหน้าทุก 5 นาที */
const DONE_PAGE_SIZE  = 20;
const WAIT_PAGE_SIZE  = 20;

let doneOffset  = DONE_OFFSET_INIT;
let doneTotal   = DONE_TOTAL_INIT;
let doneLoading = false;

let waitShown = Math.min(10, document.querySelectorAll(".wait-item").length);

/* ══════════════════════════════════════
   NAVIGATION
══════════════════════════════════════ */

function scrollToCard(reqId) {
  const el = document.getElementById("card-" + reqId);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.style.outline = "2px solid var(--purple)";
  setTimeout(() => (el.style.outline = ""), 1500);
}

function toggleSection(id) {
  document.getElementById(id).classList.toggle("collapsed");
}

/* ══════════════════════════════════════
   คอลัมน์ "เสร็จแล้ว"
══════════════════════════════════════ */

function makeDoneCardHtml(reqId, name, workerLabel) {
  return `
    <div class="work-card card-done" onclick="openDetailModal('${escHtml(reqId)}')" style="cursor:pointer">
      <div class="card-id" style="color:var(--gray)">${escHtml(reqId)}</div>
      <div class="card-name">${escHtml(name)}</div>
      <div style="font-size:11px;color:var(--green);display:flex;align-items:center;gap:3px;margin-top:3px">
        <svg width="10" height="10" stroke="var(--green)" fill="none" stroke-width="2.5"><use href="#ic-check"/></svg>
        ${escHtml(workerLabel)}
      </div>
    </div>`;
}

/* ui.js เรียกตัวนี้หลังปิดงานสำเร็จ — ย้ายการ์ดไปคอลัมน์เสร็จแล้วโดยไม่ต้องรีโหลด */
function onJobClosed(reqId) {
  const card = document.getElementById("card-" + reqId);
  if (card) {
    card.style.opacity = "0.3";
    card.style.pointerEvents = "none";
  }
  const doneBody = document.getElementById("done-body");
  const name     = card?.querySelector(".card-name")?.textContent?.trim() || "";
  doneBody.querySelector(".empty-state")?.remove();
  doneBody.insertAdjacentHTML("afterbegin", makeDoneCardHtml(reqId, name, "เสร็จแล้ว"));
  setTimeout(() => card?.remove(), 400);
}

async function loadMoreDone() {
  if (doneLoading || doneOffset >= doneTotal) return;
  doneLoading = true;

  const btn = document.getElementById("done-load-btn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<svg width="11" height="11" stroke="currentColor" fill="none" stroke-width="2"><use href="#ic-clock"/></svg> กำลังโหลด...`;
  }

  try {
    const data = await getJson(`/api/done_page/${BOARD_KEY}?offset=${doneOffset}&limit=${DONE_PAGE_SIZE}`);
    if (data.ok && data.items?.length) {
      const body = document.getElementById("done-body");
      body.querySelector(".empty-state")?.remove();

      let prevDate = body.querySelector(".day-group:last-of-type .day-label")?.textContent?.trim() || "";

      data.items.forEach(r => {
        const finishDate = (r.date_finish || r.request_date || "").substring(0, 10);
        if (finishDate && finishDate !== prevDate) {
          prevDate = finishDate;
          body.insertAdjacentHTML("beforeend",
            `<div class="day-group day-other" style="margin-top:6px"><div class="day-label">${escHtml(finishDate)}</div></div>`);
        }
        const name = `${r.requester_fname || ""} ${r.requester_lname || ""}`.trim() || "—";
        body.insertAdjacentHTML("beforeend",
          makeDoneCardHtml(r.request_id, name, r.request_action ? "เสร็จโดย " + r.request_action : ""));
      });

      doneOffset += data.items.length;
      const shownEl = document.getElementById("done-shown-count");
      if (shownEl) shownEl.textContent = doneOffset;
      if (doneOffset >= doneTotal) document.getElementById("done-load-more")?.remove();
    } else {
      document.getElementById("done-load-more")?.remove();
    }
  } catch (e) {
    toast("โหลดไม่ได้", true);
  }

  doneLoading = false;
  if (btn) {
    btn.disabled = false;
    btn.innerHTML = `<svg width="11" height="11" stroke="currentColor" fill="none" stroke-width="2"><use href="#ic-load-more"/></svg> โหลดเพิ่มเติม`;
  }
}

/* ══════════════════════════════════════
   กล่อง "รออนุมัติ" (โหลดเพิ่มฝั่ง client)
══════════════════════════════════════ */

function loadMoreWaiting() {
  const allItems = document.querySelectorAll(".wait-item");
  const newLimit = Math.min(waitShown + WAIT_PAGE_SIZE, allItems.length);
  for (let i = waitShown; i < newLimit; i++) allItems[i].style.display = "";
  waitShown = newLimit;

  const shownEl = document.getElementById("wait-shown-count");
  if (shownEl) shownEl.textContent = waitShown;
  if (waitShown >= allItems.length) document.getElementById("wait-load-more")?.remove();
}

/* ══════════════════════════════════════
   กล่อง "ติดตามเอกสาร" (เฉพาะบอร์ด asset)
══════════════════════════════════════ */

function trackingCardHtml(item) {
  const reqId = escHtml(item.request_id || "");
  const name  = escHtml(`${item.requester_fname || ""} ${item.requester_lname || ""}`.trim() || "—");
  const dept  = (item.requester_dept || "").trim();
  const label = escHtml(TRANSFER_TYPE_LABEL[(item.transfer_type || "").toUpperCase()] || item.transfer_type || "");
  const deptHtml = dept ? `<div class="mini-dept">${escHtml(dept)}</div>` : "";

  if (!item.is_complete) {
    return `
      <div class="mini-card" style="border-left:3px solid var(--yellow)">
        <div class="mini-id">${reqId}</div>
        <div class="mini-name">${name}</div>
        ${deptHtml}
        <div style="display:flex;align-items:center;justify-content:space-between;margin-top:4px">
          <span style="font-size:10px;background:#fff3cd;color:#856404;padding:2px 7px;border-radius:4px">${label}</span>
          <span style="font-size:10px;color:var(--yellow)">⏳ รอลายเซ็นครบ</span>
        </div>
      </div>`;
  }

  return `
    <div class="mini-card" style="border-left:3px solid var(--green)">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:4px">
        <div>
          <div class="mini-id" style="color:var(--green)">${reqId}</div>
          <div class="mini-name">${name}</div>
          ${deptHtml}
        </div>
        <span style="font-size:10px;background:#e8f5e9;color:#2e7d32;padding:2px 7px;border-radius:4px;white-space:nowrap">${label}</span>
      </div>
      <div style="display:flex;gap:5px;margin-top:5px">
        <button class="btn-close-job" style="font-size:11px;padding:3px 10px;flex:1"
                onclick="openCloseTrackModal('${reqId}')">✔ ปิดงาน</button>
        <button class="btn-detail-sm" onclick="openDetailModal('${reqId}')">
          <svg width="10" height="10" stroke="currentColor" fill="none" stroke-width="2"><use href="#ic-detail"/></svg>
        </button>
      </div>
    </div>`;
}

async function loadTracking() {
  const body    = document.getElementById("tracking-body");
  const countEl = document.getElementById("tracking-count");
  if (!body) return;

  try {
    const data = await getJson("/api/tracking");
    if (!data.ok) {
      body.innerHTML = '<div class="empty-state">โหลดข้อมูลไม่ได้</div>';
      return;
    }

    const items = data.items || [];
    if (countEl) countEl.textContent = items.length;
    if (!items.length) {
      body.innerHTML = '<div class="empty-state" style="padding:10px">ไม่มีรายการติดตาม</div>';
      return;
    }

    /* เอกสารที่ลายเซ็นครบขึ้นก่อน แล้วเรียงใหม่→เก่าในแต่ละกลุ่ม */
    const byDateDesc = (a, b) => (b.request_date || "").localeCompare(a.request_date || "");
    const complete   = items.filter(i => i.is_complete).sort(byDateDesc);
    const incomplete = items.filter(i => !i.is_complete).sort(byDateDesc);

    body.style.maxHeight = "320px";
    body.innerHTML = [...complete, ...incomplete].map(trackingCardHtml).join("");
  } catch (e) {
    body.innerHTML = '<div class="empty-state">Connection error</div>';
  }
}

/* ══════════════════════════════════════
   FILTER BAR — ค้นหาเลขเอกสาร / ชื่อผู้แจ้ง
══════════════════════════════════════ */

function applyBoardFilter() {
  const searchId   = (document.getElementById("search-id")?.value || "").trim();
  const filterName = (document.getElementById("filter-name")?.value || "").trim().toLowerCase();

  let visibleCount = 0;

  const matches = (id, name) =>
    (!searchId || id.startsWith(searchId)) &&
    (!filterName || name.includes(filterName));

  /* การ์ดในคอลัมน์ พร้อมทำ / กำลังทำ / เสร็จแล้ว */
  document.querySelectorAll(".work-card").forEach(card => {
    /* การ์ด done ไม่มี id attribute — ใช้ข้อความใน .card-id แทน */
    const cardId = (card.id || "").replace("card-", "") ||
                   (card.querySelector(".card-id")?.textContent || "").trim();
    const cardName = (card.querySelector(".card-name")?.textContent || "").toLowerCase();
    const show = matches(cardId, cardName);
    card.style.display = show ? "" : "none";
    if (show) visibleCount++;
  });

  /* ซ่อนหัววันที่ที่ไม่เหลือการ์ดแล้ว */
  document.querySelectorAll(".day-group").forEach(group => {
    const hasVisible = Array.from(group.querySelectorAll(".work-card"))
      .some(c => c.style.display !== "none");
    group.style.display = hasVisible ? "" : "none";
  });

  /* แถบเวลาด้านซ้าย */
  document.querySelectorAll(".tl-item").forEach(item => {
    const itemId = item.getAttribute("onclick")?.match(/\d+/)?.[0] || "";
    item.style.display = (!searchId || itemId.startsWith(searchId)) ? "" : "none";
  });

  /* การ์ดเล็กในแถบล่าง (รออนุมัติ / ยกเลิก) */
  document.querySelectorAll(".mini-card").forEach(card => {
    const cardId   = (card.querySelector(".mini-id")?.textContent || "").trim();
    const cardName = (card.querySelector(".mini-name")?.textContent || "").toLowerCase();
    card.style.display = matches(cardId, cardName) ? "" : "none";
  });

  const countEl = document.querySelector(".filter-count");
  if (countEl) countEl.textContent = (searchId || filterName) ? `พบ ${visibleCount} รายการ` : "";
}

function clearBoardFilter() {
  ["search-id", "filter-name", "filter-date"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  document.querySelectorAll(".work-card, .tl-item, .mini-card, .day-group")
    .forEach(el => (el.style.display = ""));

  const countEl = document.querySelector(".filter-count");
  if (countEl) countEl.textContent = "";
}

/* ══════════════════════════════════════
   INIT
══════════════════════════════════════ */

["search-id", "filter-name"].forEach(id => {
  document.getElementById(id)?.addEventListener("input", applyBoardFilter);
});

if (BOARD_KEY === "asset") loadTracking();

setInterval(() => location.reload(), AUTO_REFRESH_MS);
