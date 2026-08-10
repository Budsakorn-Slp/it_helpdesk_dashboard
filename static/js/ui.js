/* ══════════════════════════════════════════════════════════════════════════
   ui.js — ส่วนที่หน้าบอร์ดและหน้ารายการเอกสารใช้ร่วมกัน
            (utility, นาฬิกา, รายชื่อ IT, modal ทุกตัว, timeline, คอมเมนต์)

   ค่าคงที่ที่ template ต้องประกาศไว้ก่อนโหลดไฟล์นี้:
     STATUS_LABEL         รหัสสถานะ → ป้ายไทย (มาจาก config.STATUS_MAP)
     TRANSFER_TYPE_LABEL  ประเภทเอกสาร → ป้ายไทย (มาจาก config.TRANSFER_TYPES)

   markup ของ modal อยู่ใน templates/_modals.html
══════════════════════════════════════════════════════════════════════════ */

/* ── Constants ── */

const WORKFLOW_TITLE_MAP = {
  receiver: "ผู้รับปลายทาง",
  manager:  "ผู้อนุมัติ",
  approve:  "อนุมัติ",
  reject:   "ปฏิเสธ",
  it_close: "ปิดงานโดย IT",
};

const RELOAD_DELAY_MS = 800;   /* หน่วงให้ toast ขึ้นก่อนรีโหลด */
const FILE_BASE       = "/uploads/";
const IMG_EXT         = /\.(jpg|jpeg|png|gif|webp|bmp)$/i;

const STATUS_WAIT   = "0";
const STATUS_READY  = "1";
const STATUS_DOING  = "2";
const STATUS_CANCEL = "3";
const STATUS_APPROVE_WAIT = "4";
const STATUS_DONE   = "5";

/* ── State ── */
let currentReqId       = "";   /* modal รับงาน */
let closeReqId         = "";   /* modal ปิดงาน */
let currentDetailReqId = "";   /* modal รายละเอียด */
let approveReqId       = "";
let cancelReqId        = "";
let closeTrackReqId    = "";   /* modal ปิดงานเอกสาร */
let currentStatusReqId = "";
let currentStatusOld   = "";

let empLoaded = false;
let empList   = [];

/* ══════════════════════════════════════
   UTILITIES
══════════════════════════════════════ */

function escHtml(str) {
  return String(str == null ? "" : str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function toast(msg, isError = false) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className   = "toast show" + (isError ? " err" : "");
  setTimeout(() => (el.className = "toast"), 3000);
}

function reloadSoon() {
  setTimeout(() => location.reload(), RELOAD_DELAY_MS);
}

function closeAllModals() {
  document.querySelectorAll(".modal-overlay, .detail-overlay")
    .forEach(el => el.classList.remove("open"));
}

function openModal(id) {
  document.getElementById(id)?.classList.add("open");
}

function hideModal(id) {
  document.getElementById(id)?.classList.remove("open");
}

async function getJson(url) {
  const res = await fetch(url);
  return res.json();
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });
  return res.json();
}

/* ส่ง action แล้วรีโหลดหน้าเมื่อสำเร็จ — รูปแบบที่ทุกปุ่มใช้ร่วมกัน */
async function submitAction(url, body, successMsg, onSuccess) {
  try {
    const data = await postJson(url, body);
    if (!data.ok) {
      toast(data.msg || "error", true);
      return false;
    }
    toast(successMsg);
    if (onSuccess) onSuccess();
    else reloadSoon();
    return true;
  } catch (e) {
    toast("Connection error", true);
    return false;
  }
}

/* ══════════════════════════════════════
   CLOCK
══════════════════════════════════════ */

function updateClock() {
  const clock = document.getElementById("clock");
  const dateTxt = document.getElementById("dateTxt");
  if (!clock && !dateTxt) return;

  const now = new Date();
  if (clock) clock.textContent = now.toLocaleTimeString("th-TH", { hour12: false });
  if (dateTxt) {
    dateTxt.textContent = now.toLocaleDateString("th-TH",
      { weekday: "long", year: "numeric", month: "long", day: "numeric" });
  }
}

