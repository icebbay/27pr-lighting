// 27PR 给排水 page: water supply + drainage drawn on the same wall plan as the lighting / power pages.
// Data: plumbing_data.js (build_plumbing.py, from trade_drawings/plumbing.py); walls: lighting_data.js (walls_<F>.svg).
(function () {
  const D = window.PLUMBING, L = window.LIGHTING_DEFAULT;
  const FCN = { GF: '一层 ', FF: '二层 ' };
  const PDF = [['27PR_给排水施工图_RevC.pdf', '给排水施工图 P-00…P-08（Rev C）'], ['27PR_照明布线施工图_RevC.pdf', '照明布线施工图 E-01…E-03'],
               ['27PR_插座动力施工图_RevC.pdf', '插座动力施工图 E-11…E-13']];
  const pdfUrl = f => '../trade_drawings/out/' + encodeURIComponent(f);
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const $ = s => document.querySelector(s);
  const ui = { view: 'both', sys: { supply: true, drain: true }, nums: true, sel: null };
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

  function parseHash() {      // #GF / #FF-drain / #both-supply
    const [v, s] = (location.hash || '').replace('#', '').split('-');
    if (['GF', 'FF', 'both'].includes(v)) ui.view = v;
    if (s === 'supply' || s === 'drain') { ui.sys.supply = s === 'supply'; ui.sys.drain = s === 'drain'; }
  }

  class Pane {
    constructor(F, host) {
      const fd = D.floors[F]; this.F = F; this.m = fd.emu_per_m; this.vb0 = fd.view_box; this.vb = [...fd.view_box];
      this.el = document.createElement('div'); this.el.className = 'pane'; host.appendChild(this.el);
      this.el.innerHTML = `<div class="ttl">${FCN[F]}给排水</div><div class="zb"><button data-z="in">＋</button><button data-z="out">－</button><button data-z="fit" style="width:44px;font-size:12px">复位</button></div>`;
      this.el.querySelector('.zb').addEventListener('click', e => { const z = e.target.dataset.z; if (!z) return;
        if (z === 'fit') { this.vb = [...this.vb0]; return this.setVB(); }
        const k = z === 'in' ? 1 / 1.4 : 1.4, c = [this.vb[0] + this.vb[2] / 2, this.vb[1] + this.vb[3] / 2];
        this.vb = [c[0] - this.vb[2] * k / 2, c[1] - this.vb[3] * k / 2, this.vb[2] * k, this.vb[3] * k]; this.setVB(); });
      this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); this.el.appendChild(this.svg);
      const inner = L[F].svg.replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '');
      this.svg.innerHTML = `<rect x="-1e9" y="-1e9" width="2e9" height="2e9" fill="#fff"/><g opacity=".75">${inner}</g><g class="ov"></g>`;
      this.ov = this.svg.querySelector('.ov'); this.setVB(); this.events();
    }
    setVB() { this.svg.setAttribute('viewBox', this.vb.join(' ')); }
    pt(ev) { const p = this.svg.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY; const q = p.matrixTransform(this.svg.getScreenCTM().inverse()); return [q.x, q.y]; }
    events() {
      const svg = this.svg, touches = new Map(); let drag = null, moved = false;
      svg.addEventListener('wheel', ev => { ev.preventDefault(); const p = this.pt(ev), k = ev.deltaY > 0 ? 1.15 : 1 / 1.15;
        this.vb = [p[0] - (p[0] - this.vb[0]) * k, p[1] - (p[1] - this.vb[1]) * k, this.vb[2] * k, this.vb[3] * k]; this.setVB(); }, { passive: false });
      svg.addEventListener('pointerdown', ev => {
        if (ev.pointerType === 'touch') touches.set(ev.pointerId, [ev.clientX, ev.clientY]);
        if (touches.size > 1) { drag = null; return; }
        drag = { x: ev.clientX, y: ev.clientY, vb: [...this.vb], s: this.vb[2] / svg.clientWidth, hit: ev.target.closest('[data-k]') }; moved = false; svg.setPointerCapture(ev.pointerId);
      });
      svg.addEventListener('pointermove', ev => {
        if (touches.has(ev.pointerId)) {
          const prev = [...touches.values()]; touches.set(ev.pointerId, [ev.clientX, ev.clientY]);
          if (touches.size === 2) { const now = [...touches.values()], d0 = dist(prev[0], prev[1]), d1 = dist(now[0], now[1]); if (!d0 || !d1) return;
            const mid = this.pt({ clientX: (now[0][0] + now[1][0]) / 2, clientY: (now[0][1] + now[1][1]) / 2 }), k = d0 / d1;
            this.vb = [mid[0] - (mid[0] - this.vb[0]) * k, mid[1] - (mid[1] - this.vb[1]) * k, this.vb[2] * k, this.vb[3] * k]; this.setVB(); return; }
        }
        if (!drag) return; const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
        this.vb = [drag.vb[0] - dx * drag.s, drag.vb[1] - dy * drag.s, drag.vb[2], drag.vb[3]]; this.setVB();
      });
      const up = ev => { touches.delete(ev.pointerId); if (drag && !moved) select(drag.hit ? drag.hit.dataset.k : null); drag = null; };
      svg.addEventListener('pointerup', up); svg.addEventListener('pointercancel', ev => { touches.delete(ev.pointerId); drag = null; });
    }
    draw() {
      const F = this.F, fd = D.floors[F], m = this.m, o = [], mm = 0.11 * m;      // line widths: PDF page-mm × 0.11 m (readable on screen)
      const dim = k => ui.sel && ui.sel !== k ? 'dim' : '';
      const txt = (x, y, t, fs, extra = '') => `<text transform="translate(${x} ${y}) scale(1000)" font-size="${fs / 1000}" ${extra}>${esc(t)}</text>`;   // EMU-sized fonts do not render: scale like power.js
      for (const mk of fd.marks) {
        const st = { box: 'fill="#eee" stroke="#6b3e1e"', pond: 'fill="#bfe0f2" stroke="#3b7fa8"', channel: 'fill="#fff" stroke="#2e7d32"',
                     wall: 'fill="#f3e3c3" stroke="#a07a3a"', niche: 'fill="#fff" stroke="#a07a3a" stroke-dasharray="' + 0.03 * m + ' ' + 0.02 * m + '"' }[mk.kind];
        o.push(`<path d="M${mk.pts.map(p => p.join(' ')).join('L')}Z" ${st} stroke-width="${0.012 * m}"><title>${esc(mk.name)}</title></path>`);
      }
      fd.pipes.forEach((p, i) => {
        if (!ui.sys[p.sys]) return;
        const s = D.style[p.kind], k = `${F}:p${i}`, d = `M${p.pts.map(q => q.join(' ')).join('L')}`, on = ui.sel === k;
        const dash = s.dash ? `stroke-dasharray="${s.dash.split(' ').map(v => v * mm).join(' ')}"` : '';
        if (on) o.push(`<path d="${d}" fill="none" stroke="#ffd54f" stroke-width="${(s.w + 1.6) * mm}" stroke-linejoin="round" stroke-linecap="round"/>`);
        o.push(`<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.w * mm}" ${dash} stroke-linejoin="round" class="${dim(k)}"/>`,
               `<path d="${d}" fill="none" stroke="transparent" stroke-width="${0.3 * m}" data-k="${k}"><title>${esc(s.short + ' Ø' + p.size + ' · ' + (p.label || ''))}</title></path>`);
      });
      if (ui.nums) fd.pipes.forEach((p, i) => {
        if (!ui.sys[p.sys] || !p.no) return;
        const s = D.style[p.kind], k = `${F}:p${i}`; let best = null, bl = -1;
        for (let j = 1; j < p.pts.length; j++) { const l = dist(p.pts[j - 1], p.pts[j]); if (l > bl) { bl = l; best = [p.pts[j - 1], p.pts[j]]; } }
        const c = [(best[0][0] + best[1][0]) / 2, (best[0][1] + best[1][1]) / 2], r = 0.19 * m;
        o.push(`<g data-k="${k}" class="${dim(k)}"><circle cx="${c[0]}" cy="${c[1]}" r="${r}" fill="#fff" stroke="${s.color}" stroke-width="${0.02 * m}"/>` +
               txt(c[0], c[1] + 0.08 * m, p.no, 0.22 * m, `text-anchor="middle" fill="${s.color}" font-weight="bold"`) + '</g>');
      });
      for (const e of fd.equip) if (ui.sys.supply) {
        const k = `${F}:e:${e.id}`, w = e.d * m, h = e.w * m;
        o.push(`<g data-k="${k}" class="${dim(k)}"><rect x="${e.p[0] - w / 2}" y="${e.p[1] - h / 2}" width="${w}" height="${h}" fill="#fff6d8" stroke="#7a5b00" stroke-width="${0.015 * m}"/>` +
               txt(e.p[0], e.p[1] + 0.07 * m, e.id, 0.17 * m, 'text-anchor="middle" font-weight="bold"') + '</g>');
      }
      for (const f of fd.fixtures) {
        const k = `${F}:f:${f.code}`, a = 0.12 * m;
        o.push(`<g data-k="${k}" class="${dim(k)}"><rect x="${f.p[0] - a}" y="${f.p[1] - a}" width="${2 * a}" height="${2 * a}" fill="#fff" stroke="#333" stroke-width="${0.015 * m}"/>` +
               txt(f.p[0], f.p[1] + 0.40 * m, f.code, 0.22 * m, 'text-anchor="middle" font-weight="bold" fill="#222"') + '</g>');
      }
      if (ui.sys.drain) {
        for (const s of fd.stacks) { const k = `${F}:s:${s.id}`;
          o.push(`<g data-k="${k}" class="${dim(k)}"><circle cx="${s.p[0]}" cy="${s.p[1]}" r="${0.2 * m}" fill="#6b3e1e"/>` + txt(s.p[0], s.p[1] + 0.07 * m, s.id, 0.2 * m, 'text-anchor="middle" fill="#fff" font-weight="bold"') + '</g>'); }
        for (const c of fd.points) { const k = `${F}:c:${c.id}`, a = c.kind === 'ic' ? 0.18 * m : 0.14 * m;
          const sh = c.kind === 'gully' ? `<circle cx="${c.p[0]}" cy="${c.p[1]}" r="${a}" fill="#fff" stroke="#c77d1a" stroke-width="${0.018 * m}"/>`
            : `<rect x="${c.p[0] - a}" y="${c.p[1] - a}" width="${2 * a}" height="${2 * a}" fill="${c.kind === 'eq' ? '#fff6d8' : '#fff'}" stroke="#6b3e1e" stroke-width="${0.02 * m}"/>`;
          o.push(`<g data-k="${k}" class="${dim(k)}">${sh}` + txt(c.p[0] + a + 0.04 * m, c.p[1] - a, c.id, 0.22 * m, 'fill="#6b3e1e" font-weight="bold"') + '</g>'); }
      }
      this.ov.innerHTML = o.join('');
    }
  }

  let panes = [];
  function layout() {
    const main = $('#main'); main.innerHTML = ''; panes = [];
    for (const F of ui.view === 'both' ? ['GF', 'FF'] : [ui.view]) panes.push(new Pane(F, main));
    document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('on', b.dataset.view === ui.view));
    redraw();
  }
  function select(k) { ui.sel = k && ui.sel !== k ? k : null; redraw(); }
  function find(k) {
    const [F, rest] = k.split(':'), fd = D.floors[F];
    if (rest[0] === 'p') return { F, t: 'p', o: fd.pipes[+rest.slice(1)] };
    const id = k.split(':')[2];
    if (rest === 'f') return { F, t: 'f', o: fd.fixtures.find(x => x.code === id) };
    if (rest === 'e') return { F, t: 'e', o: fd.equip.find(x => x.id === id) };
    if (rest === 's') return { F, t: 's', o: fd.stacks.find(x => x.id === id) };
    return { F, t: 'c', o: fd.points.find(x => x.id === id) };
  }
  function detail() {
    if (!ui.sel) return '<p class="muted">点图上的管段、用水点、立管或检查井，这里显示说明。</p>';
    const { F, t, o } = find(ui.sel);
    if (t === 'p') { const s = D.style[o.kind];
      return `<div class="det"><b>${FCN[F]}${o.no ? `${o.sheet} 第 ${o.no} 段` : o.sheet + ' 管段'}</b> · <span style="color:${s.color}">${esc(s.short)} Ø${o.size}</span><br>${esc(o.label || '（同一管路的分支）')}<br><span class="muted">${esc(s.label)}</span></div>`; }
    if (t === 'f') return `<div class="det"><b>${esc(o.code)}</b> ${esc(o.name)}<br>给水：${esc(o.sup)}（S 软冷 / H 热 / C 硬冷 / P 净水）· 排水：${esc(o.drain)}</div>`;
    return `<div class="det"><b>${esc(o.id)}</b> ${esc(o.name)}</div>`;
  }
  function side() {
    const kinds = Object.entries(D.style).filter(([k, s]) => ui.sys[s.sys]);
    const floors = ui.view === 'both' ? ['GF', 'FF'] : [ui.view];
    let h = `<h3>选中</h3>${detail()}`;
    if (floors.includes('FF')) h += `<div class="warn"><b>西卫（主卧卫生间）地面不抬高</b>：淋浴盘、马桶直接坐原楼板；后墙假墙尽量薄，能借后面原墙的位置就借，尽量保留卫生间内空：马桶段 1100 高（顶面平台，AAV + 检修口），淋浴段到天花、两个壁龛；110 马桶管在假墙内、地面以上走到北墙角，再沿北墙下那一格搁栅往后进 S1（方案 B）。详见 <a href="${pdfUrl(PDF[0][0])}#page=9" target="_blank" rel="noopener">P-08 西卫后墙详图</a>。</div>`;
    h += `<h3>图例</h3><div class="legend">${kinds.map(([k, s]) => `<span class="sw" style="border-top-color:${s.color};border-top-style:${s.dash ? 'dashed' : 'solid'}"></span><div>${esc(s.label)}</div>`).join('')}
      <span style="display:inline-block;width:12px;height:12px;border:1.5px solid #333;background:#fff"></span><div>用水点（编号同 PDF）</div>
      <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#6b3e1e"></span><div>污水立管 S1 / S2</div></div>`;
    for (const F of floors) for (const sys of ['supply', 'drain']) {
      if (!ui.sys[sys]) continue;
      const fd = D.floors[F], rows = fd.pipes.map((p, i) => [p, i]).filter(([p]) => p.sys === sys && p.no && p.label);
      h += `<h3>${FCN[F]}${sys === 'supply' ? '给水' : '排水'}管段（${sys === 'supply' ? (F === 'GF' ? 'P-01' : 'P-02') : (F === 'GF' ? 'P-03 / P-07' : 'P-04')}）</h3>` +
        rows.map(([p, i]) => { const s = D.style[p.kind], k = `${F}:p${i}`;
          return `<div class="prow ${ui.sel === k ? 'cur' : ''}" data-sel="${k}"><span class="no" style="background:${s.color}">${p.sheet === 'P-07' ? 'G' : ''}${p.no}</span><div>${esc(s.short)} Ø${p.size} · ${esc(p.label)}</div></div>`; }).join('');
      h += `<details><summary class="muted">${FCN[F]}${sys === 'supply' ? '给水' : '排水'}说明</summary><ol class="nt">${fd.notes[sys].map(n => `<li>${esc(n.replace(/^\d+\.\s*/, ''))}</li>`).join('')}</ol></details>`;
    }
    if (floors.includes('GF')) h += `<details><summary class="muted">后花园水池说明</summary><ol class="nt">${D.garden_notes.map(n => `<li>${esc(n.replace(/^\d+\.\s*/, ''))}</li>`).join('')}</ol></details>`;
    h += `<h3>施工图 PDF</h3>${PDF.map(([f, t]) => `<a class="pdf" href="${pdfUrl(f)}" target="_blank" rel="noopener">${esc(t)}</a>`).join('<br>')}`;
    $('#side').innerHTML = h;
    document.querySelectorAll('[data-sel]').forEach(r => r.onclick = () => select(r.dataset.sel));
  }
  function redraw() { panes.forEach(p => p.draw()); side(); }

  $('#ver').textContent = D.rev;
  document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { ui.view = b.dataset.view; layout(); });
  for (const s of ['supply', 'drain']) $('#s-' + s).onchange = e => { ui.sys[s] = e.target.checked; ui.sel = null; redraw(); };
  $('#nums').onchange = e => { ui.nums = e.target.checked; redraw(); };
  $('#clear').onclick = () => { ui.sel = null; ui.sys.supply = ui.sys.drain = true; $('#s-supply').checked = $('#s-drain').checked = true; redraw(); };
  parseHash(); $('#s-supply').checked = ui.sys.supply; $('#s-drain').checked = ui.sys.drain;
  layout();
})();
