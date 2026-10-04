/* 插座 / 动力 page: sockets and dedicated points on the plan, coloured by circuit, simple AL1 -> points wiring per circuit */
const L = window.LIGHTING_DEFAULT, P = window.POWER_DEFAULT, CC = window.CIRCUITS;
let C = CC.build(CC.pick());   // circuits of the plan in the URL hash (#A / #B)
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const ui = { view: 'GF', sel: null, wires: true, plan: C.pid };
const M = F => L[F].json.units.emu_per_m;
const KIND = { double: ['双联插座', '2'], single: ['单联插座', '1'], outdoor: ['户外防水插座', '外'], high: ['高位插座', '高'] };

// browsers cap font-size at 10000px, and the plan is in slide EMU: draw text small and scale it up (as the lighting tool's txt())
const txt = (x, y, s, size, attrs = '') => `<text transform="translate(${x} ${y}) scale(1000)" font-size="${size / 1000}" ${attrs}>${esc(s)}</text>`;
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
function mst(nodes) {
  if (nodes.length < 2) return [];
  const inn = [nodes[0]], rest = nodes.slice(1), E = [];
  while (rest.length) { let b = null; for (const a of inn) for (const o of rest) { const d = dist(a, o); if (!b || d < b.d) b = { d, a, o }; } E.push([b.a, b.o]); inn.push(b.o); rest.splice(rest.indexOf(b.o), 1); }
  return E;
}
const ortho = (a, b) => (Math.abs(a[0] - b[0]) < 1 || Math.abs(a[1] - b[1]) < 1) ? [a, b] : [a, Math.abs(b[0] - a[0]) >= Math.abs(b[1] - a[1]) ? [b[0], a[1]] : [a[0], b[1]], b];

function pointsOf(F, cid) {
  return [...P[F].sockets.filter(s => s.c[ui.plan] === cid).map(s => [s.x, s.y]), ...P[F].items.filter(t => t.c === cid).map(t => [t.x, t.y])];
}
function wires(F) {   // per circuit: AL1 (or the riser on FF) -> nearest point, then a tree through its points; each circuit leaves on its own track
  const b = L[F].json.board, al = [b.x, b.y], m = M(F), out = [];
  const cs = C.list.filter(c => c.kind !== 'WL' && pointsOf(F, c.id).length);
  cs.forEach((c, i) => {
    const pts = pointsOf(F, c.id), start = [al[0] + (i - (cs.length - 1) / 2) * 0.12 * m, al[1]];
    const first = pts.reduce((a, p) => dist(p, al) < dist(a, al) ? p : a);
    out.push({ c: c.id, pts: [al, ...ortho(start, first)], feed: true });
    mst(pts).forEach(([a, q]) => out.push({ c: c.id, pts: ortho(a, q) }));
  });
  return out;
}

function sym(F, x, y, kind, col, m) {
  const r = 0.15 * m, [, t] = KIND[kind];
  return `<circle cx="${x}" cy="${y}" r="${r}" fill="${col}" stroke="#fff" stroke-width="${0.02 * m}"/>` +
    txt(x, y + 0.06 * m, t, 0.17 * m, 'text-anchor="middle" fill="#fff" font-weight="bold"');
}
function itemSym(t, col, m) {
  const w = Math.max(0.7, t.label.replace(/（.*）/, '').length * 0.2 + 0.2) * m, h = 0.3 * m, lab = t.label.replace(/（.*）/, '');
  return `<rect x="${t.x - w / 2}" y="${t.y - h / 2}" width="${w}" height="${h}" rx="${0.05 * m}" fill="#fff" stroke="${col}" stroke-width="${0.035 * m}"/>` +
    txt(t.x, t.y + 0.07 * m, lab, 0.18 * m, `text-anchor="middle" fill="${col}" font-weight="bold"`) +
    (t.fcu ? txt(t.x, t.y + h / 2 + 0.2 * m, t.fcu, 0.13 * m, 'text-anchor="middle" fill="#666"') : '');
}