/* ══════════════════════════════════════
   รายชื่อพนักงาน IT
══════════════════════════════════════ */

/* โหลดรายชื่อ IT ครั้งเดียวแล้ว cache ไว้ */
async function fetchEmpList() {
  if (empLoaded) return empList;
  try {
    const data = await getJson("/api/employees");
    if (data.ok && data.employees?.length) {
      empList   = data.employees;
      empLoaded = true;
    }
  } catch (e) { /* ปล่อยให้ dropdown ว่าง แล้วแจ้งผ่าน placeholder */ }
  return empList;
}

/* เติมรายชื่อลง <select> ใด ๆ — ใช้ร่วมกันทุก modal */
async function fillEmpSelect(selectId, placeholder = "เลือก IT", selected = "") {
  const select = document.getElementById(selectId);
  if (!select) return;

  select.innerHTML = "";
  select.appendChild(new Option("กำลังโหลด...", ""));

  const names = await fetchEmpList();
  select.innerHTML = "";
  if (!names.length) {
    select.appendChild(new Option("-- ไม่พบรายชื่อ --", ""));
    return;
  }
  select.appendChild(new Option(placeholder, ""));
  names.forEach(name => select.appendChild(new Option(name, name, false, name === selected)));
}

/* รายชื่อ IT พร้อมรหัสพนักงาน — ใช้เป็นผู้ดำเนินการตอนเปลี่ยนสถานะ */
async function loadItEmployees() {
  const select = document.getElementById("status-it-user");
  if (!select) return;
  try {
    const data = await getJson("/api/it_employees");
    select.innerHTML = "";
    select.appendChild(new Option("เลือก IT", ""));
    (data.items || []).forEach(it => select.appendChild(new Option(it.first_name, it.emp_id)));
  } catch (e) {
    console.error(e);
  }
}

/* ══════════════════════════════════════
   MODAL: รับงาน / เปลี่ยนผู้ทำ
══════════════════════════════════════ */

function openStartModal(reqId) {
  closeAllModals();
  currentReqId = reqId;
  document.getElementById("modal-req-id").textContent = reqId;
  const sel = document.getElementById("emp-select");
  sel.value = "";
  sel.style.borderColor = "";
  openModal("modal-start");
  fillEmpSelect("emp-select", "-- เลือกชื่อ --");
}

function closeStartModal() {
  hideModal("modal-start");
  currentReqId = "";
}

async function confirmStart() {
  const sel    = document.getElementById("emp-select");
  const worker = sel.value.trim();
  if (!worker) {
    sel.style.borderColor = "#e74c3c";
    toast("กรุณาเลือกผู้รับผิดชอบ", true);
    return;
  }
  sel.style.borderColor = "";
  const reqId = currentReqId;
  closeStartModal();
  await submitAction("/api/start", { request_id: reqId, worker },
                     `รับงาน ${reqId} — ${worker}`);
}

/* ══════════════════════════════════════
   MODAL: ปิดงาน
══════════════════════════════════════ */

function openCloseModal(reqId) {
  closeAllModals();
  closeReqId = reqId;
  document.getElementById("modal-close-req-id").textContent = reqId;
  openModal("modal-close");
  fillEmpSelect("close-job-it-sel");
}

function closeCloseModal() {
  hideModal("modal-close");
  closeReqId = "";
}

async function confirmClose() {
  const itName = document.getElementById("close-job-it-sel").value;
  if (!itName) { toast("กรุณาเลือก IT", true); return; }

  const reqId = closeReqId;
  closeCloseModal();
  await submitAction("/api/close", { request_id: reqId, it_name: itName },
                     `ปิดงาน ${reqId} เสร็จแล้ว`,
                     typeof onJobClosed === "function" ? () => onJobClosed(reqId) : null);
}

/* ══════════════════════════════════════
   MODAL: IT อนุมัติ / IT ยกเลิก
══════════════════════════════════════ */

