  /* ── นาฬิกา ── */
  const TH_MONTHS = ['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'];
  function tick(){
    const n = new Date(); const p = x => String(x).padStart(2,'0');
    document.getElementById('clock').textContent = `${p(n.getHours())}:${p(n.getMinutes())}:${p(n.getSeconds())}`;
    document.getElementById('dateTxt').textContent = `${n.getDate()} ${TH_MONTHS[n.getMonth()]} ${n.getFullYear()+543}`;
  }
  tick(); setInterval(tick,1000);

  /* ── เปิดแผงรายละเอียด ── */
  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

  function openDetail(tr){
    closeMenu();
    const d = tr.dataset;
    // เติมส่วนหัว/ซ้ายทันทีจาก data-* (เร็ว)
    document.getElementById('dDocNo').textContent = 'เอกสารเลขที่ ' + d.id;
    const st = document.getElementById('dStatus'); st.textContent = d.status; st.className = 'pill ' + d.statuscls;
    const tp = document.getElementById('dType'); tp.textContent = d.type; tp.className = 'type ' + d.typecls;
    document.getElementById('dDate').textContent  = d.date  || '—';
    document.getElementById('dReq').textContent   = d.req   || '—';
    document.getElementById('dDept').textContent  = d.dept  || '—';
    document.getElementById('dTitle').textContent = d.title || '—';
    document.getElementById('dRemark').textContent= d.remark|| '—';
    // ส่วนขวา: ขึ้น loading ก่อน
    document.getElementById('dAsset').innerHTML = '<tr><td colspan="2" style="text-align:center;color:var(--ink-faint)">กำลังโหลด…</td></tr>';
    document.getElementById('dOwner').innerHTML = '<div class="pn"><b style="color:var(--ink-faint);font-weight:500">กำลังโหลด…</b></div>';
    document.getElementById('dTimeline').innerHTML = '<div class="tl-item wait"><span class="dot"></span><div class="tt" style="color:var(--ink-faint);font-weight:500">กำลังโหลด…</div></div>';
    document.getElementById('detail').classList.add('show');
    document.getElementById('overlay').classList.add('show');
    loadDetail(d.id);
  }

  /* ── ดึงรายละเอียดเต็มจาก endpoint ── */
  async function loadDetail(reqId){
    try{
      const res = await fetch('/api/docs_detail/' + encodeURIComponent(reqId));
      const j = await res.json();
      if(!j.ok){ throw new Error(j.msg || 'error'); }
      const doc = j.doc || {};

      // เติมข้อมูลละเอียดเพิ่ม (วันที่เต็ม + ผู้ขอ + รายละเอียด)
      if(doc.date)   document.getElementById('dDate').textContent   = doc.date;
      if(doc.remark) document.getElementById('dRemark').textContent = doc.remark;
      let reqLine = doc.requester || '—';
      if(doc.empcode) reqLine += ' (' + doc.empcode + ')';
      document.getElementById('dReq').textContent = reqLine;

      // ทรัพย์สิน
      const assets = j.assets || [];
      document.getElementById('dAsset').innerHTML = assets.length
        ? assets.map(a=>`<tr><td>${esc(a.code)}</td><td>${esc(a.name)}</td></tr>`).join('')
        : '<tr><td colspan="2" style="text-align:center;color:var(--ink-faint)">ไม่มีรายการทรัพย์สิน</td></tr>';

      // ผู้รับผิดชอบ
      document.getElementById('dOwner').innerHTML = doc.owner
        ? `<div class="av">${esc(doc.owner_initial||doc.owner.slice(0,2))}</div><div class="pn"><b>${esc(doc.owner)}</b><span>เจ้าหน้าที่ไอที</span></div>`
        : '<div class="pn"><b style="color:var(--ink-faint);font-weight:500">ยังไม่มีผู้รับผิดชอบ</b></div>';

      // timeline
      const wf = j.workflow || [];
      document.getElementById('dTimeline').innerHTML = wf.length
        ? wf.map(w=>`
            <div class="tl-item ${w.cls}">
              <span class="dot"></span>
              <div class="tt">${esc(w.label)} · ${esc(w.status_label)}</div>
              <div class="tn">${esc(w.name)}</div>
              ${w.date ? `<div class="tm">${esc(w.date)}</div>` : ''}
            </div>`).join('')
        : '<div class="tl-item wait"><span class="dot"></span><div class="tt" style="color:var(--ink-faint);font-weight:500">ยังไม่มีประวัติการดำเนินการ</div></div>';
    }catch(err){
      document.getElementById('dAsset').innerHTML = '<tr><td colspan="2" style="text-align:center;color:var(--red-tx)">โหลดข้อมูลไม่สำเร็จ</td></tr>';
      document.getElementById('dOwner').innerHTML = '<div class="pn"><b style="color:var(--red-tx);font-weight:500">โหลดข้อมูลไม่สำเร็จ</b></div>';
      document.getElementById('dTimeline').innerHTML = '<div class="tl-item reject"><span class="dot"></span><div class="tt" style="color:var(--red-tx)">โหลดข้อมูลไม่สำเร็จ</div></div>';
    }
  }
  function closeDetail(){
    document.getElementById('detail').classList.remove('show');
    document.getElementById('overlay').classList.remove('show');
  }

  /* ── เมนูจัดการ (3 จุด) ── */
  let openMenuEl = null;
  function closeMenu(){ if(openMenuEl){ openMenuEl.remove(); openMenuEl = null; } }
  function toggleMenu(btn){
    const wrap = btn.parentElement;
    if(openMenuEl && openMenuEl.parentElement === wrap){ closeMenu(); return; }
    closeMenu();
    const node = document.getElementById('menuTpl').content.firstElementChild.cloneNode(true);
    wrap.appendChild(node); openMenuEl = node;
    const tr = btn.closest('tr');
    node.querySelectorAll('.mi').forEach(mi=>{
      mi.addEventListener('click', e=>{
        e.stopPropagation();
        if(mi.dataset.act === 'detail') openDetail(tr); else closeMenu();
      });
    });
  }
  document.addEventListener('click', e=>{ if(openMenuEl && !e.target.closest('.menu-wrap')) closeMenu(); });
  document.addEventListener('keydown', e=>{ if(e.key==='Escape'){ closeMenu(); closeDetail(); } });

  /* ── เลือกทั้งหมด ── */
  document.getElementById('chkAll').addEventListener('change', e=>{
    document.querySelectorAll('.row-chk').forEach(c=>{
      c.checked = e.target.checked;
      c.closest('tr').classList.toggle('selected', e.target.checked);
    });
  });

  /* ── ค้นหา / กรอง (client-side) ── */
  let navGroup = '';
  let navDoc = '';
  function setNav(el, group, doc){
    navGroup = group || '';
    navDoc = doc || '';
    document.querySelectorAll('.sidebar .nav-item').forEach(a=>a.classList.remove('active'));
    el.classList.add('active');
    filterRows();
  }

  /* แปลง data-date ("04/05/2026 07:33") เป็น Date object */
