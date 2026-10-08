/* 插座 / 动力 page: sockets and dedicated points on the plan, coloured by circuit, simple AL1 -> points wiring per circuit */
const L = window.LIGHTING_DEFAULT, P = window.POWER_DEFAULT, CC = window.CIRCUITS;
let C = CC.build(CC.pick());   // circuits of the plan in the URL hash (#A / #B)
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const ui = { view: 'GF', sel: null, trace: null, wires: true, lamps: true, plan: C.pid };
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

function lampsOf(F) {   // [{x, y, id, wl}] — each lamp coloured by the lighting circuit (WL) it belongs to in the current plan
  const J = L[F].json, wlOf = {};
  for (const w of C.list.filter(c => c.kind === 'WL' && c.floor === F)) for (const cid of w.circ) for (const lid of (J.circuits.find(c => c.id === cid)?.lights || [])) wlOf[lid] = w.id;
  return J.lights.filter(l => wlOf[l.id]).map(l => ({ x: l.x, y: l.y, id: l.id, wl: wlOf[l.id] }));
}
function nodesOf(F, cid) {   // sockets and appliances of one circuit on floor F, with stable ids (s<i> / i<i>)
  const n = [];
  P[F].sockets.forEach((s, i) => { if (s.c[ui.plan] === cid) n.push({ id: 's' + i, p: [s.x, s.y] }); });
  P[F].items.forEach((t, i) => { if (t.c[ui.plan] === cid) n.push({ id: 'i' + i, p: [t.x, t.y] }); });
  return n;
}
const isRing = c => /环路/.test(c.cable || '');
function graph(F, c, start) {   // ring: AL1 -> nearest-neighbour tour -> back to AL1; radial: tree grown from AL1
  const b = L[F].json.board, al = [b.x, b.y], nodes = nodesOf(F, c.id), E = [];
  const leg = (q, back) => back ? [...ortho(q.p, start), al] : [al, ...ortho(start, q.p)];
  if (!nodes.length) return E;
  if (isRing(c) && nodes.length > 1) {
    const rest = nodes.slice(), tour = []; let cur = al;
    while (rest.length) { const k = rest.reduce((bi, q, i) => dist(q.p, cur) < dist(rest[bi].p, cur) ? i : bi, 0); tour.push(rest[k]); cur = rest[k].p; rest.splice(k, 1); }
    E.push({ a: 'AL1', b: tour[0].id, pts: leg(tour[0]), feed: true });
    for (let i = 0; i + 1 < tour.length; i++) E.push({ a: tour[i].id, b: tour[i + 1].id, pts: ortho(tour[i].p, tour[i + 1].p) });
    E.push({ a: tour[tour.length - 1].id, b: 'AL1', pts: leg(tour[tour.length - 1], true), feed: true });
  } else {
    const inn = [{ id: 'AL1', p: al }], out = nodes.slice();
    while (out.length) {
      let best = null; for (const x of inn) for (const o of out) { const d = dist(x.p, o.p); if (!best || d < best.d) best = { d, x, o }; }
      E.push({ a: best.x.id, b: best.o.id, pts: best.x.id === 'AL1' ? leg(best.o) : ortho(best.x.p, best.o.p), feed: best.x.id === 'AL1' });
      inn.push(best.o); out.splice(out.indexOf(best.o), 1);
    }
  }
  return E;
}
function wires(F) {   // every socket / dedicated circuit; each leaves AL1 (or the riser on FF) on its own track
  const b = L[F].json.board, al = [b.x, b.y], m = M(F), out = [];
  const cs = C.list.filter(c => c.kind !== 'WL' && nodesOf(F, c.id).length);
  cs.forEach((c, i) => { const start = [al[0] + (i - (cs.length - 1) / 2) * 0.12 * m, al[1]]; graph(F, c, start).forEach(e => out.push({ ...e, c: c.id })); });
  return out.map((e, i) => ({ ...e, i }));
}
function tracePath(W, cid, target) {   // edge index -> forward?, from AL1 to the target; a ring is fed from both ends
  const E = W.filter(e => e.c === cid), adj = {};
  E.forEach(e => { (adj[e.a] = adj[e.a] || []).push([e.b, e, true]); (adj[e.b] = adj[e.b] || []).push([e.a, e, false]); });
  const walk = avoid => {
    const prev = { AL1: null }, q = ['AL1'];
    while (q.length) { const u = q.shift(); for (const [v, e, fw] of adj[u] || []) { if (v in prev || (u === 'AL1' && e === avoid)) continue; prev[v] = [u, e, fw]; q.push(v); } }
    if (!(target in prev)) return null;
    const path = []; let u = target; while (prev[u]) { path.unshift([prev[u][1], prev[u][2], u]); u = prev[u][0]; } return path;
  };
  const p1 = walk(null), edges = new Map(), sides = [];
  if (p1) { sides.push(p1); if (isRing(C.byId[cid])) { const p2 = walk(p1[0][0]); if (p2) sides.push(p2); } }
  sides.forEach(p => p.forEach(([e, fw]) => edges.set(e.i, fw)));
  return { edges, sides };
}
function nodeInfo(F, id) {
  if (id[0] === 's') { const s = P[F].sockets[+id.slice(1)]; return { label: KIND[s.kind][0], room: s.room, c: s.c[ui.plan], p: [s.x, s.y] }; }
  const t = P[F].items[+id.slice(1)]; return { label: t.label.replace(/（.*）/, ''), room: t.fcu ? t.fcu + ' 带保险开关' : '', c: t.c[ui.plan], p: [t.x, t.y], tbc: t.tbc };
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
    const mm = M(F);
    this.svg.innerHTML = `<style>.fl-${F}{stroke-dasharray:${0.16 * mm} ${0.1 * mm};animation:pf${F} .8s linear infinite}@keyframes pf${F}{to{stroke-dashoffset:${-0.52 * mm}}}</style><rect x="-1e9" y="-1e9" width="2e9" height="2e9" fill="#fff"/><g>${inner}</g><g class="ov"></g>`;
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
      drag = { x: ev.clientX, y: ev.clientY, vb: [...this.vb], s: this.vb[2] / svg.clientWidth, hit: ev.target.closest('[data-c]') }; moved = false; svg.setPointerCapture(ev.pointerId);   // remember what was pressed: with pointer capture the pointerup target is the svg
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
      if (drag && !moved) { const t = drag.hit; if (t && t.dataset.node) trace(this.F, t.dataset.node); else select(t ? t.dataset.c : null); }
      drag = null; };
    svg.addEventListener('pointerup', up); svg.addEventListener('pointercancel', ev => { touches.delete(ev.pointerId); drag = null; });
  }
  draw() {
    const F = this.F, m = M(F), o = [], T = ui.trace, W = wires(F);
    const tr = T && T.F === F ? tracePath(W, T.c, T.node) : null;
    const dim = c => (ui.sel && ui.sel !== c) || (T && T.c !== c) ? 'dim' : '';
    if (ui.wires) for (const w of W) { const c = C.byId[w.c], on = tr && tr.edges.has(w.i);
      const pts = on && !tr.edges.get(w.i) ? [...w.pts].reverse() : w.pts, d = `M${pts.map(p => p.join(' ')).join('L')}`;
      if (on) o.push(`<path d="${d}" fill="none" stroke="${c.color}" stroke-width="${0.11 * m}" stroke-linejoin="round" stroke-opacity=".3"/>`,
                     `<path d="${d}" fill="none" stroke="#c62828" stroke-width="${0.05 * m}" stroke-linejoin="round" class="fl-${F}"/>`);
      else o.push(`<path d="${d}" fill="none" stroke="${c.color}" stroke-width="${(w.feed ? 0.045 : 0.025) * m}" stroke-linejoin="round" ${w.feed ? '' : `stroke-dasharray="${0.08 * m} ${0.05 * m}"`} class="${dim(w.c)}" data-c="${w.c}"/>`); }
    if (ui.lamps) for (const l of lampsOf(F)) { const c = C.byId[l.wl], r = 0.09 * m;
      o.push(`<g data-c="${l.wl}" class="${dim(l.wl)}"><title>${esc(l.id)} · ${l.wl}</title><rect x="${l.x - r}" y="${l.y - r}" width="${2 * r}" height="${2 * r}" transform="rotate(45 ${l.x} ${l.y})" fill="#fff" stroke="${c.color}" stroke-width="${0.04 * m}"/></g>`); }
    const b = L[F].json.board;
    o.push(`<g><rect x="${b.x - 0.28 * m}" y="${b.y - 0.13 * m}" width="${0.56 * m}" height="${0.26 * m}" fill="#fff" stroke="#111" stroke-width="${0.025 * m}"/><path d="M${b.x - 0.28 * m} ${b.y + 0.13 * m}L${b.x + 0.28 * m} ${b.y - 0.13 * m}L${b.x + 0.28 * m} ${b.y + 0.13 * m}Z" fill="#111"/>${txt(b.x, b.y + 0.4 * m, F === 'GF' ? 'AL1' : '↑ AL1 引上', 0.2 * m, 'text-anchor="middle" font-weight="bold"')}</g>`);
    P[F].sockets.forEach((s, i) => { const sc = s.c[ui.plan], c = C.byId[sc]; o.push(`<g data-c="${sc}" data-node="s${i}" class="${dim(sc)}"><title>${esc(KIND[s.kind][0])} · ${esc(s.room)} · ${sc}（点一下看电从哪来）</title>${sym(F, s.x, s.y, s.kind, c.color, m)}</g>`); });
    P[F].items.forEach((t, i) => { const tc = t.c[ui.plan], c = C.byId[tc]; o.push(`<g data-c="${tc}" data-node="i${i}" class="${dim(tc)}"><title>${esc(t.label)} · ${tc}（点一下看电从哪来）</title>${itemSym(t, c.color, m)}</g>`); });
    if (T && T.F === F) { const n = nodeInfo(F, T.node); o.push(`<circle cx="${n.p[0]}" cy="${n.p[1]}" r="${0.32 * m}" fill="none" stroke="#c62828" stroke-width="${0.05 * m}" pointer-events="none"/>`); }
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
function select(id) { ui.trace = null; ui.sel = ui.sel === id ? null : id; draw(); }
function trace(F, node) { const n = nodeInfo(F, node); ui.sel = null; ui.trace = ui.trace && ui.trace.F === F && ui.trace.node === node ? null : { F, node, c: n.c }; draw(); }

function traceHtml() {   // AL1 -> breaker -> cable -> sockets on the way -> this socket, and what else goes off with it
  const T = ui.trace; if (!T) return '';
  const n = nodeInfo(T.F, T.node), c = C.byId[n.c], W = wires(T.F), tr = tracePath(W, n.c, T.node), ring = isRing(c) && tr.sides.length > 1;
  const via = side => side.slice(0, -1).map(([, , id]) => nodeInfo(T.F, id)), rooms = arr => [...new Set(arr.map(x => x.room).filter(Boolean))];
  const ways = tr.sides.map(sd => { const v = via(sd); return v.length ? `经过 ${v.length} 个点（${rooms(v).join('、') || '同一房间'}）` : '直接到这里'; });
  const all = ['GF', 'FF'].flatMap(F => nodesOf(F, n.c).map(x => ({ F, id: x.id, ...nodeInfo(F, x.id) })));
  const roomsAll = [...new Set(all.map(x => (x.F === 'GF' ? '一层' : '二层') + (x.id[0] === 's' ? x.room : x.label)))];
  const items = [...new Set(all.filter(x => x.id[0] === 'i').map(x => x.label))], nSock = all.filter(x => x.id[0] === 's').length;
  return `<div class="trace"><h3>电从哪里来</h3>
    <div class="step">① 配电箱 <b>AL1</b>（一层楼梯下）${T.F === 'FF' ? '，沿楼梯井引上二层' : ''}</div><div class="arrow">↓</div>
    <div class="step">② 断路器 <span class="chip" style="background:${c.color}">${c.id}</span> ${esc(c.br)}<div class="muted">${esc(c.name)}</div></div><div class="arrow">↓</div>
    <div class="step">③ 线：${esc(c.cable)}${ring ? '<div class="muted">环路：线从配电箱出去，串过所有插座再回到配电箱，<b>电从两头过来</b>（图上两条红色流动线）</div>' : ''}</div><div class="arrow">↓</div>
    <div class="step">④ ${ways.map((w, i) => (ring ? (i ? '另一头：' : '一头：') : '') + w).join('<br>')}</div><div class="arrow">↓</div>
    <div class="step">⑤ <b>这个点</b>：${esc(n.label)}${n.room ? ' · ' + esc(n.room) : ''}${n.tbc ? `<div class="tbc">${esc(n.tbc)}</div>` : ''}</div>
    <div class="off"><b>${c.id} 跳闸时，一起断电的有：</b>${nSock} 个插座${items.length ? ' + ' + items.join('、') : ''}<div class="muted">${roomsAll.join('、')}</div></div>
    <p class="muted">再点一次这个插座，或点空白处，取消追踪。</p></div>`;
}
function side() {
  const h = [traceHtml()], row = c => {
    const pts = ['GF', 'FF'].flatMap(F => P[F].items.filter(t => t.c[ui.plan] === c.id));
    return `<div class="crow ${ui.sel === c.id ? 'cur' : ''}" data-sel="${c.id}"><span class="chip" style="background:${c.color}">${c.id}</span>
      <div>${esc(c.name)}<div class="br">${esc(c.br)} · ${esc(c.cable)}</div>${c.note ? `<div class="br">${esc(c.note)}</div>` : ''}${pts.filter(t => t.tbc).map(t => `<div class="br tbc">${esc(t.label)}：${esc(t.tbc)}</div>`).join('')}</div>
      <span class="n">${esc(c.count)}</span></div>`;
  };
  const xs = C.list.filter(c => c.kind === 'WX'), ps = C.list.filter(c => c.kind === 'WP'), ls = C.list.filter(c => c.kind === 'WL'), pl = C.plan;
  if (!ui.trace) h.push(`<p class="hint">👆 点图上任意一个插座或电器，看它的电从配电箱哪一路、经过哪些地方过来。</p>`);
  h.push(`<h3>${esc(pl.name)}</h3><div class="muted">共 ${C.list.length} 路：照明 ${C.list.filter(c => c.kind === 'WL').length} + 插座 ${xs.length} + 专线 ${ps.length} · 配电箱 ${esc(pl.board.model)}（${pl.board.ways} 位）· <a href="board.html#${ui.plan}">配电箱</a></div>`);
  h.push(`<h3>照明回路（${ls.length} 路，图上菱形 = 灯）</h3>`, ...ls.map(row));
  h.push(`<h3>插座回路（${xs.length} 路）</h3>`, ...xs.map(row));
  h.push(`<h3>专线（${ps.length} 路，一样电器一路）</h3>`, ...ps.map(row));
  h.push(`<h3>图例</h3><div class="legend">`,
    ...Object.entries(KIND).map(([k, [n, t]]) => `<svg viewBox="-14 -14 28 28" width="22" height="22"><circle r="12" fill="#666"/><text y="5" font-size="14" text-anchor="middle" fill="#fff" font-weight="bold">${t}</text></svg><div>${n}</div>`),
    `<svg viewBox="-14 -9 28 18" width="24" height="16"><rect x="-13" y="-8" width="26" height="16" rx="3" fill="#fff" stroke="#666" stroke-width="2"/></svg><div>专线电器 / FCU 带保险开关</div>`,
    `<svg viewBox="-12 -12 24 24" width="20" height="20"><rect x="-7" y="-7" width="14" height="14" transform="rotate(45)" fill="#fff" stroke="#666" stroke-width="3"/></svg><div>灯（颜色 = 照明回路；开关和联动见「照明」页）</div>`,
    `<svg viewBox="0 -4 28 8" width="24" height="8"><path d="M0 0H28" stroke="#666" stroke-width="4"/></svg><div>粗线 = AL1 引出（每路一根）</div>`,
    `<svg viewBox="0 -4 28 8" width="24" height="8"><path d="M0 0H28" stroke="#666" stroke-width="2" stroke-dasharray="5 3"/></svg><div>虚线 = 同一路的插座串在一起</div></div>`);
  h.push(`<p class="muted">插座点位来自 v10 PPT 插座页（你标的圆点；2026-10-06 按 v7 / v9 更新）。线路只表示属于哪一路，实际走线现场定。开关和联动见「照明」页，全部回路、采购清单见「配电箱」页。</p>`);
  $('#side').innerHTML = h.join('');
  $('#side').querySelectorAll('[data-sel]').forEach(e => e.onclick = () => select(e.dataset.sel));
}

document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { ui.view = b.dataset.view; layout(); });
$('#showwires').onchange = e => { ui.wires = e.target.checked; draw(); };
$('#showlamps').onchange = e => { ui.lamps = e.target.checked; draw(); };
$('#clear').onclick = () => { ui.sel = null; ui.trace = null; draw(); };
function setPlan(pid) {
  ui.plan = pid; C = CC.build(pid); ui.sel = null; ui.trace = null;
  if (location.hash.replace('#', '').toUpperCase() !== pid) history.replaceState(null, '', '#' + pid);
  document.querySelectorAll('[data-plan]').forEach(b => b.classList.toggle('on', b.dataset.plan === pid));
  $('#ver').textContent = C.plan.short; draw();
}
document.querySelectorAll('[data-plan]').forEach(b => b.onclick = () => setPlan(b.dataset.plan));
window.addEventListener('hashchange', () => setPlan(CC.pick()));
layout(); setPlan(ui.plan);
window.POWER = { ui, select, layout, panes: () => panes };