function approveByIT(reqId) {
  closeAllModals();
  approveReqId = reqId;
  document.getElementById("modal-approve-req-id").textContent = reqId;
  openModal("modal-approve-it");
  fillEmpSelect("approve-it-sel");
}

function closeApproveModal() {
  hideModal("modal-approve-it");
  approveReqId = "";
}

async function confirmApproveIT() {
  const itName = document.getElementById("approve-it-sel").value;
  if (!itName) { toast("กรุณาเลือก IT", true); return; }
  if (!confirm("ยืนยันว่า IT จะอนุมัติเอง?")) return;

  const reqId = approveReqId;
  closeApproveModal();
  await submitAction("/api/approve_it", { request_id: reqId, it_name: itName },
                     "IT อนุมัติสำเร็จ");
}

function cancelByIT(reqId) {
  closeAllModals();
  cancelReqId = reqId;
  document.getElementById("modal-cancel-req-id").textContent = reqId;
  openModal("modal-cancel-it");
  fillEmpSelect("cancel-it-sel");
}

function closeCancelModal() {
  hideModal("modal-cancel-it");
  cancelReqId = "";
}

async function confirmCancelIT() {
  const itName = document.getElementById("cancel-it-sel").value;
  if (!itName) { toast("กรุณาเลือก IT", true); return; }
  if (!confirm("ยืนยันยกเลิกงานนี้?")) return;

  const reqId = cancelReqId;
  closeCancelModal();
  await submitAction("/api/cancel_it", { request_id: reqId, it_name: itName }, "ยกเลิกสำเร็จ");
}

/* ══════════════════════════════════════
   MODAL: ปิดงานเอกสาร (tracking)
══════════════════════════════════════ */

function openCloseTrackModal(reqId) {
  closeAllModals();
  closeTrackReqId = reqId;
  const label = document.getElementById("close-track-req-id");
  if (label) label.textContent = reqId;
  openModal("close-track-modal");
  fillEmpSelect("close-track-it");
}

/* เปิดจากในหน้ารายละเอียด — ปิด modal รายละเอียดก่อน */
function openCloseTrackFromDetail(reqId) {
  hideModal("modal-detail");
  openCloseTrackModal(reqId);
}

function closeTrackModal() {
  hideModal("close-track-modal");
  closeTrackReqId = "";
}

async function submitCloseTracking() {
  const itName = document.getElementById("close-track-it").value;
  if (!itName) { toast("กรุณาเลือก IT", true); return; }

  const reqId = closeTrackReqId;
  closeTrackModal();
  await submitAction("/api/close_tracking", { request_id: reqId, it_name: itName },
                     "ปิดงานสำเร็จ");
}

/* ══════════════════════════════════════
   MODAL: เปลี่ยนสถานะ
══════════════════════════════════════ */

function openStatusModal(reqId, currentStatus) {
  currentStatusReqId = reqId;
  document.getElementById("status-modal-wrap").classList.add("show");

  const hidden = document.getElementById("status-select");
  const currentVal = currentStatus || hidden?.value || STATUS_WAIT;
  if (hidden) hidden.value = currentVal;

  currentStatusOld = currentVal;
  document.getElementById("status-current-label").textContent = STATUS_LABEL[currentVal] || "-";

  const matchItem = document.querySelector(`#status-cdd-list .cdd-item[data-value="${currentVal}"]`);
  if (matchItem) selectCdd(matchItem);

  loadItEmployees().then(updateStatusSummary);
}

function closeStatusModal() {
  document.getElementById("status-modal-wrap").classList.remove("show");
}

function updateStatusSummary() {
  const summary = document.getElementById("status-summary");
  if (!summary) return;

  const statusValue = document.getElementById("status-select").value;
  const empSelect   = document.getElementById("status-it-user");
  const empText     = empSelect.options[empSelect.selectedIndex]?.text || "-";

  summary.innerHTML = `
    เปลี่ยนสถานะจาก <b>${escHtml(STATUS_LABEL[currentStatusOld] || "-")}</b>
    → <b>${escHtml(STATUS_LABEL[statusValue] || "-")}</b>
    <br><br>โดย: <b>${escHtml(empText)}</b>
  `;
}