class Pane {
  constructor(F, host) {
    this.F = F; this.vb = [...L[F].json.units.view_box];
    this.el = document.createElement('div'); this.el.className = 'pane'; host.appendChild(this.el);
    this.el.innerHTML = `<div class="ttl">${CC.FCN[F]}插座 / 动力</div><div class="zb"><button data-z="in">＋</button><button data-z="out">－</button><button data-z="fit" style="width:44px;font-size:12px">复位</button></div>`;
    this.el.querySelector('.zb').addEventListener('click', e => { const z = e.target.dataset.z; if (!z) return;
      if (z === 'fit') { this.vb = [...L[F].json.units.view_box]; return this.setVB(); }
      const k = z === 'in' ? 1 / 1.4 : 1.4, c = [this.vb[0] + this.vb[2] / 2, this.vb[1] + this.vb[3] / 2];
      this.vb = [c[0] - this.vb[2] * k / 2, c[1] - this.vb[3] * k / 2, this.vb[2] * k, this.vb[3] * k]; this.setVB(); });
    this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); this.el.appendChild(this.svg);
    const inner = L[F].svg.replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '');
    this.svg.innerHTML = `<rect x="-1e9" y="-1e9" width="2e9" height="2e9" fill="#fff"/><g>${inner}</g><g class="ov"></g>`;
    this.ov = this.svg.querySelector('.ov'); this.setVB(); this.events();
  }
  setVB() { this.svg.setAttribute('viewBox', this.vb.join(' ')); }
  pt(ev) { const p = this.svg.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY; const q = p.matrixTransform(this.svg.getScreenCTM().inverse()); return [q.x, q.y]; }
  events() {
    const svg = this.svg, touches = new Map();
    svg.addEventListener('wheel', ev => { ev.preventDefault(); const p = this.pt(ev), k = ev.deltaY > 0 ? 1.15 : 1 / 1.15;
      this.vb = [p[0] - (p[0] - this.vb[0]) * k, p[1] - (p[1] - this.vb[1]) * k, this.vb[2] * k, this.vb[3] * k]; this.setVB(); }, { passive: false });
    let drag = null, moved = false;
    svg.addEventListener('pointerdown', ev => {
      if (ev.pointerType === 'touch') touches.set(ev.pointerId, [ev.clientX, ev.clientY]);
      if (touches.size > 1) { drag = null; return; }
      drag = { x: ev.clientX, y: ev.clientY, vb: [...this.vb], s: this.vb[2] / svg.clientWidth }; moved = false; svg.setPointerCapture(ev.pointerId);
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
    const up = ev => { touches.delete(ev.pointerId);
      if (drag && !moved) { const t = ev.target.closest('[data-c]'); select(t ? t.dataset.c : null); }
      drag = null; };
    svg.addEventListener('pointerup', up); svg.addEventListener('pointercancel', ev => { touches.delete(ev.pointerId); drag = null; });
  }
  draw() {
    const F = this.F, m = M(F), o = [], dim = c => ui.sel && ui.sel !== c ? 'dim' : '';
    if (ui.wires) for (const w of wires(F)) { const c = C.byId[w.c];
      o.push(`<path d="M${w.pts.map(p => p.join(' ')).join('L')}" fill="none" stroke="${c.color}" stroke-width="${(w.feed ? 0.045 : 0.025) * m}" stroke-linejoin="round" ${w.feed ? '' : `stroke-dasharray="${0.08 * m} ${0.05 * m}"`} class="${dim(w.c)}" data-c="${w.c}"/>`); }
    const b = L[F].json.board;
    o.push(`<g><rect x="${b.x - 0.28 * m}" y="${b.y - 0.13 * m}" width="${0.56 * m}" height="${0.26 * m}" fill="#fff" stroke="#111" stroke-width="${0.025 * m}"/><path d="M${b.x - 0.28 * m} ${b.y + 0.13 * m}L${b.x + 0.28 * m} ${b.y - 0.13 * m}L${b.x + 0.28 * m} ${b.y + 0.13 * m}Z" fill="#111"/>${txt(b.x, b.y + 0.4 * m, F === 'GF' ? 'AL1' : '↑ AL1 引上', 0.2 * m, 'text-anchor="middle" font-weight="bold"')}</g>`);
    for (const s of P[F].sockets) { const sc = s.c[ui.plan], c = C.byId[sc]; o.push(`<g data-c="${sc}" class="${dim(sc)}"><title>${esc(KIND[s.kind][0])} · ${esc(s.room)} · ${sc}</title>${sym(F, s.x, s.y, s.kind, c.color, m)}</g>`); }
    for (const t of P[F].items) { const c = C.byId[t.c]; o.push(`<g data-c="${t.c}" class="${dim(t.c)}"><title>${esc(t.label)} · ${t.c}${t.tbc ? ' · ' + esc(t.tbc) : ''}</title>${itemSym(t, c.color, m)}</g>`); }
    this.ov.innerHTML = o.join('');
  }
}

let panes = [];
function layout() {
  const host = $('#main'); host.innerHTML = '';
  panes = (ui.view === 'both' ? ['GF', 'FF'] : [ui.view]).map(F => new Pane(F, host));
  document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('on', b.dataset.view === ui.view));
  draw();
}
function draw() { panes.forEach(p => p.draw()); side(); }
function select(id) { ui.sel = ui.sel === id ? null : id; draw(); }

