// ─────────────────────────────────────────────
//  State
// ─────────────────────────────────────────────
const opSel       = document.getElementById('operator');
const opAvatar    = document.getElementById('opAvatar');
const contentArea = document.getElementById('content-area');
const opHint      = document.getElementById('op-hint');
const logBody     = document.getElementById('logBody');
const singleFields = ['f_company','f_costdep','f_department','f_costcenter','f_desc','f_status','f_code'];

let parsedRows = [];
//: ผลจับคู่ "ฟิลด์ในระบบ → ชื่อหัวคอลัมน์ในไฟล์" ของไฟล์ที่เลือกอยู่
let parsedCols = {};
//: ข้อมูลที่กรอกไว้ตอนเจอ Cost Center ซ้ำ — รอผู้ใช้กดยืนยันก่อนอัปเดตทับ
let pendingSave = null;

// ─────────────────────────────────────────────
//  Operator
// ─────────────────────────────────────────────
function checkOperator() {
  if (opSel.value) {
    contentArea.style.display = 'block';
    opHint.style.display      = 'none';
    const name = opSel.options[opSel.selectedIndex].textContent;
    opAvatar.textContent = name.trim()[0] || '?';
  } else {
    contentArea.style.display = 'none';
    opHint.style.display      = 'flex';
    opAvatar.textContent      = '?';
  }
}
opSel.onchange = checkOperator;

fetch('/api/it_employees')
  .then(r => r.json())
  .then(result => {
    opSel.innerHTML = '<option value="">— กรุณาเลือกผู้ดำเนินการ —</option>';
    (result.items || []).forEach(emp => {
      const o = document.createElement('option');
      o.value = emp.emp_id; o.textContent = emp.first_name;
      opSel.appendChild(o);
    });
    checkOperator();
  })
  .catch(() => { opSel.innerHTML = '<option value="">— โหลดข้อมูลไม่สำเร็จ —</option>'; checkOperator(); });

// ─────────────────────────────────────────────
//  Tabs
// ─────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(t => t.onclick = () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  document.querySelectorAll('.pane').forEach(p => p.classList.remove('show'));
  document.getElementById('pane-' + t.dataset.tab).classList.add('show');
});