async function confirmStatusChange() {
  const newStatus  = document.getElementById("status-select").value;
  const actionBy   = document.getElementById("status-it-user").value;
  const actionNote = (document.getElementById("status-note")?.value || "").trim();

  if (!actionBy) { toast("กรุณาเลือก IT", true); return; }

  await submitAction("/api/change_status", {
    request_id:  currentStatusReqId,
    new_status:  newStatus,
    action_by:   actionBy,
    action_note: actionNote,
  }, "บันทึกสถานะสำเร็จ");
}

/* ── Custom dropdown ของสถานะ ── */

function toggleCdd() {
  document.getElementById("status-cdd-wrap").classList.toggle("open");
}

function selectCdd(el) {
  document.getElementById("status-select").value = el.dataset.value;

  const selected = document.getElementById("status-cdd-selected");
  selected.style.background = el.style.background;
  selected.style.color      = el.style.color;
  document.getElementById("status-cdd-label").textContent = el.textContent;

  document.getElementById("status-cdd-wrap").classList.remove("open");
  updateStatusSummary();
}

/* ══════════════════════════════════════
   DETAIL MODAL
══════════════════════════════════════ */

function closeDetailModal() {
  hideModal("modal-detail");
}

/* ป้ายสถานะ — ใช้ approver_status ประกอบด้วยเหมือนที่แสดงบนการ์ด */
function detailStatusBadge(d) {
  const approver = (d.approver_status || "Waiting").trim();
  const status   = (d.request_status || STATUS_WAIT).trim();

  if (status === STATUS_DONE)         return ["เสร็จ", "status-5"];
  if (status === STATUS_CANCEL)       return ["ยกเลิก", "status-3"];
  if (status === STATUS_DOING)        return ["กำลังทำ", "status-2"];
  if (approver === "Approve")         return ["อนุมัติแล้ว (รอ IT ดำเนินการ)", "status-1"];
  if (approver === "Reject")          return ["ยกเลิก", "status-3"];
  if (status === STATUS_APPROVE_WAIT) return ["รออนุมัติ", "status-4"];
  return [STATUS_LABEL[status] || "-", "status-" + status];
}

/* แถบผู้รับผิดชอบ + ปุ่มบนหัว modal ให้ตรงกับสถานะของงาน */
function applyDetailActions(overlay, d) {
  const bar       = overlay.querySelector(".dm-assignee-bar");
  const btnStatus = overlay.querySelector("#btn-change-status");
  const btnWorker = overlay.querySelector("#btn-change-worker");
  const btnClose  = overlay.querySelector("#btn-close-tracking");
  const status    = d.request_status;

  [bar, btnStatus, btnWorker].forEach(el => { if (el) el.style.display = ""; });
  if (btnClose) btnClose.style.display = "none";

  if (d.is_tracking) {
    /* เอกสารติดตาม: เปลี่ยนสถานะ/ผู้ทำเองไม่ได้ ต้องรอลายเซ็นครบแล้วกดปิดงาน */
    if (btnStatus) btnStatus.style.display = "none";
    if (btnWorker) btnWorker.style.display = "none";
    if (btnClose)  btnClose.style.display  = d.transfer_complete ? "" : "none";
    if (bar && status === STATUS_DONE) bar.style.display = "none";
    return;
  }
  /* พร้อมทำ / รออนุมัติ: ยังไม่มีผู้รับผิดชอบ จึงซ่อนแถบทั้งแถบ */
  if ((status === STATUS_READY || status === STATUS_APPROVE_WAIT) && bar) {
    bar.style.display = "none";
  }
}

