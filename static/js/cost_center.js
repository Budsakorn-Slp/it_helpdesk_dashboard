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
}

function saveSingle() {
  const v = id => document.getElementById(id).value.trim();
  const company=v('f_company'), costcenter=v('f_costcenter'), costdep=v('f_costdep'),
        dept=v('f_department'), desc=v('f_desc'), status=v('f_status'), code=v('f_code');

  singleFields.slice(0,4).forEach(id => document.getElementById(id).classList.remove('err'));
  const miss = [];
  if (!company)    miss.push('f_company');
  if (!costdep)    miss.push('f_costdep');
  if (!dept)       miss.push('f_department');
  if (!costcenter) miss.push('f_costcenter');
  if (miss.length) { miss.forEach(id=>document.getElementById(id).classList.add('err')); toast('กรุณากรอกข้อมูลที่จำเป็น (*) ให้ครบ','error'); return; }

  const btn = document.getElementById('btn-save-single');
  const origHTML = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = SPIN_HTML + ' กำลังบันทึก...';

  fetch('/api/cost-center', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ company, costcenter, costdep, dept, desc, status, code, operator: opSel.value, source: 'single' })
  })
  .then(r=>r.json())
  .then(res => {
    btn.disabled = false; btn.innerHTML = origHTML;
    if (!res.ok) {
      if (res.msg?.includes('ซ้ำ')) document.getElementById('f_costcenter').classList.add('err');
      toast(res.msg || 'เกิดข้อผิดพลาด', 'error'); return;
    }
    clearForm(); loadLog();
    toast(`บันทึก Cost Center "${costcenter}" เรียบร้อย`, 'ok');
  })
  .catch(() => { btn.disabled=false; btn.innerHTML=origHTML; toast('ไม่สามารถเชื่อมต่อ server ได้','error'); });
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

  const ext = file.name.split('.').pop().toLowerCase();

  if (ext === 'csv') {
    // CSV: อ่านเป็น text
    const reader = new FileReader();
    reader.onload = e => {
      const lines = e.target.result.trim().split('\n');
      const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g,''));
      const rows = lines.slice(1).map(line => {
        const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g,''));
        const obj = {};
        headers.forEach((h,i) => obj[h] = vals[i] || '');
        return obj;
      }).filter(r => Object.values(r).some(v => v));
      parsedRows = rows;
      renderPreview(rows);
    };
    reader.readAsText(file, 'UTF-8');
  } else {
    // XLSX / XLS: ใช้ SheetJS
    const reader = new FileReader();
    reader.onload = e => {
      try {
        const wb = XLSX.read(e.target.result, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const data = XLSX.utils.sheet_to_json(ws, { defval: '' });
        parsedRows = data;
        renderPreview(data);
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
  const COLS = ['COST_COMPANY','COST_DEPARTMENT','COST_COSTDEP','COST_DESCRIPTION','COST_COSTCENTER','COST_STATUS'];
  const previewRows = rows.slice(0, 50); // แสดงสูงสุด 50 แถวใน preview

  container.innerHTML = `
    <div class="preview-wrap">
      <div class="preview-header">
        <span>ตัวอย่างข้อมูล ${previewRows.length < rows.length ? `(แสดง ${previewRows.length} จาก ${rows.length})` : `(${rows.length} แถว)`}</span>
        <span class="preview-badge">พร้อมอัปโหลด ${rows.length} รายการ</span>
      </div>
      <div class="tbl-wrap">
        <div class="tbl-scroll">
          <table>
            <thead><tr>${COLS.map(c=>`<th>${c}</th>`).join('')}</tr></thead>
            <tbody>
              ${previewRows.map(r=>`<tr>${COLS.map(c=>`<td>${esc(String(r[c]||''))}</td>`).join('')}</tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>`;
}

function clearFile(){
  parsedRows = [];
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

  let okCount = 0, updCount = 0, errCount = 0, skipCount = 0;
  const total    = parsedRows.length;
  const errRows  = []; // เก็บรายการที่มีปัญหา

  for (let i = 0; i < total; i++) {
    const row = parsedRows[i];
    const rowNo = i + 2; // บวก 2 เพราะ Excel row 1 = header, data เริ่มที่ row 2
    const pct = Math.round(((i + 1) / total) * 100);
    progBar.style.width = pct + '%';
    progPct.textContent = pct + '%';
    progLabel.textContent = `กำลังบันทึก... (${i+1}/${total})`;

    const company    = String(row['COST_COMPANY']     || '').trim();
    const dept       = String(row['COST_DEPARTMENT']  || '').trim();  // ชื่อแผนก
    const costdep    = String(row['COST_COSTDEP']     || '').trim();  // รหัสแผนก
    const desc       = String(row['COST_DESCRIPTION'] || '').trim();
    const costcenter = String(row['COST_COSTCENTER']  || '').trim();
    const status     = String(row['COST_STATUS']      || 'Active').trim();

    // ── ตรวจ required fields ──
    const missing = [];
    if (!company)    missing.push('COST_COMPANY');
    if (!dept)       missing.push('COST_DEPARTMENT');
    if (!costdep)    missing.push('COST_COSTDEP');
    if (!costcenter) missing.push('COST_COSTCENTER');

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
    ${errCount  ? `<span class="err-count">✖ DB Error ${errCount} รายการ</span>` : ''}`;

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
  const hdr = ['COST_COMPANY','COST_DEPARTMENT','COST_COSTDEP','COST_DESCRIPTION','COST_COSTCENTER','COST_STATUS'];
  const ex  = [
    ['SBI',  'ตัวอย่างแผนก A', '9G01000000', 'SUPPORT',      '9G01000001', 'Active'],
    ['SBDS', 'ตัวอย่างแผนก B', '9G00000000', '9G1-SBDS CDC', '9G00000001', 'Block'],
  ];
  const ws = XLSX.utils.aoa_to_sheet([hdr, ...ex]);

  // กำหนดความกว้างคอลัมน์
  ws['!cols'] = [12,35,18,28,18,14].map(w => ({wch: w}));

  XLSX.utils.book_append_sheet(wb, ws, 'Cost Center Template');
  XLSX.writeFile(wb, 'CostCenter_Template.xlsx');
  toast('ดาวน์โหลด Template เรียบร้อย', 'ok');
}

// ─────────────────────────────────────────────
//  Init
// ─────────────────────────────────────────────
loadLog();