// ─────────────────────────────────────────────
//  Utility
// ─────────────────────────────────────────────
function esc(s){ return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function toast(msg, type){
  const t = document.createElement('div');
  t.className = 'toast ' + (type === 'error' ? 'error' : 'ok');
  const ic = type === 'error'
    ? '<svg class="tic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>'
    : '<svg class="tic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>';
  t.innerHTML = ic + '<span>' + esc(msg) + '</span>';
  document.getElementById('toasts').appendChild(t);
  setTimeout(() => { t.style.transition='.3s'; t.style.opacity='0'; t.style.transform='translateX(40px)'; setTimeout(()=>t.remove(),300); }, 3500);
}

const SPIN_HTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;animation:spin 1s linear infinite"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>';

// ─────────────────────────────────────────────
//  Log
// ─────────────────────────────────────────────
function loadLog() {
  fetch('/api/cost-center/logs').then(r=>r.json()).then(res=>renderLog(res.ok ? res.items : [])).catch(()=>renderLog([]));
}

function parseNote(note) {
  const get = key => { const m = (note||'').match(new RegExp(key+':\\s*([^|]+)')); return m ? m[1].trim() : '-'; };
  return {
    cc:      get('Cost Center'),
    costdep: get('รหัสแผนก'),
    dept:    get('ชื่อแผนก'),
    company: get('บริษัท'),
    desc:    get('รายละเอียด') !== '-' ? get('รายละเอียด') : '',
    status:  get('สถานะ'),
    source:  get('source') !== '-' ? get('source') : 'single',
  };
}

function renderLog(items) {
  logBody.innerHTML = '';
  if (!items.length) {
    logBody.innerHTML = '<tr><td colspan="8" class="empty">ยังไม่มีประวัติ</td></tr>';
    return;
  }
  items.forEach((l, i) => {
    const ini = (l.action_by||'?').trim()[0].toUpperCase();
    const latest = i === 0 ? '<span class="latest-tag">ล่าสุด</span>' : '';
    const n = parseNote(l.action_note);
    const srcTag = n.source === 'bulk'
      ? '<span class="source-tag bulk">Excel</span>'
      : '<span class="source-tag single">Manual</span>';
    const statusPill = (n.status||'').toLowerCase() === 'active'
      ? `<span class="pill active">Active</span>`
      : `<span class="pill inactive">${esc(n.status)}</span>`;
    const tr = document.createElement('tr');
    if (i === 0) tr.classList.add('new-row');
    tr.innerHTML = `
      <td>${esc(l.created_at)}</td>
      <td><div class="who"><div class="av">${ini}</div><span>${esc(l.action_by)}${latest}${srcTag}</span></div></td>
      <td>${esc(n.company)}</td>
      <td class="mono">${esc(n.costdep)}</td>
      <td>${esc(n.dept)}</td>
      <td class="mono">${esc(n.cc)}</td>
      <td>${esc(n.desc)}</td>
      <td>${statusPill}</td>`;
    logBody.appendChild(tr);
  });
}

// ─────────────────────────────────────────────
//  Single entry
// ─────────────────────────────────────────────
function clearForm(){
  singleFields.forEach(id => {
    const e = document.getElementById(id);
    if (e.tagName === 'SELECT') e.selectedIndex = 0; else e.value = '';
    e.classList.remove('err');
  });
  hideDupConfirm();
}

function saveSingle() {
  const v = id => document.getElementById(id).value.trim();
  const payload = {
    company:    v('f_company'),
    costcenter: v('f_costcenter'),
    costdep:    v('f_costdep'),
    dept:       v('f_department'),
    desc:       v('f_desc'),
    status:     v('f_status'),
    code:       v('f_code'),
  };

  singleFields.slice(0,4).forEach(id => document.getElementById(id).classList.remove('err'));
  const miss = [];
  if (!payload.company)    miss.push('f_company');
  if (!payload.costdep)    miss.push('f_costdep');
  if (!payload.dept)       miss.push('f_department');
  if (!payload.costcenter) miss.push('f_costcenter');
  if (miss.length) { miss.forEach(id=>document.getElementById(id).classList.add('err')); toast('กรุณากรอกข้อมูลที่จำเป็น (*) ให้ครบ','error'); return; }

  hideDupConfirm();
  submitSingle(payload, false);
}

/** ยิงข้อมูลไป server — overwrite=true คือผู้ใช้ยืนยันแล้วว่าจะทับของเดิม */
function submitSingle(payload, overwrite) {
  const btn = document.getElementById('btn-save-single');
  const origHTML = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = SPIN_HTML + (overwrite ? ' กำลังอัปเดต...' : ' กำลังบันทึก...');

  fetch('/api/cost-center', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ ...payload, operator: opSel.value, source: 'single', overwrite })
  })
  .then(r=>r.json())
  .then(res => {
    btn.disabled = false; btn.innerHTML = origHTML;
    // ซ้ำ = ยังไม่ถือว่าผิด แค่ต้องให้ยืนยันก่อนทับ
    if (res.duplicate) { renderDupConfirm(payload, res.current || {}); return; }
    if (!res.ok) { toast(res.msg || 'เกิดข้อผิดพลาด', 'error'); return; }
    clearForm(); loadLog();
    toast(res.msg || `บันทึก Cost Center "${payload.costcenter}" เรียบร้อย`, 'ok');
  })
  .catch(() => { btn.disabled=false; btn.innerHTML=origHTML; toast('ไม่สามารถเชื่อมต่อ server ได้','error'); });
}

// ─────────────────────────────────────────────
//  Overwrite confirm (Cost Center ซ้ำ)
// ─────────────────────────────────────────────
//: [ป้ายไทย, คอลัมน์ที่ server ส่งกลับ, คีย์ในฟอร์ม]
const DUP_FIELDS = [
  ['บริษัท',     'cost_company',     'company'],
  ['รหัสแผนก',   'cost_costdep',     'costdep'],
  ['ชื่อแผนก',   'cost_department',  'dept'],
  ['รายละเอียด', 'cost_description', 'desc'],
  ['สถานะ',      'cost_status',      'status'],
  ['Code',       'code',             'code'],
];

function hideDupConfirm(){
  pendingSave = null;
  const box = document.getElementById('dup-confirm');
  if (box) { box.innerHTML = ''; box.classList.remove('show'); }
  const cc = document.getElementById('f_costcenter');
  if (cc) cc.classList.remove('warn');
}

function confirmOverwrite(){
  if (pendingSave) submitSingle(pendingSave, true);
}