function detailAttachHtml(fileName) {
  const name = (fileName || "").trim();
  if (!name) return '<span class="attach-none">ไม่มีไฟล์แนบ</span>';

  const url = FILE_BASE + encodeURIComponent(name);
  return IMG_EXT.test(name)
    ? `<a href="${url}" target="_blank" class="attach-img-wrap">
         <img src="${url}" class="attach-img-preview">
         <div class="attach-img-name">${escHtml(name)}</div>
       </a>`
    : `<a class="attach-link" href="${url}" target="_blank">${escHtml(name)}</a>`;
}

function detailSection(icon, title) {
  return `<div class="dm-section">
            <div class="dm-section-icon">${icon}</div>
            <div class="dm-section-title">${escHtml(title)}</div>
          </div>`;
}

function detailIcon(id) {
  return `<svg width="16" height="16" fill="none" stroke="var(--purple)" stroke-width="2"><use href="#${id}"/></svg>`;
}

function detailCell(label, value, fullWidth = false) {
  return `<div class="dm-info-cell"${fullWidth ? ' style="grid-column:1/-1"' : ""}>
            <div class="dm-info-label">${escHtml(label)}</div>
            <div class="dm-info-value">${value}</div>
          </div>`;
}

function renderDetailBody(d) {
  const fullname = `${d.requester_fname || ""} ${d.requester_lname || ""}`.trim() || "—";

  const attachSection = (d.request_file || "").trim()
    ? detailSection(detailIcon("ic-attach"), "ไฟล์แนบ") +
      `<div class="dm-attach-box">${detailAttachHtml(d.request_file)}</div>`
    : "";

  const solutionSection = (d.request_solution || "").trim()
    ? detailSection(detailIcon("ic-check"), "วิธีแก้ไข / ผลการดำเนินการ") +
      `<div class="dm-remark-box">
         <textarea class="dm-remark-area" rows="4" readonly>${escHtml(d.request_solution)}</textarea>
       </div>`
    : "";

  /* คอมเมนต์ได้เฉพาะงานที่กด "เริ่มทำ" แล้ว */
  const commentSection = d.request_status === STATUS_DOING
    ? `<div class="add-comment-title">เพิ่มคอมเมนต์ใหม่</div>
       <textarea class="d-val-area editable" id="it-comment-text" rows="3" placeholder="พิมพ์คอมเมนต์..."></textarea>
       <div class="it-comment-by-row">
         <span class="it-comment-by-label">โดย:</span>
         <select class="emp-select" id="it-comment-by-select" style="margin-bottom:0;flex:1;width:auto"></select>
       </div>
       <button class="btn-save-comment" id="btn-save-comment"
               onclick="saveComment('${escHtml(d.request_id)}')">เพิ่มคอมเมนต์</button>`
    : '<div class="comment-locked">กดปุ่ม &quot;เริ่มทำ&quot; ก่อนจึงจะเพิ่มคอมเมนต์ได้</div>';

  return (
    detailSection(detailIcon("ic-user"), "ข้อมูลผู้แจ้ง") +
    `<div class="dm-info-grid">
       ${detailCell("ชื่อ–นามสกุล", escHtml(fullname))}
       ${detailCell("แผนก / ฝ่าย", escHtml(d.requester_dept || "—"))}
       ${detailCell("เบอร์โทรศัพท์", escHtml(d.requester_tel || "—"))}
       ${detailCell("รหัสพนักงาน", escHtml(d.requester_empcode || "—"))}
       ${d.requester_email ? detailCell("อีเมล", escHtml(d.requester_email), true) : ""}
     </div>` +
    detailSection(detailIcon("ic-msg"), "รายละเอียดคำขอ") +
    `<div class="dm-info-grid">
       ${detailCell("หมวดหมู่", `<span class="dm-category-badge">${escHtml(d.request_category || "—")}</span>`)}
       ${detailCell("ประเภทปัญหา", escHtml(d.request_typeproblem || "—"))}
     </div>
     <div class="dm-remark-box">
       <div class="dm-info-label" style="margin-bottom:6px">รายละเอียด</div>
       <textarea class="dm-remark-area" rows="4" readonly>${escHtml(d.request_remark || "(ไม่มีรายละเอียด)")}</textarea>
     </div>` +
    attachSection +
    solutionSection +
    detailSection("📋", "ลำดับการอนุมัติ") +
    '<div class="comment-timeline" id="approver-history"><div class="comment-empty">กำลังโหลด...</div></div>' +
    detailSection(detailIcon("ic-msg"), "ประวัติคอมเมนต์ IT") +
    '<div class="comment-timeline" id="comment-timeline"><div class="comment-empty">กำลังโหลด...</div></div>' +
    `<div class="add-comment-box" id="add-comment-box">${commentSection}</div>`
  );
}