function parseRowDate(s){
  if(!s) return null;
  s = s.trim().split(' ')[0];                    // เอาเฉพาะส่วนวันที่
  let d, m, y;
  if(s.includes('/'))      [d, m, y] = s.split('/').map(Number);   // DD/MM/YYYY
  else if(s.includes('-')) [y, m, d] = s.split('-').map(Number);   // YYYY-MM-DD
  else return null;
  if(!y || !m || !d) return null;
  if(y > 2500) y -= 543;                          // เผื่อเก็บเป็น พ.ศ.
  return new Date(y, m-1, d);
}

function filterRows(){
  const q   = document.getElementById('searchBox').value.toLowerCase().trim();
  const ty  = document.getElementById('fType').value;
  const stt = document.getElementById('fStatus').value;
  const dr  = parseInt(document.getElementById('fDate').value, 10) || 0;  // ← เพิ่ม

  const today = new Date(); today.setHours(0,0,0,0);

  document.querySelectorAll('#tbody tr').forEach(tr=>{
    if(!tr.dataset.id) return;
    const text = (tr.dataset.id+' '+tr.dataset.req+' '+tr.dataset.title).toLowerCase();
    const okQ = !q   || text.includes(q);
    const okT = !ty  || tr.dataset.type === ty;
    const okS = !stt || tr.dataset.status === stt;
    const okG = !navGroup || tr.dataset.group === navGroup;
    const okD = !navDoc   || tr.dataset.doc === navDoc;

    let okDate = true;                                                    // ← เพิ่มบล็อกนี้
    if(dr){
      const rd = parseRowDate(tr.dataset.date);
      if(!rd) okDate = false;
      else {
        const diff = Math.floor((today - rd) / 86400000);   // จำนวนวันห่างจากวันนี้
        okDate = diff >= 0 && diff < dr;                     // อยู่ในช่วง N วันล่าสุด
      }
    }

    tr.style.display = (okQ && okT && okS && okG && okD && okDate) ? '' : 'none';
  });
}

  function clearFilter(){
    document.getElementById('searchBox').value = '';
    document.getElementById('fType').value = '';
    document.getElementById('fStatus').value = '';
    document.getElementById('fDate').value = '';
    filterRows();
  }