function renderDupConfirm(payload, current){
  pendingSave = payload;
  document.getElementById('f_costcenter').classList.add('warn');

  const cell = val => esc(val) || '<span class="nil">— ว่าง —</span>';
  const rows = DUP_FIELDS.map(([label, dbKey, key]) => {
    const oldVal = (current[dbKey] || '').trim();
    // CODE ที่เว้นว่างจะคงค่าเดิม (SQL ใช้ NVL) ฟิลด์อื่นเว้นว่าง = ทับด้วยค่าว่างจริง
    const keepOld = key === 'code' && !payload[key] && !!oldVal;
    const newVal  = keepOld ? oldVal : payload[key];
    return `<tr class="${newVal !== oldVal ? 'changed' : ''}">
        <td class="lab">${esc(label)}</td>
        <td>${cell(oldVal)}</td>
        <td class="arw">→</td>
        <td>${cell(newVal)}${keepOld ? '<span class="keep">คงค่าเดิม</span>' : ''}</td>
      </tr>`;
  }).join('');

  const box = document.getElementById('dup-confirm');
  box.innerHTML = `
    <div class="dup-head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/></svg>
      <div>
        <b>Cost Center <span class="mono">${esc(payload.costcenter)}</span> มีอยู่ในระบบแล้ว</b>
        <p>ตรวจสอบค่าที่จะถูกเขียนทับด้านล่าง ถ้ากรอกรหัสผิดให้กดยกเลิกแล้วแก้ไขก่อน</p>
      </div>
    </div>
    <div class="tbl-wrap">
      <div class="tbl-scroll">
        <table class="dup-diff">
          <thead><tr><th>ฟิลด์</th><th>ข้อมูลเดิม</th><th></th><th>ข้อมูลใหม่</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
    <div class="dup-actions">
      <button class="btn btn-ghost" onclick="hideDupConfirm()">ยกเลิก</button>
      <button class="btn btn-warn" onclick="confirmOverwrite()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
        อัปเดตทับข้อมูลเดิม
      </button>
    </div>`;
  box.classList.add('show');
  box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ─────────────────────────────────────────────
//  Column mapping — รองรับหัวคอลัมน์ได้หลายแบบ
// ─────────────────────────────────────────────
//: ฟิลด์ในระบบ → ชื่อหัวคอลัมน์ที่ยอมรับ (เรียงตามลำดับที่อยากได้ก่อน)
//  ระวัง COST_DEPARTMENT: ไฟล์ส่งออกจริงใช้เป็น "รหัสแผนก" แต่ Template ชุดเก่าใช้เป็น
//  "ชื่อแผนก" — จึงจับ dept ก่อน ถ้าไฟล์มีคอลัมน์ DEPARTMENT แยกอยู่แล้ว
//  COST_DEPARTMENT จะเหลือให้ costdep เอง ทำให้อ่านได้ถูกทั้งสองแบบ
const COL_ALIASES = {
  company:    ['COST_COMPANY','COMPANY','บริษัท'],
  costcenter: ['COST_COSTCENTER','COSTCENTER','COST CENTER','COST_CENTER'],
  dept:       ['DEPARTMENT','COST_DEPARTMENT','DEPT_NAME','ชื่อแผนก'],
  costdep:    ['COST_COSTDEP','COSTDEP','COST_DEPARTMENT','DEPT_CODE','รหัสแผนก'],
  desc:       ['COST_DESCRIPTION','DESCRIPTION','DESC','รายละเอียด'],
  status:     ['COST_STATUS','STATUS','สถานะ'],
  code:       ['CODE'],
};
const MAP_ORDER       = ['company','costcenter','dept','costdep','desc','status','code'];
const REQUIRED_FIELDS = ['company','costcenter','dept','costdep'];
const FIELD_LABELS    = {
  company:'บริษัท', costcenter:'Cost Center', dept:'ชื่อแผนก',
  costdep:'รหัสแผนก', desc:'รายละเอียด', status:'สถานะ', code:'Code',
};

/** หัวคอลัมน์ในไฟล์ → ฟิลด์ในระบบ (ไม่สนตัวพิมพ์เล็กใหญ่และช่องว่างหัวท้าย) */
function mapColumns(headers){
  const seen = new Map();                     // 'COSTCENTER' → หัวคอลัมน์จริงในไฟล์
  (headers || []).forEach(h => {
    const k = String(h == null ? '' : h).trim().toUpperCase();
    if (k && !seen.has(k)) seen.set(k, h);
  });

  const taken = new Set(), map = {};
  MAP_ORDER.forEach(field => {
    const hit = COL_ALIASES[field].find(a => seen.has(a.toUpperCase()) && !taken.has(a.toUpperCase()));
    if (hit) { taken.add(hit.toUpperCase()); map[field] = seen.get(hit.toUpperCase()); }
    else     { map[field] = ''; }
  });
  return map;
}

/** ค่าในเซลล์ → ข้อความ — ตัด ' ที่ Excel ใช้บังคับ format ข้อความออกให้ด้วย */
function cellText(row, header){
  if (!header) return '';
  const raw = row[header];
  if (raw === undefined || raw === null) return '';
  if (typeof raw === 'number') return String(raw);   // เช็ค e+ ตอนอัปโหลดอีกที
  return String(raw).trim().replace(/^'+/, '').trim();
}

/** เก็บแถว + จับคู่คอลัมน์ แล้ววาด preview */
function setRows(rows, headers){
  parsedRows = rows;
  parsedCols = mapColumns(headers && headers.length ? headers : Object.keys(rows[0] || {}));
  renderPreview(rows);
}

// ─────────────────────────────────────────────
//  Drag & Drop
// ─────────────────────────────────────────────
function onDragOver(e){ e.preventDefault(); document.getElementById('drop-zone').classList.add('dragover'); }
function onDragLeave(){ document.getElementById('drop-zone').classList.remove('dragover'); }
function onDrop(e){
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) processFile(file);
}

// ─────────────────────────────────────────────
//  File parsing
// ─────────────────────────────────────────────
function pickFile(inp){
  if (inp.files[0]) processFile(inp.files[0]);
}

function processFile(file) {
  document.getElementById('fileName').textContent = '📄 ' + file.name;
  document.getElementById('btn-clear-file').style.display = '';
  document.getElementById('bulk-preview').innerHTML = '';
  document.getElementById('bulk-progress').classList.remove('show');
  parsedRows = [];
  parsedCols = {};

  const ext = file.name.split('.').pop().toLowerCase();

  if (ext === 'csv') {
    // CSV: อ่านเป็น text
    const reader = new FileReader();
    reader.onload = e => {
      const lines = e.target.result.trim().split('\n');
      const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g,''));
      const rows = lines.slice(1).map((line, i) => {
        const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g,''));
        const obj = {};
        headers.forEach((h,j) => obj[h] = vals[j] || '');
        obj.__excelRow = i + 2;   // เก็บเลขแถวจริงไว้ ก่อนกรองแถวว่างออก
        return obj;
      }).filter(r => Object.keys(r).some(k => k !== '__excelRow' && r[k]));
      setRows(rows, headers);
    };
    reader.readAsText(file, 'UTF-8');
  } else {
    // XLSX / XLS: ใช้ SheetJS
    const reader = new FileReader();
    reader.onload = e => {
      try {
        const wb = XLSX.read(e.target.result, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const raw  = XLSX.utils.sheet_to_json(ws, { defval: '' });
        const head = Object.keys(raw[0] || {});
        // Excel มักติดแถวเปล่าท้ายไฟล์มาด้วยเพราะจำการจัดรูปแบบของเซลล์ไว้
        // ต้องกรองทิ้งเหมือนฝั่ง CSV ไม่งั้นจะถูกรายงานว่า "ข้อมูลไม่ครบ"
        const data = raw
          .map((r, i) => Object.assign({}, r, { __excelRow: i + 2 }))
          .filter(r => head.some(h => String(r[h] ?? '').trim() !== ''));
        setRows(data, head);
      } catch(err) {
        toast('อ่านไฟล์ไม่สำเร็จ: ' + err.message, 'error');
      }
    };
    reader.readAsArrayBuffer(file);
  }
}