async function openDetailModal(reqId) {
  currentDetailReqId = reqId;
  const overlay = document.getElementById("modal-detail");
  const body    = document.getElementById("detail-body");

  document.getElementById("d-head-title").textContent = "กำลังโหลด...";
  document.getElementById("d-head-tag").textContent   = "คำขอรับบริการ IT";
  body.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)">กำลังโหลด...</div>';

  closeAllModals();
  overlay.classList.add("open");

  let json;
  try {
    json = await getJson("/api/detail/" + encodeURIComponent(reqId));
  } catch (e) {
    body.innerHTML = '<div style="text-align:center;padding:40px;color:var(--red)">Connection error</div>';
    return;
  }
  if (!json.ok) {
    body.innerHTML = '<div style="text-align:center;padding:40px;color:var(--red)">ไม่พบข้อมูล</div>';
    return;
  }

  const d = json.data;

  document.getElementById("d-head-title").textContent = "คำขอ #" + d.request_id;
  document.getElementById("d-head-tag").textContent   = "ประเภท " + (d.request_typeform || "");

  const [statusLabel, badgeClass] = detailStatusBadge(d);
  const badge = document.getElementById("d-status-badge");
  if (badge) {
    badge.textContent = statusLabel;
    badge.className   = "dm-status-badge " + badgeClass;
  }

  const assigneeName = document.getElementById("d-assignee-name");
  const assigneeDept = document.getElementById("d-assignee-dept");
  if (assigneeName) assigneeName.textContent = d.request_action || "ยังไม่ได้รับมอบหมาย";
  if (assigneeDept) {
    assigneeDept.textContent = d.request_action ? "IT Support" : "";
    assigneeDept.style.display = d.request_action ? "" : "none";
  }

  applyDetailActions(overlay, d);
  body.innerHTML = renderDetailBody(d);

  const statusSelect = document.getElementById("status-select");
  if (statusSelect) statusSelect.value = d.request_status || STATUS_WAIT;

  loadWorkflow(d.request_id);
  loadCommentHistory(d.request_id);
  if (d.request_status === STATUS_DOING) fillEmpSelect("it-comment-by-select", "-- เลือกชื่อ --");
}

/* ══════════════════════════════════════
   WORKFLOW TIMELINE
══════════════════════════════════════ */

async function loadWorkflow(reqId) {
  const box = document.getElementById("approver-history");
  if (!box) return;
  box.innerHTML = '<div class="comment-empty">กำลังโหลด...</div>';

  try {
    const data = await getJson("/api/approvers/" + encodeURIComponent(reqId));
    if (!data.ok) {
      box.innerHTML = '<div class="comment-empty">โหลดข้อมูลไม่ได้</div>';
      return;
    }
    const items = data.items || [];
    if (!items.length) {
      box.innerHTML = '<div class="comment-empty">ไม่มี workflow</div>';
      return;
    }

    box.innerHTML = items.map(step => {
      const approved = step.status === "approved";
      const rejected = step.status === "reject";
      const badge = approved ? "✓" : rejected ? "✖" : "⏳";
      const color = approved ? "#16a34a" : rejected ? "#dc2626" : "#f59e0b";
      const title = WORKFLOW_TITLE_MAP[step.title] || step.title || "-";
      return `
        <div class="comment-item">
          <div class="comment-avatar" style="background:${color};border-color:${color};color:#fff">${badge}</div>
          <div class="comment-bubble">
            <div class="comment-meta">
              <span class="comment-by">${escHtml(title)}</span>
              <span class="comment-date">${escHtml(step.date || "-")}</span>
            </div>
            <div class="comment-text">โดย: ${escHtml(step.by || "-")}</div>
          </div>
        </div>`;
    }).join("");
  } catch (e) {
    box.innerHTML = '<div class="comment-empty">Connection error</div>';
  }
}