function side() {
  const h = [], row = c => {
    const pts = ['GF', 'FF'].flatMap(F => P[F].items.filter(t => t.c === c.id));
    return `<div class="crow ${ui.sel === c.id ? 'cur' : ''}" data-sel="${c.id}"><span class="chip" style="background:${c.color}">${c.id}</span>
      <div>${esc(c.name)}<div class="br">${esc(c.br)} · ${esc(c.cable)}</div>${c.note ? `<div class="br">${esc(c.note)}</div>` : ''}${pts.filter(t => t.tbc).map(t => `<div class="br tbc">${esc(t.label)}：${esc(t.tbc)}</div>`).join('')}</div>
      <span class="n">${esc(c.count)}</span></div>`;
  };
  const xs = C.list.filter(c => c.kind === 'WX'), ps = C.list.filter(c => c.kind === 'WP'), pl = C.plan;
  h.push(`<h3>${esc(pl.name)}</h3><div class="muted">共 ${C.list.length} 路：照明 ${C.list.filter(c => c.kind === 'WL').length} + 插座 ${xs.length} + 专线 ${ps.length} · 配电箱 ${esc(pl.board.model)}（${pl.board.ways} 位）· <a href="board.html#${ui.plan}">看 A / B 对比</a></div>`);
  h.push(`<h3>插座回路（${xs.length} 路）</h3>`, ...xs.map(row));
  h.push(`<h3>专线（${ps.length} 路，一样电器一路）</h3>`, ...ps.map(row));
  h.push(`<h3>图例</h3><div class="legend">`,
    ...Object.entries(KIND).map(([k, [n, t]]) => `<svg viewBox="-14 -14 28 28" width="22" height="22"><circle r="12" fill="#666"/><text y="5" font-size="14" text-anchor="middle" fill="#fff" font-weight="bold">${t}</text></svg><div>${n}</div>`),
    `<svg viewBox="-14 -9 28 18" width="24" height="16"><rect x="-13" y="-8" width="26" height="16" rx="3" fill="#fff" stroke="#666" stroke-width="2"/></svg><div>专线电器 / FCU 带保险开关</div>`,
    `<svg viewBox="0 -4 28 8" width="24" height="8"><path d="M0 0H28" stroke="#666" stroke-width="4"/></svg><div>粗线 = AL1 引出（每路一根）</div>`,
    `<svg viewBox="0 -4 28 8" width="24" height="8"><path d="M0 0H28" stroke="#666" stroke-width="2" stroke-dasharray="5 3"/></svg><div>虚线 = 同一路的插座串在一起</div></div>`);
  h.push(`<p class="muted">插座点位来自 v6 PPT 插座页（你标的圆点），两个方案点位相同，只是分路不同。线路只表示属于哪一路，实际走线现场定。照明见「照明」页（显示方案 A 的 4 路），全部回路和两个方案的对比见「配电箱」页。</p>`);
  $('#side').innerHTML = h.join('');
  $('#side').querySelectorAll('[data-sel]').forEach(e => e.onclick = () => select(e.dataset.sel));
}

document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { ui.view = b.dataset.view; layout(); });
$('#showwires').onchange = e => { ui.wires = e.target.checked; draw(); };
$('#clear').onclick = () => { ui.sel = null; draw(); };
function setPlan(pid) {
  ui.plan = pid; C = CC.build(pid); ui.sel = null;
  if (location.hash.replace('#', '').toUpperCase() !== pid) history.replaceState(null, '', '#' + pid);
  document.querySelectorAll('[data-plan]').forEach(b => b.classList.toggle('on', b.dataset.plan === pid));
  $('#ver').textContent = C.plan.short; draw();
}
document.querySelectorAll('[data-plan]').forEach(b => b.onclick = () => setPlan(b.dataset.plan));
window.addEventListener('hashchange', () => setPlan(CC.pick()));
layout(); setPlan(ui.plan);
window.POWER = { ui, select, layout, panes: () => panes };