function renderPreview(rows) {
  const container = document.getElementById('bulk-preview');
  if (!rows.length) {
    container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--ink-faint);font-size:13px">ไม่พบข้อมูลในไฟล์</div>';
    return;
  }

  // ป้ายบอกว่าระบบอ่านคอลัมน์ไหนเป็นฟิลด์อะไร — ให้ผู้ใช้ทักท้วงได้ก่อนอัปโหลด
  const missing = REQUIRED_FIELDS.filter(f => !parsedCols[f]);
  const chips = MAP_ORDER.map(f => {
    const src = parsedCols[f];
    if (src)  return `<span class="map-chip ok">${esc(FIELD_LABELS[f])}<i>←</i>${esc(src)}</span>`;
    const req = REQUIRED_FIELDS.includes(f);
    return `<span class="map-chip ${req ? 'bad' : 'skip'}">${esc(FIELD_LABELS[f])}<i>←</i>${req ? 'ไม่พบคอลัมน์' : 'ไม่มีในไฟล์'}</span>`;
  }).join('');

  const cols = MAP_ORDER.filter(f => parsedCols[f]);
  const previewRows = rows.slice(0, 50); // แสดงสูงสุด 50 แถวใน preview

  container.innerHTML = `
    <div class="preview-wrap">
      <div class="preview-header">
        <span>ตัวอย่างข้อมูล ${previewRows.length < rows.length ? `(แสดง ${previewRows.length} จาก ${rows.length})` : `(${rows.length} แถว)`}</span>
        <span class="preview-badge">พร้อมอัปโหลด ${rows.length} รายการ</span>
      </div>
      <div class="col-map">
        <b>ระบบจับคู่คอลัมน์ในไฟล์ได้ดังนี้</b>
        <div class="map-chips">${chips}</div>
        ${missing.length ? `<div class="map-warn">ไม่พบคอลัมน์ที่จำเป็น: <b>${missing.map(f=>esc(FIELD_LABELS[f])).join(', ')}</b> — แก้ชื่อหัวคอลัมน์ในไฟล์ให้ตรง หรือดาวน์โหลด Template ใหม่ก่อนอัปโหลด</div>` : ''}
      </div>
      <div class="tbl-wrap">
        <div class="tbl-scroll">
          <table>
            <thead><tr>${cols.map(f=>`<th>${esc(FIELD_LABELS[f])}</th>`).join('')}</tr></thead>
            <tbody>
              ${previewRows.map(r=>`<tr>${cols.map(f=>`<td>${esc(cellText(r, parsedCols[f]))}</td>`).join('')}</tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>`;
}

function clearFile(){
  parsedRows = [];
  parsedCols = {};
  document.getElementById('fileName').textContent = '';
  document.getElementById('bulk-preview').innerHTML = '';
  document.getElementById('bulk-progress').classList.remove('show');
  document.getElementById('btn-clear-file').style.display = 'none';
  document.getElementById('xlfile').value = '';
}

// ─────────────────────────────────────────────
//  Upload (loop POST ทีละแถว)
// ─────────────────────────────────────────────
async function uploadFile() {
  if (!parsedRows.length) { toast('กรุณาเลือกไฟล์และตรวจสอบ Preview ก่อน','error'); return; }
  if (!opSel.value)       { toast('กรุณาเลือกผู้ดำเนินการก่อน','error'); return; }

  // จับคู่คอลัมน์ไม่ครบ = ทุกแถวจะกลายเป็น "ข้อมูลไม่ครบ" — บอกสาเหตุจริงดีกว่าปล่อยให้วิ่งจนจบ
  const noCol = REQUIRED_FIELDS.filter(f => !parsedCols[f]);
  if (noCol.length) {
    toast(`ไฟล์นี้ไม่มีคอลัมน์: ${noCol.map(f=>FIELD_LABELS[f]).join(', ')} — ตรวจชื่อหัวคอลัมน์ในไฟล์ก่อน`, 'error');
    return;
  }

  const btn = document.getElementById('btn-upload');
  btn.disabled = true;
  btn.innerHTML = SPIN_HTML + ' กำลังอัปโหลด...';

  // reset error detail
  const errDetail  = document.getElementById('error-detail');
  const errTbody   = document.getElementById('error-tbody');
  errDetail.style.display = 'none';
  errTbody.innerHTML = '';

  // แสดง progress
  const progWrap  = document.getElementById('bulk-progress');
  const progBar   = document.getElementById('prog-bar');
  const progLabel = document.getElementById('prog-label');
  const progPct   = document.getElementById('prog-pct');
  const progRes   = document.getElementById('prog-result');
  progWrap.classList.add('show');
  progRes.innerHTML = '';

  let okCount = 0, updCount = 0, errCount = 0, skipCount = 0, blankCount = 0;
  const total    = parsedRows.length;
  const errRows  = []; // เก็บรายการที่มีปัญหา

  for (let i = 0; i < total; i++) {
    const row = parsedRows[i];
    const rowNo = row.__excelRow || (i + 2); // เลขแถวจริงในไฟล์ (row 1 = header)
    const pct = Math.round(((i + 1) / total) * 100);
    progBar.style.width = pct + '%';
    progPct.textContent = pct + '%';
    progLabel.textContent = `กำลังบันทึก... (${i+1}/${total})`;

    const company    = cellText(row, parsedCols.company);
    const dept       = cellText(row, parsedCols.dept);      // ชื่อแผนก
    const costdep    = cellText(row, parsedCols.costdep);   // รหัสแผนก
    const desc       = cellText(row, parsedCols.desc);
    const costcenter = cellText(row, parsedCols.costcenter);
    const rawStatus  = cellText(row, parsedCols.status);
    const status     = rawStatus || 'Active';

    // ── แถวว่างทั้งแถว: ข้ามเงียบ ๆ ──
    // Excel มักติดแถวเปล่าท้ายไฟล์มาด้วย เพราะจำการจัดรูปแบบของเซลล์ไว้
    // (เคยพิมพ์แล้วลบ หรือลากเส้นตาราง) แถวพวกนี้ไม่ใช่ข้อมูลที่กรอกผิด
    // จึงไม่ควรนับเป็น "ข้อมูลไม่ครบ" ไปกลบแถวที่ผิดพลาดจริง
    if (!company && !dept && !costdep && !costcenter && !desc && !rawStatus) {
      blankCount++;
      continue;
    }

    // ── ตรวจ required fields ──
    const missing = [];
    if (!company)    missing.push(FIELD_LABELS.company);
    if (!dept)       missing.push(FIELD_LABELS.dept);
    if (!costdep)    missing.push(FIELD_LABELS.costdep);
    if (!costcenter) missing.push(FIELD_LABELS.costcenter);

    if (missing.length) {
      skipCount++;
      errRows.push({
        rowNo, company, costcenter, dept,
        type:   'missing',
        typeLabel: 'ข้อมูลไม่ครบ',
        detail: `ฟิลด์ที่ขาด: ${missing.join(', ')}`,
      });
      continue;
    }

    // ── Excel แปลงรหัสแบบ 1E00000100 เป็นตัวเลขวิทยาศาสตร์ไปแล้ว ──
    const sci = [[FIELD_LABELS.costcenter, costcenter], [FIELD_LABELS.costdep, costdep]]
      .filter(([, v]) => /e\+/i.test(v));
    if (sci.length) {
      skipCount++;
      errRows.push({
        rowNo, company, costcenter, dept,
        type:   'missing',
        typeLabel: 'Excel แปลงค่า',
        detail: `${sci.map(([l,v])=>`${l} อ่านได้เป็น "${v}"`).join(', ')} — ` +
                "จัดรูปแบบคอลัมน์เป็น Text (หรือพิมพ์ ' นำหน้า) แล้วบันทึกไฟล์ใหม่",
      });
      continue;
    }

    // ── ตรวจ COST_STATUS ──
    const validStatus = ['active','block'];
    if (status && !validStatus.includes(status.toLowerCase())) {
      errRows.push({
        rowNo, company, costcenter, dept,
        type:   'missing',
        typeLabel: 'ค่าไม่ถูกต้อง',
        detail: `COST_STATUS "${status}" ไม่ถูกต้อง — ต้องเป็น Active หรือ Block`,
      });
      // ยังคง POST ไป server เพื่อให้ Oracle ตัดสิน (หรือ continue ก็ได้)
    }

    try {
      const res = await fetch('/api/cost-center', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          company, costdep, dept, costcenter, desc, status,
          code: '', operator: opSel.value, source: 'bulk',
        }),
      }).then(r => r.json());

      if (res.ok) {
        if (res.updated) updCount++; else okCount++;
      } else {
        errCount++;
        // ดึง error message จาก Oracle/server มาแสดงตรงๆ
        errRows.push({
          rowNo, company, costcenter, dept,
          type:   'db',
          typeLabel: 'DB Error',
          detail: res.msg || 'เกิดข้อผิดพลาดจาก server',
        });
      }
    } catch (ex) {
      errCount++;
      errRows.push({
        rowNo, company, costcenter, dept,
        type:   'db',
        typeLabel: 'Network Error',
        detail: ex.message || 'ไม่สามารถเชื่อมต่อ server ได้',
      });
    }
  }

  // ── สรุปผล ──
  progLabel.textContent = 'เสร็จสิ้น';
  progRes.innerHTML = `
    <span class="ok-count">✔ เพิ่มใหม่ ${okCount} รายการ</span>
    ${updCount  ? `<span class="skip-count">⟳ อัปเดต ${updCount} รายการ</span>` : ''}
    ${skipCount ? `<span class="skip-count">⚠ ข้อมูลไม่ครบ ${skipCount} รายการ</span>` : ''}
    ${errCount  ? `<span class="err-count">✖ DB Error ${errCount} รายการ</span>` : ''}
    ${blankCount ? `<span class="blank-count">แถวว่างที่ข้ามไป ${blankCount} แถว</span>` : ''}`;

  // ── แสดงตาราง error detail ถ้ามี ──
  if (errRows.length) {
    errTbody.innerHTML = errRows.map(e => `
      <tr>
        <td style="text-align:center;font-weight:600;color:var(--ink-faint)">${e.rowNo}</td>
        <td>${esc(e.company)}</td>
        <td class="mono">${esc(e.costcenter)}</td>
        <td>${esc(e.dept)}</td>
        <td><span class="err-tag ${e.type}">${esc(e.typeLabel)}</span></td>
        <td><div class="err-detail">${esc(e.detail)}</div></td>
      </tr>`).join('');
    errDetail.style.display = 'block';
  }

  btn.disabled = false;
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5M12 3v12"/></svg> อัปโหลดเข้าระบบ`;

  loadLog();
  const totalBad = skipCount + errCount;
  const msg = `เพิ่มใหม่ ${okCount}` +
    (updCount  ? ` | อัปเดต ${updCount}` : '') +
    (skipCount ? ` | ข้อมูลไม่ครบ ${skipCount}` : '') +
    (errCount  ? ` | DB Error ${errCount}` : '') + ' รายการ';
  toast(msg, totalBad > 0 && (okCount + updCount) === 0 ? 'error' : (totalBad > 0 ? 'error' : 'ok'));
}