/* ══════════════════════════════════════
   COMMENT TIMELINE
══════════════════════════════════════ */

async function loadCommentHistory(reqId) {
  const tl = document.getElementById("comment-timeline");
  if (!tl) return;
  try {
    const data = await getJson("/api/comments/" + encodeURIComponent(reqId));
    renderTimeline(data.comments || []);
  } catch (e) {
    tl.innerHTML = '<div class="comment-empty">โหลดไม่ได้</div>';
  }
}

function renderTimeline(comments) {
  const tl = document.getElementById("comment-timeline");
  if (!tl) return;
  if (!comments.length) {
    tl.innerHTML = '<div class="comment-empty">ยังไม่มีคอมเมนต์</div>';
    return;
  }
  tl.innerHTML = comments.map(c => {
    const initial = (c.comment_by || "IT").charAt(0).toUpperCase();
    return `
      <div class="comment-item">
        <div class="comment-avatar">${escHtml(initial)}</div>
        <div class="comment-bubble">
          <div class="comment-meta">
            <span class="comment-by">${escHtml(c.comment_by || "IT")}</span>
            <span class="comment-date">${escHtml(c.comment_date || "")}</span>
          </div>
          <div class="comment-text">${escHtml(c.comment_text || "")}</div>
        </div>
      </div>`;
  }).join("");
}

async function saveComment(reqId) {
  const text      = document.getElementById("it-comment-text").value.trim();
  const select    = document.getElementById("it-comment-by-select");
  const commentBy = select ? select.value.trim() : "";
  const btn       = document.getElementById("btn-save-comment");

  if (!text) { toast("กรุณากรอกคอมเมนต์", true); return; }
  if (!commentBy) {
    if (select) select.style.borderColor = "#e74c3c";
    toast("กรุณาเลือกชื่อผู้คอมเมนต์", true);
    return;
  }
  if (select) select.style.borderColor = "";

  btn.disabled = true;
  btn.textContent = "กำลังบันทึก...";

  const ok = await submitAction("/api/comment",
    { request_id: reqId, comment: text, comment_by: commentBy },
    "เพิ่มคอมเมนต์สำเร็จ",
    () => { closeDetailModal(); reloadSoon(); });

  if (!ok) {
    btn.disabled = false;
    btn.innerHTML = `<svg width="12" height="12" stroke="#fff" fill="none" stroke-width="2"><use href="#ic-save"/></svg> เพิ่มคอมเมนต์`;
  }
}

/* ══════════════════════════════════════
   EVENT LISTENERS ที่ทุกหน้าใช้ร่วมกัน
══════════════════════════════════════ */

document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeAllModals();
});

document.addEventListener("change", e => {
  if (e.target.id === "status-select" || e.target.id === "status-it-user") updateStatusSummary();
});

/* ปิด dropdown สถานะเมื่อคลิกนอกกรอบ */
document.addEventListener("click", e => {
  const wrap = document.getElementById("status-cdd-wrap");
  if (wrap && !wrap.contains(e.target)) wrap.classList.remove("open");
});

/* คลิกพื้นหลัง modal = ปิด */
[["modal-detail", closeDetailModal],
 ["modal-start", closeStartModal],
 ["modal-close", closeCloseModal],
 ["modal-cancel-it", closeCancelModal],
 ["modal-approve-it", closeApproveModal],
 ["close-track-modal", closeTrackModal]].forEach(([id, close]) => {
  document.getElementById(id)?.addEventListener("click", function (e) {
    if (e.target === this) close();
  });
});

updateClock();
setInterval(updateClock, 1000);