// ─────────────────────────────────────────────
//  Download Template (สร้างด้วย SheetJS)
// ─────────────────────────────────────────────
function downloadTemplate() {
  const wb  = XLSX.utils.book_new();
  //: ใช้ชื่อหัวคอลัมน์ชุดเดียวกับไฟล์ส่งออกจริง (COST_DEPARTMENT = รหัส, DEPARTMENT = ชื่อ)
  const hdr = ['COMPANY','COST_DEPARTMENT','DEPARTMENT','COSTCENTER','COST_DESCRIPTION','COST_STATUS'];
  const ex  = [
    ['SBI',  '1E00000000', '1E  Purchasing',              '1E00000100', 'OEM',     'Active'],
    ['SBDS', '9G01000000', '9G Sales & Operation (SBDS)', '9G01000001', 'SUPPORT', 'Block'],
  ];
  const ws = XLSX.utils.aoa_to_sheet([hdr, ...ex]);

  // บังคับคอลัมน์รหัสให้เป็น Text ล่วงหน้า — ไม่งั้น Excel อ่าน 1E00000100
  // เป็นตัวเลขวิทยาศาสตร์ ทำให้ต้องพิมพ์ ' นำหน้าเองทุกครั้ง
  const TEXT_COLS = [1, 3];   // COST_DEPARTMENT, COSTCENTER
  const LAST_ROW  = 200;      // เผื่อแถวว่างไว้ให้กรอกต่อ
  TEXT_COLS.forEach(c => {
    for (let r = 1; r <= LAST_ROW; r++) {
      const ref  = XLSX.utils.encode_cell({ r, c });
      const cell = ws[ref] || (ws[ref] = { v: '' });
      cell.t = 's';
      cell.z = '@';
    }
  });
  ws['!ref']  = XLSX.utils.encode_range({ s:{r:0,c:0}, e:{r:LAST_ROW, c:hdr.length - 1} });
  ws['!cols'] = [12,18,35,18,28,14].map(w => ({wch: w}));

  XLSX.utils.book_append_sheet(wb, ws, 'Cost Center Template');
  XLSX.writeFile(wb, 'CostCenter_Template.xlsx');
  toast('ดาวน์โหลด Template เรียบร้อย', 'ok');
}

// ─────────────────────────────────────────────
//  Init
// ─────────────────────────────────────────────
loadLog();
