'use strict';
/* 27PR 平面图照明 workflow 工具
   数据：lighting_GF.json / lighting_FF.json（坐标 = 用户 PPT 页面 EMU），墙体：walls_GF.svg / walls_FF.svg
   试灯：每个键是一个开关，同一回路的所有控制点按“异或”计算（双控 / 中途开关三控都成立），门控 MK 并联。 */

const FLOORS = ['GF', 'FF'], FCN = { GF: '一层', FF: '二层' };
const WATT = { 筒灯: 5, 主灯: 40, 待选: 40, 壁灯: 10, 地灯: 3 };
const PALETTE = ['#e07a1f', '#2e86ab', '#3b9c5a', '#8e5cc5', '#00838f', '#c2185b', '#6d4c41', '#d1495b'];
const LETTERS = 'abcdefghijklmnopqrstuvwxyz';
const BATH = /卫生间|主卫|浴室/;
const clone = o => JSON.parse(JSON.stringify(o));
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const add = (a, b) => [a[0] + b[0], a[1] + b[1]], sub = (a, b) => [a[0] - b[0], a[1] - b[1]], mul = (a, k) => [a[0] * k, a[1] * k];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1];
const norm = a => { const l = Math.hypot(a[0], a[1]) || 1; return [a[0] / l, a[1] / l]; };
const $ = s => document.querySelector(s);

let ORIG = window.LIGHTING_DEFAULT || null;
let S = {}, SVGSRC = {}, GEO = {}, D = {}, ISS = [];
const sim = { key: {}, door: {}, brk: {} };
const ui = { mode: 'sim', tool: 'select', view: 'GF', sel: null, ak: null, trace: null, wires: true, issues: true, tab: 'info', drag: null, box: null, snapHint: null };
const hist = { undo: [], redo: [] };
const panes = [];
let SERVER = false, lastBuild = null;

const M = F => S[F].units.emu_per_m;
const P = F => S[F].plates;
const wlColor = w => { const n = parseInt(String(w).replace(/\D/g, ''), 10) || 0; return PALETTE[(n - 1 + PALETTE.length) % PALETTE.length]; };
const kid = (F, plate, key) => `${F}|${plate}|${key}`;

/* ---------------- geometry (walls, rooms raster, doors) ---------------- */
function buildGeo(F) {
  const J = S[F], m = M(F), vb = J.units.view_box;
  const doc = new DOMParser().parseFromString(SVGSRC[F], 'image/svg+xml');
  const polys = [];
  doc.querySelectorAll('g[class] > path').forEach(p => {
    const d = p.getAttribute('d'), nums = d.replace(/[MLZ]/g, ' ').trim().split(/\s+/).map(Number), pts = [];
    for (let i = 0; i + 1 < nums.length; i += 2) pts.push([nums[i], nums[i + 1]]);
    polys.push({ cls: p.parentNode.getAttribute('class'), d, pts, closed: /Z\s*$/.test(d), name: p.getAttribute('data-name') });
  });
  const segs = [];
  for (const Q of polys) if (Q.cls === 'wall') {
    const n = Q.pts.length;
    for (let i = 0; i < n - (Q.closed ? 0 : 1); i++) segs.push([Q.pts[i], Q.pts[(i + 1) % n]]);
  }
  const res = 0.05 * m, k = 1 / res, W = Math.ceil(vb[2] * k), H = Math.ceil(vb[3] * k);
  const ras = keep => {
    const c = document.createElement('canvas'); c.width = W; c.height = H;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.setTransform(k, 0, 0, k, -vb[0] * k, -vb[1] * k); g.lineWidth = 0.04 * m;
    for (const Q of polys) if (keep(Q.cls)) { const p2 = new Path2D(Q.d); g.fill(p2, 'evenodd'); g.stroke(p2); }
    const a = g.getImageData(0, 0, W, H).data, o = new Uint8Array(W * H);
    for (let i = 0; i < W * H; i++) o[i] = a[i * 4 + 3] > 40 ? 1 : 0;
    return o;
  };
  const occ = ras(c => c !== 'stair'), occW = ras(c => c === 'wall');
  const toPx = (x, y) => [Math.floor((x - vb[0]) * k), Math.floor((y - vb[1]) * k)];
  const inR = (x, y) => x >= 0 && y >= 0 && x < W && y < H;
  const nearest = (px, py, ok, R) => {
    for (let r = 0; r <= R; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
      if (Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
      const x = px + dx, y = py + dy;
      if (inR(x, y) && ok(y * W + x)) return y * W + x;
    }
    return -1;
  };
  // rooms: multi-source flood fill from the room-name points (open doorways split by geodesic distance)
  const own = new Int16Array(W * H).fill(-1), q = new Int32Array(W * H); let qh = 0, qt = 0;
  J.rooms.forEach((r, i) => { const [px, py] = toPx(r.x, r.y); const s = nearest(px, py, t => !occ[t], 12); if (s >= 0 && own[s] < 0) { own[s] = i; q[qt++] = s; } });
  while (qh < qt) {
    const s = q[qh++], x = s % W, y = (s / W) | 0;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx, ny = y + dy; if (!inR(nx, ny)) continue;
      const t = ny * W + nx; if (occ[t] || own[t] >= 0) continue; own[t] = own[s]; q[qt++] = t;
    }
  }
  const roomAt = (x, y) => { const [px, py] = toPx(x, y); const s = nearest(px, py, t => own[t] >= 0, 10); return s < 0 ? -1 : own[s]; };
  const wallAt = (x, y) => { const [px, py] = toPx(x, y); return inR(px, py) && occW[py * W + px] === 1; };
  const G = { polys, segs, roomAt, wallAt, doors: [] };
  // doors: open leaves (thin, 0.5–1.4 m) -> hinge = end touching the wall, lock jamb = hinge + leaf length along the wall
  for (const dr of J.doors) {
    if (!/Leaf/.test(dr.name) || /WR_/.test(dr.name) || dr.pts.length < 3) continue;
    const n = dr.pts.length, c = dr.pts.reduce((a, p) => add(a, mul(p, 1 / n)), [0, 0]);
    let sxx = 0, syy = 0, sxy = 0;
    for (const p of dr.pts) { const d = sub(p, c); sxx += d[0] * d[0]; syy += d[1] * d[1]; sxy += d[0] * d[1]; }
    const th = 0.5 * Math.atan2(2 * sxy, sxx - syy), ax = [Math.cos(th), Math.sin(th)], pr = [-ax[1], ax[0]];
    const ta = dr.pts.map(p => dot(sub(p, c), ax)), tp = dr.pts.map(p => dot(sub(p, c), pr));
    const L = Math.max(...ta) - Math.min(...ta), T = Math.max(...tp) - Math.min(...tp);
    if (L < 0.5 * m || L > 1.4 * m || T > 0.15 * m) continue;
    const e1 = add(c, mul(ax, Math.min(...ta))), e2 = add(c, mul(ax, Math.max(...ta)));
    const d1 = wallNear(G, e1).d, d2 = wallNear(G, e2).d;
    const hinge = d1 <= d2 ? e1 : e2, free = d1 <= d2 ? e2 : e1;
    if (Math.min(d1, d2) > 0.25 * m) continue;
    let best = null;
    for (const s of [1, -1]) {
      const e = mul(pr, s), mid = add(hinge, mul(e, L / 2)), beyond = add(hinge, mul(e, L + 0.12 * m));
      const sc = (wallAt(...mid) ? 0 : 2) + (wallAt(...beyond) ? 1 : 0) + (wallAt(...add(hinge, mul(e, -0.12 * m))) ? 1 : 0);
      if (!best || sc > best.sc) best = { sc, e };
    }
    G.doors.push({ name: dr.name, hinge, lock: add(hinge, mul(best.e, L)), e: best.e, n: norm(sub(free, hinge)), L });
  }
  return G;
}

function wallNear(G, p) {
  let best = { d: Infinity, q: p };
  for (const [a, b] of G.segs) {
    const v = sub(b, a), L2 = dot(v, v) || 1, t = Math.max(0, Math.min(1, dot(sub(p, a), v) / L2)), q = add(a, mul(v, t)), d = dist(p, q);
    if (d < best.d) best = { d, q };
  }
  return best;
}
const roomName = (F, x, y) => { const i = GEO[F].roomAt(x, y); return i < 0 ? '室外' : S[F].rooms[i].name; };

/* ---------------- derived data ---------------- */
function controlsOf(F, c) {
  const out = [];
  for (const k of c.keys) for (const p of P(F)) if (p.keys.includes(k))
    out.push({ F, plate: p.id, key: k, gang: p.keys.indexOf(k) + 1, middle: (p.middle_keys || []).includes(k) });
  for (const rl of c.remote_links || []) {
    const p = S[rl.floor]?.plates.find(x => x.id === rl.plate);
    out.push({ F: rl.floor, plate: rl.plate, key: rl.key, gang: p ? p.keys.indexOf(rl.key) + 1 : 0, middle: !!p && (p.middle_keys || []).includes(rl.key), remote: true, broken: !p || !p.keys.includes(rl.key) });
  }
  return out;
}
const modeName = n => ({ 0: '无开关', 1: '单控', 2: '双控', 3: '三控' }[n] || `${n}控`);

function derive() {
  for (const F of FLOORS) {
    const J = S[F], d = D[F] = { L: {}, P: {}, C: {}, keyCirc: {}, lightCirc: {}, ctrls: {}, fan: {}, wires: [], room: {} };
    J.lights.forEach(l => { d.L[l.id] = l; d.room[l.id] = roomName(F, l.x, l.y); });
    J.plates.forEach(p => d.P[p.id] = p);
    J.circuits.forEach(c => { d.C[c.id] = c; c.keys.forEach(k => d.keyCirc[k] = c.id); c.lights.forEach(l => d.lightCirc[l] = c.id); });
    J.circuits.forEach(c => d.ctrls[c.id] = controlsOf(F, c));
  }
  for (const F of FLOORS) { fans(F); wires(F); }
  checks();
}

function plateCircuits(F, p) { return p.keys.map(k => D[F].keyCirc[k]).filter(Boolean); }

function fans(F) {   // FI isolator -> the bathroom circuit switched next to it (fan runs with that light)
  const d = D[F], m = M(F);
  for (const p of P(F)) {
    if (p.gangs !== 0) continue;
    let best = null;
    for (const c of S[F].circuits) for (const x of d.ctrls[c.id]) {
      if (x.F !== F) continue;
      const q = d.P[x.plate], dd = dist([p.x, p.y], [q.x, q.y]) - (c.lights.some(l => BATH.test(d.room[l])) ? 0.5 * m : 0);
      if (!best || dd < best.d) best = { d: dd, c: c.id };
    }
    if (best && best.d < 1.5 * m) d.fan[p.id] = best.c;
  }
}

/* ---------------- simulation ---------------- */
const breakerOn = (F, c) => !!c.wl && sim.brk[c.wl] !== false && !!S[F].wl[c.wl];
function circuitOut(F, c) {
  const xs = D[F].ctrls[c.id] || [];
  const par = xs.reduce((a, x) => a ^ (sim.key[kid(x.F, x.plate, x.key)] ? 1 : 0), 0);
  const door = S[F].door_switches.some(ds => ds.circuit === c.id && sim.door[F + '|' + ds.id]);
  return (xs.length && par === 1) || door;
}
const circuitOn = (F, c) => breakerOn(F, c) && circuitOut(F, c);
const lightOn = (F, id) => { const c = D[F].C[D[F].lightCirc[id]]; return !!c && circuitOn(F, c); };
function setCircuit(F, c, on) {   // flip the first control so the circuit ends up on / off
  if (circuitOut(F, c) === on) return;
  const x = D[F].ctrls[c.id][0]; if (!x) return;
  const k = kid(x.F, x.plate, x.key); sim.key[k] = !sim.key[k];
}

/* ---------------- wiring (like 国标 plan: AL1 -> WL -> switch boxes; same-letter lamps chained; switch drops; travellers) ---------------- */
function mst(nodes) {
  if (nodes.length < 2) return [];
  const inn = [nodes[0]], out = nodes.slice(1), E = [];
  while (out.length) {
    let b = null;
    for (const a of inn) for (const o of out) { const dd = dist(a.p, o.p); if (!b || dd < b.d) b = { d: dd, a, o }; }
    E.push([b.a, b.o]); inn.push(b.o); out.splice(out.indexOf(b.o), 1);
  }
  return E;
}
function ortho(a, b) {
  if (Math.abs(a[0] - b[0]) < 1 || Math.abs(a[1] - b[1]) < 1) return [a, b];
  return [a, Math.abs(b[0] - a[0]) >= Math.abs(b[1] - a[1]) ? [b[0], a[1]] : [a[0], b[1]], b];
}
function orthoClear(a, b, avoid) {
  const segD = (p, q, c) => { const v = sub(q, p), L2 = dot(v, v) || 1, t = Math.max(0, Math.min(1, dot(sub(c, p), v) / L2)); return dist(add(p, mul(v, t)), c); };
  let best = null;
  for (const cr of [[b[0], a[1]], [a[0], b[1]]]) {
    const dd = Math.min(Infinity, ...avoid.map(c => Math.min(segD(a, cr, c), segD(cr, b, c))));
    if (!best || dd > best.d) best = { d: dd, cr };
  }
  return [a, best.cr, b];
}
function wires(F) {
  const d = D[F], J = S[F], W = d.wires = [], LP = id => [d.L[id].x, d.L[id].y];
  const al = [J.board.x, J.board.y];
  const WLS = Object.keys(J.wl);
  for (const w of WLS) {
    const plates = J.plates.filter(p => p.keys.some(k => d.C[d.keyCirc[k]]?.wl === w));
    if (!plates.length) continue;
    const nodes = plates.map(p => ({ id: p.id, p: [p.x, p.y] }));
    const E = mst(nodes), first = nodes.reduce((a, n) => dist(n.p, al) < dist(a.p, al) ? n : a);
    const out = [al[0] + (WLS.indexOf(w) - (WLS.length - 1) / 2) * 0.16 * M(F), al[1]];   // each WL leaves AL1 on its own track, side by side
    W.push({ kind: 'feed', wl: w, a: 'AL1', b: first.id, pts: [al, ...ortho(out, first.p)] });
    E.forEach(([a, b]) => W.push({ kind: 'feed', wl: w, a: a.id, b: b.id, pts: ortho(a.p, b.p) }));
  }
  for (const c of J.circuits) {
    const pts = c.lights.filter(l => d.L[l]).map(l => ({ id: l, p: LP(l) }));
    mst(pts).forEach(([a, b]) => W.push({ kind: 'chain', c: c.id, wl: c.wl, pts: ortho(a.p, b.p) }));
    const xs = d.ctrls[c.id].filter(x => x.F === F);
    for (const x of xs) {
      const p = d.P[x.plate], m = [p.x, p.y];
      if (!pts.length) continue;
      const t = pts.reduce((a, n) => dist(n.p, m) < dist(a.p, m) ? n : a);
      W.push({ kind: 'drop', c: c.id, wl: c.wl, plate: x.plate, key: x.key, pts: orthoClear(m, t.p, J.lights.filter(l => l.id !== t.id).map(l => [l.x, l.y])) });
    }
    for (let i = 0; i + 1 < xs.length; i++) if (xs[i].plate !== xs[i + 1].plate) {
      const a = d.P[xs[i].plate], b = d.P[xs[i + 1].plate];
      W.push({ kind: 'strap', c: c.id, wl: c.wl, pts: [[a.x, a.y], [b.x, b.y]], n: xs.length });
    }
    for (const ds of J.door_switches.filter(ds => ds.circuit === c.id)) if (pts.length) {
      const t = pts.reduce((a, n) => dist(n.p, [ds.x, ds.y]) < dist(a.p, [ds.x, ds.y]) ? n : a);
      W.push({ kind: 'mk', c: c.id, wl: c.wl, pts: ortho([ds.x, ds.y], t.p) });
    }
  }
  for (const p of J.plates) for (const k of p.keys) {
    const sk = J.special_keys[k];
    if (sk?.link) W.push({ kind: 'riser', plate: p.id, key: k, link: sk.link, wl: S[sk.link.floor]?.circuits.find(c => c.id === sk.link.circuit)?.wl, pts: [[p.x, p.y], [p.x, p.y - 0.6 * M(F)]] });
  }
  W.forEach((w, i) => w.i = i);
}
function feedPath(F, w, targets) {   // edges of the WL tree from AL1 to the given plates
  const E = D[F].wires.filter(x => x.kind === 'feed' && x.wl === w), adj = {};
  E.forEach(e => { (adj[e.a] = adj[e.a] || []).push([e.b, e]); (adj[e.b] = adj[e.b] || []).push([e.a, e]); });
  const prev = { AL1: null }, q = ['AL1'];
  while (q.length) { const u = q.shift(); for (const [v, e] of adj[u] || []) if (!(v in prev)) { prev[v] = [u, e]; q.push(v); } }
  const out = new Set();
  for (const t of targets) { let u = t; while (prev[u]) { out.add(prev[u][1].i); u = prev[u][0]; } }
  return out;
}

/* ---------------- rule checks ---------------- */
function checks() {
  ISS = [];
  const I = (sev, F, msg, tgt) => ISS.push({ sev, F, msg, tgt });
  for (const F of FLOORS) {
    const J = S[F], d = D[F], m = M(F), G = GEO[F];
    const ids = {};
    J.plates.forEach(p => { if (ids[p.id]) I('error', F, `开关编号重复：${p.id}`, { k: 'plate', id: p.id }); ids[p.id] = 1; });
    for (const l of J.lights) if (!d.lightCirc[l.id]) I('error', F, `灯没有开关：${short(l.id)}（${d.room[l.id]}）`, { k: 'lamp', id: l.id });
    for (const c of J.circuits) {
      const xs = d.ctrls[c.id], nd = J.door_switches.filter(x => x.circuit === c.id).length;
      if (!c.lights.length) I('error', F, `回路 ${c.letter} 没有灯`, { k: 'circ', id: c.id });
      if (!xs.length && !nd) I('error', F, `回路 ${c.letter}（${c.name}）没有开关`, { k: 'circ', id: c.id, hard: false });
      xs.filter(x => x.broken).forEach(x => I('error', F, `回路 ${c.letter} 的跨层控制点 ${FCN[x.F]} ${x.plate} 键 ${x.key} 不存在`, { k: 'circ', id: c.id, hard: true }));
      if (!c.wl || !J.wl[c.wl]) I('error', F, `回路 ${c.letter} 没有分配 WL`, { k: 'circ', id: c.id, hard: true });
      const mid = xs.filter(x => x.middle).length, need = Math.max(0, xs.length - 2);
      if (mid < need) I('warn', F, `回路 ${c.letter} 是${modeName(xs.length)}，缺中途开关（需 ${need} 只，现 ${mid}）`, { k: 'circ', id: c.id, fix: 'middle' });
      if (mid > need) I('warn', F, `回路 ${c.letter} 是${modeName(xs.length)}，多了中途开关`, { k: 'circ', id: c.id });
      if (c.lights.length > 0 && J.lights.filter(l => c.lights.includes(l.id)).some(l => l.outdoor) && J.lights.filter(l => c.lights.includes(l.id)).some(l => !l.outdoor))
        I('info', F, `回路 ${c.letter} 户内、户外灯混在一起`, { k: 'circ', id: c.id });
    }
    for (const p of J.plates) for (const k of p.keys) if (!d.keyCirc[k] && !J.special_keys[k])
      I('warn', F, `${p.id} 键 ${p.keys.indexOf(k) + 1}（原 ${k}）没有控制任何灯`, { k: 'key', id: p.id, key: k });
    for (const ds of J.door_switches) if (!d.C[ds.circuit]) I('error', F, `门控开关 ${ds.id} 没有连到回路`, { k: 'mk', id: ds.id, hard: true });
    for (const [k, sk] of Object.entries(J.special_keys)) if (sk.link) {
      const c = S[sk.link.floor]?.circuits.find(x => x.id === sk.link.circuit);
      if (!c) I('error', F, `键 ${k} 的跨层回路 ${FCN[sk.link.floor]} ${sk.link.circuit} 不存在`, { k: 'key', id: (J.plates.find(p => p.keys.includes(k)) || {}).id, key: k, hard: true });
    }
    // bathrooms: FI isolator beside the light switch or in the room
    const baths = {};
    for (const l of J.lights) if (BATH.test(d.room[l.id])) { const ri = G.roomAt(l.x, l.y); (baths[ri] = baths[ri] || []).push(l); }
    for (const [ri, ls] of Object.entries(baths)) {
      if (J.meta.fan_isolator === false) { ls.filter(l => ipOf(F, l) < 44).forEach(l => I('warn', F, `卫生间灯 ${short(l.id)} 防护等级 ${ipStr(F, l)}，应 ≥ IP44`, { k: 'lamp', id: l.id })); continue; }
      const ctrlPlates = ls.flatMap(l => (d.ctrls[d.lightCirc[l.id]] || []).filter(x => x.F === F).map(x => d.P[x.plate]));
      const ok = J.plates.some(p => p.gangs === 0 && (G.roomAt(p.x, p.y) === +ri || ctrlPlates.some(q => dist([p.x, p.y], [q.x, q.y]) < 1.0 * m)));
      if (!ok) I('warn', F, `${J.rooms[ri]?.name || '卫生间'}（${ls.map(l => d.lightCirc[l.id] ? d.C[d.lightCirc[l.id]].letter : '?').join('')}）缺排气扇隔离开关 FI`, { k: 'lamp', id: ls[0].id });
      ls.filter(l => ipOf(F, l) < 44).forEach(l => I('warn', F, `卫生间灯 ${short(l.id)} 防护等级 ${ipStr(F, l)}，应 ≥ IP44`, { k: 'lamp', id: l.id }));
    }
    J.lights.filter(l => l.outdoor && ipOf(F, l) < 65).forEach(l => I('warn', F, `户外灯 ${short(l.id)} 防护等级 ${ipStr(F, l)}，应 ≥ IP65`, { k: 'lamp', id: l.id }));
    // switch position: on a wall, lock side of the nearest door, ~150 mm from the frame
    for (const p of J.plates) {
      const pt = [p.x, p.y], w = wallNear(G, pt);
      if (w.d > 0.15 * m) I('info', F, `${p.id} 不在墙上（离墙 ${(w.d / m).toFixed(2)} m）`, { k: 'plate', id: p.id });
      let dr = null;
      for (const o of G.doors) { const dd = Math.min(dist(pt, o.hinge), dist(pt, o.lock)); if (dd < 1.0 * m && (!dr || dd < dr.d)) dr = { d: dd, o }; }
      if (dr) {
        const o = dr.o, along = dot(sub(pt, o.lock), o.e);
        if (dist(pt, o.hinge) < dist(pt, o.lock)) I('warn', F, `${p.id} 在门的合页侧（应在锁侧）`, { k: 'plate', id: p.id });
        else if (along > 0.4 * m) I('info', F, `${p.id} 离门框 ${(along / m).toFixed(2)} m（建议 0.15 m）`, { k: 'plate', id: p.id });
      }
      if (!p.sheet) I('warn', F, `${p.id} 不在任何分区放大图范围内`, { k: 'plate', id: p.id });
    }
    // WL load
    for (const [w, def] of Object.entries(J.wl)) {
      const W = wlWatts(F, w), lim = /C10/.test(def.br) ? 2300 : /B6|C6/.test(def.br) ? 1380 : 3680;
      if (W > 0.8 * lim) I('warn', F, `${w} 估算 ${W} W，超过 ${def.br} 的 80%`, { k: 'wl', id: w });
      if (!J.circuits.some(c => c.wl === w)) I('info', F, `${w} 没有回路`, { k: 'wl', id: w });
    }
  }
  const order = { error: 0, warn: 1, info: 2 };
  ISS.sort((a, b) => order[a.sev] - order[b.sev]);
}
const ipDefault = (F, l) => l.outdoor ? 'IP65' : BATH.test(D[F].room[l.id]) ? 'IP44' : 'IP20';
const ipStr = (F, l) => l.ip || ipDefault(F, l);
const ipOf = (F, l) => parseInt(ipStr(F, l).replace(/\D/g, ''), 10) || 0;
const wlLights = (F, w) => S[F].circuits.filter(c => c.wl === w).flatMap(c => c.lights.map(id => D[F].L[id])).filter(Boolean);
const wlWatts = (F, w) => wlLights(F, w).reduce((a, l) => a + (WATT[l.kind] || 10), 0);
const short = id => id.replace(/^(射灯|主灯位待选|主灯|壁灯|地灯) /, '').replace(/^GU10_(GF|FF)_/, 'GU10 ').replace('主灯待选_', '待选 ');

/* ---------------- editing ---------------- */
function commit(label) { hist.undo.push(JSON.stringify(S)); if (hist.undo.length > 200) hist.undo.shift(); hist.redo = []; if (label) toast(label); }
function undo() { if (!hist.undo.length) return; hist.redo.push(JSON.stringify(S)); S = JSON.parse(hist.undo.pop()); afterLoad(); }
function redo() { if (!hist.redo.length) return; hist.undo.push(JSON.stringify(S)); S = JSON.parse(hist.redo.pop()); afterLoad(); }
function afterLoad() { if (ui.sel && !findSel()) ui.sel = null; ui.ak = null; derive(); render(); }
function findSel() { const s = ui.sel; if (!s) return null; if (s.k === 'plate') return S[s.F].plates.find(p => p.id === s.id); if (s.k === 'mk') return S[s.F].door_switches.find(p => p.id === s.id); if (s.k === 'lamp') return D[s.F]?.L[s.id]; return s; }

function nextKey(F) {
  let n = 0;
  const J = S[F];
  for (const k of [...J.plates.flatMap(p => p.keys), ...Object.keys(J.special_keys), ...J.fcus.map(f => f.key)]) if (/^\d+$/.test(k)) n = Math.max(n, +k);
  return () => String(++n);
}
function nextPlateId(F) { let n = 0; for (const p of S[F].plates) { const v = parseInt(p.id.replace(/\D/g, ''), 10); if (v > n) n = v; } return 'S' + (n + 1); }
function sheetOf(F, x, y) {
  const u = S[F].units.emu_per_px, px = x / u, py = y / u;
  for (const [z, v] of Object.entries(S[F].zones)) { const [a, b, c, d] = v.member; if (px >= a && px <= c && py >= b && py <= d) return +z; }
  return 0;
}
function snap(F, p, free) {
  if (free) return { p, how: '自由' };
  const m = M(F), G = GEO[F];
  let best = null;
  for (const o of G.doors) { const dd = dist(p, o.lock); if (dd < 0.8 * m && (!best || dd < best.d)) best = { d: dd, o }; }
  if (best) {
    const o = best.o, side = Math.sign(dot(sub(p, o.lock), o.n)) || 1;
    const q0 = add(o.lock, mul(o.e, 0.18 * m)), tgt = add(q0, mul(o.n, side * 0.3 * m)), w = wallNear(G, tgt);
    return { p: add(w.q, mul(norm(sub(tgt, w.q)), 0.03 * m)), how: '门锁侧 150 mm', door: o };
  }
  const w = wallNear(G, p);
  if (w.d < 0.5 * m) return { p: w.d > 1 ? add(w.q, mul(norm(sub(p, w.q)), 0.03 * m)) : p, how: '贴墙' };
  return { p, how: '未吸附（离墙 > 0.5 m）' };
}
const GNAME = { 0: '风扇隔离开关', 1: '单联开关', 2: '双联开关', 3: '三联开关', 4: '四联开关' };
function placePlate(F, raw, type, free) {
  const s = snap(F, raw, free), J = S[F], nk = nextKey(F), room = roomName(F, ...s.p);
  commit();
  if (type === 'MK') {
    let n = 1; while (J.door_switches.some(d => d.id === (n === 1 ? 'MK' : 'MK' + n))) n++;
    const id = n === 1 ? 'MK' : 'MK' + n;
    J.door_switches.push({ id, x: Math.round(s.p[0]), y: Math.round(s.p[1]), sheet: sheetOf(F, ...s.p), circuit: null, location: `${room}门框锁侧`, label: `${room}门控开关`, parallel: '', schedule: '' });
    ui.sel = { k: 'mk', F, id }; ui.ak = { F, mk: id };
    toast(`放置 ${id}（${s.how}）→ 再点一盏灯，把门控并联到它的回路`);
  } else {
    const g = type === 'FI' ? 0 : +type, id = nextPlateId(F), keys = Array.from({ length: Math.max(g, 1) }, () => nk());
    const p = { id, panel: `${GNAME[g]} 新${id}`, gangs: g, keys, x: Math.round(s.p[0]), y: Math.round(s.p[1]), location: `${room} · ${s.door ? '门旁（锁侧）' : '墙面'}`, sheet: sheetOf(F, ...s.p), middle_keys: [] };
    if (g === 0) J.special_keys[keys[0]] = { text: `${room}排气扇（FI）`, tag: 'FI', fan: true };
    J.plates.push(p);
    ui.sel = { k: 'plate', F, id }; ui.ak = g ? { F, plate: id, key: keys[0] } : null;
    toast(`放置 ${id} ${g ? g + ' 联' : 'FI'}（${s.how}）${g ? ' → 已选中键 1，点灯建立控制关系' : ''}`);
  }
  derive(); render();
}
function deletePlate(F, id) {
  const J = S[F], p = J.plates.find(x => x.id === id); if (!p) return;
  commit(`删除 ${id}`);
  J.plates = J.plates.filter(x => x !== p);
  for (const k of p.keys) {
    if (J.plates.some(x => x.keys.includes(k))) continue;
    J.circuits.forEach(c => c.keys = c.keys.filter(x => x !== k));
    dropSpecial(F, k);
  }
  for (const G of FLOORS) S[G].circuits.forEach(c => { if (c.remote_links) { c.remote_links = c.remote_links.filter(r => !(r.floor === F && r.plate === id)); syncRemote(G, c); } });
  ui.sel = null; ui.ak = null; derive(); render();
}
function dropSpecial(F, k) {
  const sk = S[F].special_keys[k]; if (!sk) return;
  if (sk.link) { const c = S[sk.link.floor]?.circuits.find(x => x.id === sk.link.circuit); if (c) { c.remote_links = (c.remote_links || []).filter(r => !(r.floor === F && r.key === k)); syncRemote(sk.link.floor, c); } }
  delete S[F].special_keys[k];
}
function syncRemote(F, c) {
  if (!c.remote_links) return;
  if (!c.remote_links.length) { delete c.remote_links; delete c.remote; return; }
  c.remote = c.remote_links.map(r => `${FCN[r.floor]} ${r.plate}`);
}
function newCircuit(F, lights) {
  const J = S[F], used = new Set(J.circuits.map(c => c.letter));
  const letter = [...LETTERS].find(l => !used.has(l)) || '?';
  let n = 0; J.circuits.forEach(c => { const v = parseInt(c.id.replace(/\D/g, ''), 10); if (v > n) n = v; });
  const rooms = [...new Set(lights.map(l => D[F].room[l]))], kinds = {};
  lights.forEach(l => { const k = D[F].L[l].kind; kinds[k] = (kinds[k] || 0) + 1; });
  const wlCount = {};
  J.circuits.forEach(c => { if (c.lights.some(l => rooms.includes(D[F].room[l]))) wlCount[c.wl] = (wlCount[c.wl] || 0) + 1; });
  const wl = Object.entries(wlCount).sort((a, b) => b[1] - a[1])[0]?.[0] || Object.keys(J.wl)[0];
  const c = { id: 'L' + (n + 1), letter, name: `${rooms.join('/')} ${Object.entries(kinds).map(([k, v]) => k + (v > 1 ? ' ×' + v : '')).join(' + ')}`, keys: [], lights: [], wl };
  J.circuits.push(c); return c;
}
function takeLight(F, id) {   // remove a lamp from its circuit; a circuit left without lamps disappears
  const J = S[F];
  for (const c of J.circuits) if (c.lights.includes(id)) c.lights = c.lights.filter(x => x !== id);
  const gone = J.circuits.filter(c => !c.lights.length);
  if (gone.length) {
    J.circuits = J.circuits.filter(c => c.lights.length);
    for (const c of gone) { J.door_switches.forEach(ds => { if (ds.circuit === c.id) ds.circuit = null; });
      for (const G of FLOORS) for (const [k, sk] of Object.entries(S[G].special_keys)) if (sk.link && sk.link.floor === F && sk.link.circuit === c.id) delete S[G].special_keys[k]; }
  }
}
function unlinkKey(F, plate, key) {
  commit();
  S[F].circuits.forEach(c => c.keys = c.keys.filter(k => k !== key));
  const p = S[F].plates.find(x => x.id === plate); if (p) p.middle_keys = (p.middle_keys || []).filter(k => k !== key);
  if (S[F].special_keys[key] && !S[F].special_keys[key].fan) dropSpecial(F, key);
  toast(`${plate} 键 ${p ? p.keys.indexOf(key) + 1 : ''} 已解除`); derive(); render();
}
// link the active key (or MK) to lamps; cross-floor if the key sits on the other floor
function linkLights(FL, ids) {
  const ak = ui.ak; if (!ak || !ids.length) return;
  commit();
  const J = S[FL], d = D[FL];
  let msg = '';
  if (ak.mk) {
    const ds = S[ak.F].door_switches.find(x => x.id === ak.mk);
    if (ak.F !== FL) { toast('门控开关只能连本层的灯'); hist.undo.pop(); return; }
    let c = d.C[d.lightCirc[ids[0]]];
    if (!c) { c = newCircuit(FL, []); ids.forEach(i => { takeLight(FL, i); c.lights.push(i); }); }
    ds.circuit = c.id;
    const x = d.ctrls[c.id]?.[0];
    ds.parallel = x ? `${x.plate} 键 ${x.gang}` : '';
    ds.schedule = `${c.letter} ${c.name}${ds.parallel ? `（与 ${ds.parallel} 并联）` : ''}`;
    msg = `${ds.id} 并联到回路 ${c.letter}`;
  } else if (ak.F !== FL) {   // cross-floor: the key controls a circuit on the other floor
    let c = d.C[d.lightCirc[ids[0]]];
    if (!c) { c = newCircuit(FL, []); ids.forEach(i => { takeLight(FL, i); c.lights.push(i); }); }
    S[ak.F].circuits.forEach(x => x.keys = x.keys.filter(k => k !== ak.key));
    c.remote_links = c.remote_links || [];
    if (c.remote_links.some(r => r.floor === ak.F && r.plate === ak.plate && r.key === ak.key)) {
      c.remote_links = c.remote_links.filter(r => !(r.floor === ak.F && r.plate === ak.plate && r.key === ak.key));
      delete S[ak.F].special_keys[ak.key]; msg = `解除跨层控制 ${ak.plate} → ${c.letter}`;
    } else {
      c.remote_links.push({ floor: ak.F, plate: ak.plate, key: ak.key });
      const tag = short(c.lights[0] || '').split(' ')[0];
      S[ak.F].special_keys[ak.key] = { text: `${FCN[FL]}${c.name}（跨层控制，回路 ${c.letter}）`, tag, riser: `↑ 引至${FCN[FL]} ${tag}`, link: { floor: FL, circuit: c.id } };
      msg = `${FCN[ak.F]} ${ak.plate} 跨层控制 ${FCN[FL]} 回路 ${c.letter}`;
    }
    syncRemote(FL, c);
  } else {
    dropSpecial(FL, ak.key);
    const kc = d.C[d.keyCirc[ak.key]];
    const lc = ids.map(i => d.lightCirc[i]);
    if (!kc) {
      const same = lc[0] && lc.every(x => x === lc[0]) && (ids.length === 1 || d.C[lc[0]].lights.length === ids.length);
      if (same) { d.C[lc[0]].keys.push(ak.key); const c = d.C[lc[0]]; msg = `${ak.plate} 加入回路 ${c.letter} → ${modeName(controlsOf(FL, c).length)}`; }
      else { const c = newCircuit(FL, ids); ids.forEach(i => { takeLight(FL, i); c.lights.push(i); }); c.keys.push(ak.key); msg = `新回路 ${c.letter}：${ids.length} 盏灯`; }
    } else if (ids.length === 1 && lc[0] === kc.id) {
      takeLight(FL, ids[0]); msg = `从回路 ${kc.letter} 移除 ${short(ids[0])}`;
      if (!S[FL].circuits.includes(kc)) msg += `（回路 ${kc.letter} 已无灯，删除）`;
    } else {
      ids.filter(i => d.lightCirc[i] !== kc.id).forEach(i => { takeLight(FL, i); kc.lights.push(i); });
      msg = `回路 ${kc.letter} 现在 ${kc.lights.length} 盏灯`;
    }
  }
  derive(); render(); toast(msg);
}
function autoMiddle(F, cid) {
  const c = D[F].C[cid], xs = D[F].ctrls[cid], need = xs.length - 2;
  if (need < 1) return;
  commit();
  const loc = xs.filter(x => !x.middle);
  const pt = x => { const p = S[x.F].plates.find(q => q.id === x.plate); return [p.x, p.y]; };
  const score = x => { const o = loc.filter(y => y !== x && y.F === x.F); return o.length < 2 ? Infinity : dist(pt(o[0]), pt(x)) + dist(pt(x), pt(o[1])) - dist(pt(o[0]), pt(o[1])); };
  const pick = loc.filter(x => x.F === F || x.remote).sort((a, b) => score(a) - score(b)).slice(0, need - xs.filter(x => x.middle).length);
  pick.forEach(x => { const p = S[x.F].plates.find(q => q.id === x.plate); p.middle_keys = [...new Set([...(p.middle_keys || []), x.key])]; });
  derive(); render(); toast(`中途开关：${pick.map(x => x.plate).join('、')}`);
}

/* ---------------- plan rendering ---------------- */
class Pane {
  constructor(F, host) {
    this.F = F; const J = S[F]; this.vb = [...J.units.view_box];
    this.el = document.createElement('div'); this.el.className = 'pane'; host.appendChild(this.el);
    this.el.innerHTML = `<div class="ttl">${FCN[F]}平面</div><div class="zb"><button data-z="in" title="放大">＋</button><button data-z="out" title="缩小">－</button><button data-z="fit" title="全图" style="width:44px;font-size:12px">复位</button></div>`;
    this.el.querySelector('.zb').addEventListener('click', e => { const z = e.target.dataset.z; if (!z) return;
      if (z === 'fit') { this.vb = [...S[F].units.view_box]; this.setVB(); return; }
      const k = z === 'in' ? 1 / 1.4 : 1.4, c = [this.vb[0] + this.vb[2] / 2, this.vb[1] + this.vb[3] / 2];
      this.vb = [c[0] - this.vb[2] * k / 2, c[1] - this.vb[3] * k / 2, this.vb[2] * k, this.vb[3] * k]; this.setVB(); });
    const ns = 'http://www.w3.org/2000/svg';
    this.svg = document.createElementNS(ns, 'svg'); this.svg.setAttribute('class', 'plan p-' + F); this.el.appendChild(this.svg);
    const m = M(F);
    const inner = SVGSRC[F].replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '');
    this.svg.innerHTML = `<defs><radialGradient id="glow${F}"><stop offset="0" stop-color="#ffe066" stop-opacity=".95"/><stop offset=".45" stop-color="#ffd43b" stop-opacity=".45"/><stop offset="1" stop-color="#ffd43b" stop-opacity="0"/></radialGradient></defs>
      <style>.p-${F} .live{stroke-dasharray:${0.16 * m} ${0.1 * m};animation:flow${F} .9s linear infinite}@keyframes flow${F}{to{stroke-dashoffset:${-0.52 * m}}}.p-${F} .fanspin{animation:spin 1.2s linear infinite;transform-box:fill-box;transform-origin:center}</style>
      <rect x="-1e9" y="-1e9" width="2e9" height="2e9" fill="#fff" data-bg="1"/><g class="base">${inner}</g><g class="ov"></g>`;
    this.ov = this.svg.querySelector('.ov');
    this.setVB(); this.events();
  }
  setVB() { this.svg.setAttribute('viewBox', this.vb.join(' ')); }
  pt(ev) { const p = this.svg.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY; const q = p.matrixTransform(this.svg.getScreenCTM().inverse()); return [q.x, q.y]; }
  zoomTo(p, w) { const r = this.vb[3] / this.vb[2]; this.vb = [p[0] - w / 2, p[1] - w * r / 2, w, w * r]; this.setVB(); }
  events() {
    const svg = this.svg, F = this.F;
    svg.addEventListener('wheel', ev => {
      ev.preventDefault(); const p = this.pt(ev), k = ev.deltaY > 0 ? 1.15 : 1 / 1.15;
      this.vb = [p[0] - (p[0] - this.vb[0]) * k, p[1] - (p[1] - this.vb[1]) * k, this.vb[2] * k, this.vb[3] * k]; this.setVB();
    }, { passive: false });
    const touches = new Map();
    svg.addEventListener('pointerdown', ev => { if (ev.pointerType === 'touch') touches.set(ev.pointerId, [ev.clientX, ev.clientY]); }, true);
    svg.addEventListener('pointermove', ev => {
      if (!touches.has(ev.pointerId)) return;
      const prev = [...touches.values()]; touches.set(ev.pointerId, [ev.clientX, ev.clientY]);
      if (touches.size !== 2) return;
      const now = [...touches.values()], d0 = Math.hypot(prev[0][0] - prev[1][0], prev[0][1] - prev[1][1]), d1 = Math.hypot(now[0][0] - now[1][0], now[0][1] - now[1][1]);
      if (!d0 || !d1) return;
      const mid = this.pt({ clientX: (now[0][0] + now[1][0]) / 2, clientY: (now[0][1] + now[1][1]) / 2 }), k = d0 / d1;
      this.vb = [mid[0] - (mid[0] - this.vb[0]) * k, mid[1] - (mid[1] - this.vb[1]) * k, this.vb[2] * k, this.vb[3] * k]; this.setVB(); this.pinching = true;
    }, true);
    const lift = ev => { touches.delete(ev.pointerId); if (!touches.size) this.pinching = false; };
    svg.addEventListener('pointerup', lift, true); svg.addEventListener('pointercancel', lift, true);
    svg.addEventListener('pointerdown', ev => {
      if (ev.button === 1 || ev.button === 2) return this.startPan(ev);
      if (touches.size > 1) return;
      const t = ev.target.closest('[data-k]'), p = this.pt(ev);
      const k = t?.dataset.k, id = t?.dataset.id;
      if (ui.mode === 'sim') {
        if (k === 'key') { const s = kid(t.dataset.f, t.dataset.plate, t.dataset.key); sim.key[s] = !sim.key[s]; render(); return; }
        if (k === 'mk') { const s = F + '|' + id; sim.door[s] = !sim.door[s]; render(); return; }
        if (k === 'lamp') { ui.trace = { F, light: id, c: D[F].lightCirc[id] }; ui.tab = 'info'; render(); return; }
        if (k === 'board') { ui.tab = 'wl'; render(); return; }
        if (ui.trace) { ui.trace = null; render(); }
        return this.startPan(ev);
      }
      // edit mode
      if (k === 'key') { const a = { F: t.dataset.f, plate: t.dataset.plate, key: t.dataset.key };
        ui.ak = ui.ak && ui.ak.plate === a.plate && ui.ak.key === a.key && ui.ak.F === a.F ? null : a; ui.sel = { k: 'plate', F, id: a.plate }; ui.tab = 'info'; render(); return this.startDrag(ev, 'plate', a.plate, p); }
      if (k === 'plate') { ui.sel = { k: 'plate', F, id }; ui.tab = 'info'; render(); return this.startDrag(ev, 'plate', id, p); }
      if (k === 'mk') { ui.sel = { k: 'mk', F, id }; ui.ak = { F, mk: id }; ui.tab = 'info'; render(); return this.startDrag(ev, 'mk', id, p); }
      if (k === 'board') { return this.startDrag(ev, 'board', 'AL1', p); }
      if (k === 'lamp') { if (ui.ak) linkLights(F, [id]); else { ui.sel = { k: 'lamp', F, id }; ui.tab = 'info'; render(); } return; }
      if (ui.tool === 'place' && ev.button === 0) { placePlate(F, p, $('#placetype').value, ev.altKey); return; }
      if (ev.shiftKey && ui.ak) return this.startBox(ev, p);
      if (!ev.shiftKey) { ui.sel = null; render(); }
      this.startPan(ev);
    });
    svg.addEventListener('pointermove', ev => {
      if (ui.mode === 'edit' && ui.tool === 'place' && !this.op) { const s = snap(F, this.pt(ev), ev.altKey); ui.snapHint = { F, p: s.p, how: s.how }; this.drawHint(); foot(`放开关：${s.how}（按住 Alt 不吸附）· ${roomName(F, ...s.p)}`); }
    });
    svg.addEventListener('pointerleave', () => { if (ui.snapHint) { ui.snapHint = null; this.drawHint(); } });
    svg.addEventListener('contextmenu', ev => ev.preventDefault());
  }
  capture(ev, move, up) {
    this.op = true; this.svg.setPointerCapture(ev.pointerId);
    const mv = e => move(e), u = e => { this.svg.removeEventListener('pointermove', mv); this.svg.removeEventListener('pointerup', u); this.op = false; up && up(e); };
    this.svg.addEventListener('pointermove', mv); this.svg.addEventListener('pointerup', u);
  }
  startPan(ev) {
    const x0 = ev.clientX, y0 = ev.clientY, vb0 = [...this.vb], r = this.svg.getBoundingClientRect(), k = Math.max(vb0[2] / r.width, vb0[3] / r.height);
    this.capture(ev, e => { if (this.pinching) return; this.vb = [vb0[0] - (e.clientX - x0) * k, vb0[1] - (e.clientY - y0) * k, vb0[2], vb0[3]]; this.setVB(); });
  }
  startDrag(ev, kind, id, p0) {
    const F = this.F, J = S[F];
    const obj = kind === 'plate' ? J.plates.find(x => x.id === id) : kind === 'mk' ? J.door_switches.find(x => x.id === id) : J.board;
    const o0 = [obj.x, obj.y]; let moved = false, snapped = null;
    this.capture(ev, e => {
      const p = this.pt(e), dp = sub(p, p0);
      if (!moved && Math.hypot(...dp) < 0.08 * M(F)) return;
      if (!moved) { commit(); moved = true; }
      const raw = add(o0, dp), s = kind === 'board' ? { p: raw, how: '' } : snap(F, raw, e.altKey);
      snapped = s; obj.x = Math.round(s.p[0]); obj.y = Math.round(s.p[1]);
      derive(); render(); foot(`移动 ${id}：${s.how}（Alt = 不吸附）`);
    }, () => {
      if (moved && kind !== 'board') { obj.sheet = sheetOf(F, obj.x, obj.y); if (kind === 'plate' && snapped) obj.location = obj.location; derive(); render(); toast(`${id} → ${snapped?.how || ''}，${roomName(F, obj.x, obj.y)}`); }
    });
  }
  startBox(ev, p0) {
    const F = this.F;
    this.capture(ev, e => { ui.box = { F, a: p0, b: this.pt(e) }; this.drawHint(); }, () => {
      const b = ui.box; ui.box = null; this.drawHint(); if (!b) return;
      const [x0, x1] = [Math.min(b.a[0], b.b[0]), Math.max(b.a[0], b.b[0])], [y0, y1] = [Math.min(b.a[1], b.b[1]), Math.max(b.a[1], b.b[1])];
      const ids = S[F].lights.filter(l => l.x >= x0 && l.x <= x1 && l.y >= y0 && l.y <= y1).map(l => l.id);
      if (ids.length) linkLights(F, ids);
    });
  }
  drawHint() {
    let h = this.svg.querySelector('.hint'); if (!h) { h = document.createElementNS('http://www.w3.org/2000/svg', 'g'); h.setAttribute('class', 'hint'); this.svg.appendChild(h); }
    const m = M(this.F); let s = '';
    if (ui.snapHint && ui.snapHint.F === this.F) { const [x, y] = ui.snapHint.p; s += `<circle cx="${x}" cy="${y}" r="${0.1 * m}" fill="none" stroke="#1f4e79" stroke-width="${0.02 * m}"/><path d="M${x - 0.18 * m} ${y}H${x + 0.18 * m}M${x} ${y - 0.18 * m}V${y + 0.18 * m}" stroke="#1f4e79" stroke-width="${0.012 * m}"/>`; }
    if (ui.box && ui.box.F === this.F) { const { a, b } = ui.box; s += `<rect x="${Math.min(a[0], b[0])}" y="${Math.min(a[1], b[1])}" width="${Math.abs(a[0] - b[0])}" height="${Math.abs(a[1] - b[1])}" fill="rgba(31,78,121,.08)" stroke="#1f4e79" stroke-dasharray="${0.08 * m}" stroke-width="${0.015 * m}"/>`; }
    h.innerHTML = s;
  }
  render() { this.ov.innerHTML = planOverlay(this.F); this.drawHint(); }
}

function txt(x, y, s, size, attrs = '') { return `<text transform="translate(${x} ${y}) scale(1000)" font-size="${size / 1000}" ${attrs}>${esc(s)}</text>`; }
function lampSym(l, r, on, F) {
  const st = `stroke="#222" stroke-width="${r * 0.12}"`, fill = on ? '#ffd54a' : '#fff', x = l.x, y = l.y;
  const X = k => `<path d="M${x - k} ${y - k}L${x + k} ${y + k}M${x - k} ${y + k}L${x + k} ${y - k}" ${st}/>`;
  if (l.kind === '主灯' || l.kind === '待选') return `<circle cx="${x}" cy="${y}" r="${1.25 * r}" fill="${fill}" ${st} ${l.kind === '待选' ? `stroke-dasharray="${r * 0.4}"` : ''}/>${X(r * 0.85)}`;
  if (l.kind === '筒灯') return `<circle cx="${x}" cy="${y}" r="${0.85 * r}" fill="${fill}" ${st}/><circle cx="${x}" cy="${y}" r="${0.25 * r}" fill="#222"/>`;
  if (l.kind === '壁灯') return `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" ${st}/><path d="M${x - r} ${y}A${r} ${r} 0 0 0 ${x + r} ${y}Z" fill="${on ? '#e0a800' : '#222'}"/>`;
  return `<circle cx="${x}" cy="${y}" r="${0.8 * r}" fill="${fill}" ${st}/><path d="M${x} ${y - 0.45 * r}L${x - 0.4 * r} ${y + 0.3 * r}L${x + 0.4 * r} ${y + 0.3 * r}Z" fill="#222"/>`;
}

function traceSet() {   // wires / lamps / plates belonging to the traced circuit
  const t = ui.trace; if (!t || !t.c) return null;
  const c = D[t.F].C[t.c]; if (!c) return null;
  const xs = D[t.F].ctrls[c.id], set = { wires: {}, lamps: new Set(c.lights.map(l => t.F + '|' + l)), plates: new Set(xs.map(x => x.F + '|' + x.plate)), F: t.F };
  for (const F of FLOORS) {
    set.wires[F] = new Set(D[F].wires.filter(w => (F === t.F && w.c === c.id) || (w.kind === 'riser' && w.link?.floor === t.F && w.link?.circuit === c.id)).map(w => w.i));
    const targets = xs.filter(x => x.F === F).map(x => x.plate);
    const wl = F === t.F ? c.wl : null;
    if (wl) feedPath(F, wl, targets).forEach(i => set.wires[F].add(i));
    else if (targets.length) {   // a control point on the other floor is fed by its own WL; show the feed to it
      const p = S[F].plates.find(q => q.id === targets[0]);
      const w2 = p && p.keys.map(k => D[F].C[D[F].keyCirc[k]]?.wl).find(Boolean);
      if (w2) feedPath(F, w2, targets).forEach(i => set.wires[F].add(i));
    }
  }
  return set;
}

function layoutPanels(F) {   // panel boxes beside their mounting dots, slid along the wall / flipped so they do not overlap
  const J = S[F], m = M(F), r = 0.11 * m, out = {}, placed = [];
  const lampBox = J.lights.map(l => [l.x - 1.3 * r, l.y - 1.3 * r, l.x + 1.3 * r, l.y + 1.3 * r]);
  for (const ds of J.door_switches) placed.push([ds.x - 0.24 * m, ds.y - 0.15 * m, ds.x + 0.24 * m, ds.y + 0.4 * m]);   // MK box + 门开/门关 text
  const hit = (a, b) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
  for (const p of J.plates) {
    const pt = [p.x, p.y], w = wallNear(GEO[F], pt);
    let dir = w.d > 0.01 * m ? norm(sub(pt, w.q)) : [0, -1];
    dir = Math.abs(dir[0]) > Math.abs(dir[1]) ? [Math.sign(dir[0]), 0] : [0, Math.sign(dir[1]) || -1];
    const n = p.keys.length, kw = 0.34 * m, kh = 0.44 * m, pw = n * kw + 0.08 * m, ph = kh + 0.08 * m;
    let best = null;
    for (const side of [1, -1]) for (const k of [0, 1, -1, 2, -2, 3, -3, 4, -4]) {
      const d = mul(dir, side), along = [Math.abs(d[1]), Math.abs(d[0])];
      const gap = 0.2 * m + 0.04 * m * Math.abs(k);
      const cx = p.x + d[0] * (pw / 2 + gap) + along[0] * k * 0.45 * m, cy = p.y + d[1] * (ph / 2 + gap) + along[1] * k * 0.45 * m;
      const box = [cx - pw / 2 - 0.02 * m, cy - ph / 2 - 0.02 * m, cx + pw / 2 + 0.02 * m, cy + ph / 2 + 0.02 * m];
      const cost = placed.filter(b => hit(b, box)).length * 10 + lampBox.filter(b => hit(b, box)).length + Math.abs(k) * 0.8 +(side < 0 ? 0.5 : 0);
      if (!best || cost < best.cost) best = { cost, cx, cy, box, dir: d };
      if (cost < 0.01) break;
    }
    placed.push(best.box);
    out[p.id] = { cx: best.cx, cy: best.cy, pw, ph, kw, kh, dir: best.dir };
  }
  return out;
}

function planOverlay(F) {
  const J = S[F], d = D[F], m = M(F), r = 0.11 * m, out = [], tr = traceSet(), dimW = i => tr && !tr.wires[F].has(i);
  const editing = ui.mode === 'edit';
  // feed stretches that carry current: AL1 -> each plate whose circuit is on (not the whole WL)
  const liveFeed = new Set();
  for (const wl of Object.keys(J.wl)) {
    const tg = new Set();
    for (const c of J.circuits) if (c.wl === wl && circuitOn(F, c)) d.ctrls[c.id].filter(x => x.F === F).forEach(x => tg.add(x.plate));
    if (tg.size) feedPath(F, wl, [...tg]).forEach(i => liveFeed.add(i));
  }
  // wires
  if (ui.wires) for (const w of d.wires) {
    const c = w.c && d.C[w.c], col = wlColor(w.wl), pts = w.pts.map(p => p.join(' ')).join(' L');
    let live = false, wd = 0.02 * m, dash = '', stroke = col, op = 1;
    if (w.kind === 'feed') { live = sim.brk[w.wl] !== false; wd = 0.05 * m; op = live ? .9 : .35; if (!live) stroke = '#999'; }
    else if (w.kind === 'chain' || w.kind === 'drop' || w.kind === 'mk') { live = c && circuitOn(F, c); wd = w.kind === 'chain' ? 0.028 * m : 0.02 * m; if (w.kind !== 'chain') dash = `stroke-dasharray="${0.05 * m} ${0.05 * m}"`; if (!live) { stroke = '#8a8f98'; op = .75; } }
    else if (w.kind === 'strap') { live = c && breakerOn(F, c); stroke = live ? '#c62828' : '#999'; wd = 0.03 * m; dash = `stroke-dasharray="${0.2 * m} ${0.08 * m}"`; }
    else if (w.kind === 'riser') { const lc = S[w.link.floor]?.circuits.find(x => x.id === w.link.circuit); live = lc && circuitOn(w.link.floor, lc); stroke = live ? wlColor(w.wl) : '#8a8f98'; wd = 0.025 * m; }
    const flowing = w.kind === 'feed' && live && liveFeed.has(w.i);
    const cls = [(live && w.kind !== 'feed' && w.kind !== 'strap') || flowing ? 'live' : '', dimW(w.i) ? 'dim' : ''].join(' ');
    out.push(`<path d="M${pts}" fill="none" stroke="${stroke}" stroke-width="${tr && tr.wires[F].has(w.i) ? wd * 1.8 : wd}" stroke-opacity="${op}" ${cls.includes('live') ? '' : dash} class="${cls}" stroke-linejoin="round"/>`);
    if (w.kind === 'riser') { const [x, y] = w.pts[1]; const lc = S[w.link.floor]?.circuits.find(x => x.id === w.link.circuit);
      out.push(`<path d="M${x - 0.08 * m} ${y + 0.12 * m}L${x} ${y}L${x + 0.08 * m} ${y + 0.12 * m}" fill="none" stroke="${stroke}" stroke-width="${wd}"/>` + txt(x + 0.1 * m, y, `${FCN[w.link.floor]} ${lc ? lc.letter : '?'}`, 0.18 * m, `fill="${stroke}" font-weight="bold"`)); }
    if (w.kind === 'strap' && !dimW(w.i)) { const [a, b] = w.pts, mid = add(a, mul(sub(b, a), .5)); out.push(txt(mid[0], mid[1] - 0.05 * m, w.n > 2 ? '三控联络' : '双控联络', 0.13 * m, `fill="${stroke}" text-anchor="middle"`)); }
  }
  // lamps
  for (const l of J.lights) {
    const cid = d.lightCirc[l.id], c = d.C[cid], on = c && circuitOn(F, c), dim = tr && !tr.lamps.has(F + '|' + l.id);
    const dead = !c || (!d.ctrls[c.id].length && !J.door_switches.some(ds => ds.circuit === c.id));
    out.push(`<g data-k="lamp" data-id="${esc(l.id)}" class="${dim ? 'dim' : ''}">`);
    if (on) out.push(`<circle cx="${l.x}" cy="${l.y}" r="${r * 4.2}" fill="url(#glow${F})" pointer-events="none"/>`);
    out.push(`<circle cx="${l.x}" cy="${l.y}" r="${r * 1.8}" fill="transparent"/>` + lampSym(l, r, on, F));
    out.push(txt(l.x + 1.1 * r, l.y - 1.3 * r, c ? c.letter : '?', 0.24 * m, `fill="${dead ? '#c62828' : wlColor(c.wl)}" font-weight="bold"`));
    if (dead && ui.issues) out.push(`<circle cx="${l.x}" cy="${l.y}" r="${r * 2.1}" fill="none" stroke="#c62828" stroke-width="${0.025 * m}" stroke-dasharray="${0.06 * m}"/>`);
    if (ui.sel?.k === 'lamp' && ui.sel.F === F && ui.sel.id === l.id) out.push(`<circle cx="${l.x}" cy="${l.y}" r="${r * 2.2}" fill="none" stroke="#1f4e79" stroke-width="${0.03 * m}"/>`);
    out.push('</g>');
  }
  // upstairs / downstairs lamps switched from this floor: ghost at the matching plan position, dashed link to the plate
  for (const [k, sk] of Object.entries(J.special_keys)) if (sk.ghost && sk.link) {
    const g = sk.ghost, lc = S[sk.link.floor]?.circuits.find(x => x.id === sk.link.circuit), on = lc && circuitOn(sk.link.floor, lc);
    const p = J.plates.find(q => q.keys.includes(k)), col = lc ? wlColor(lc.wl) : '#888';
    out.push(`<g data-k="ghost" opacity="${on ? 1 : 0.7}">`);
    if (p) out.push(`<path d="M${p.x} ${p.y}L${g.x} ${g.y}" fill="none" stroke="${col}" stroke-width="${0.015 * m}" stroke-dasharray="${0.03 * m} ${0.06 * m}"/>`);
    if (on) out.push(`<circle cx="${g.x}" cy="${g.y}" r="${r * 4.2}" fill="url(#glow${F})" pointer-events="none"/>`);
    out.push(`<circle cx="${g.x}" cy="${g.y}" r="${r * 1.9}" fill="none" stroke="${col}" stroke-width="${0.02 * m}" stroke-dasharray="${0.05 * m} ${0.04 * m}"/>` + lampSym({ id: g.light, kind: g.kind || '主灯', x: g.x, y: g.y }, r, on, F));
    out.push(txt(g.x + 2.1 * r, g.y + 0.06 * m, `${lc ? lc.letter : '?'}↑ ${g.label}`, 0.15 * m, `fill="${col}" font-weight="bold"`) + '</g>');
  }
  // board
  const b = J.board;
  out.push(`<g data-k="board"><rect x="${b.x - 0.28 * m}" y="${b.y - 0.13 * m}" width="${0.56 * m}" height="${0.26 * m}" fill="#fff" stroke="#111" stroke-width="${0.025 * m}"/><path d="M${b.x - 0.28 * m} ${b.y + 0.13 * m}L${b.x + 0.28 * m} ${b.y - 0.13 * m}L${b.x + 0.28 * m} ${b.y + 0.13 * m}Z" fill="#111"/>${txt(b.x, b.y + 0.36 * m, F === 'GF' ? 'AL1' : '↑ AL1 引上', 0.2 * m, 'text-anchor="middle" font-weight="bold"')}</g>`);
  // doors (edit mode): lock jamb
  if (editing) for (const o of GEO[F].doors) out.push(`<circle cx="${o.lock[0]}" cy="${o.lock[1]}" r="${0.05 * m}" fill="#2e7d32" opacity=".7"/><circle cx="${o.hinge[0]}" cy="${o.hinge[1]}" r="${0.04 * m}" fill="none" stroke="#8a6d3b" stroke-width="${0.012 * m}"/>`);
  // plates
  const issueAt = new Set(ISS.filter(i => i.F === F && (i.sev !== 'info') && i.tgt).map(i => i.tgt.k + '|' + (i.tgt.id || '')));
  const LAY = layoutPanels(F);
  for (const p of J.plates) {
    const { cx, cy, pw, ph, kw, kh, dir } = LAY[p.id];
    const dim = tr && !tr.plates.has(F + '|' + p.id), sel = ui.sel?.k === 'plate' && ui.sel.F === F && ui.sel.id === p.id;
    out.push(`<g class="${dim ? 'dim' : ''}">`);
    const ex = Math.max(cx - pw / 2, Math.min(p.x, cx + pw / 2)), ey = Math.max(cy - ph / 2, Math.min(p.y, cy + ph / 2));
    out.push(`<path d="M${p.x} ${p.y}L${ex} ${ey}" stroke="#c00000" stroke-width="${0.025 * m}"/>`);
    if (sel) out.push(`<rect x="${cx - pw / 2 - 0.06 * m}" y="${cy - ph / 2 - 0.06 * m}" width="${pw + 0.12 * m}" height="${ph + 0.12 * m}" rx="${0.06 * m}" fill="none" stroke="#1f4e79" stroke-width="${0.025 * m}" stroke-dasharray="${0.06 * m} ${0.04 * m}"/>`);
    out.push(`<circle cx="${p.x}" cy="${p.y}" r="${0.06 * m}" fill="#111" data-k="plate" data-id="${p.id}"/>`);
    out.push(`<rect x="${cx - pw / 2}" y="${cy - ph / 2}" width="${pw}" height="${ph}" rx="${0.04 * m}" fill="#5a4632" stroke="${issueAt.has('plate|' + p.id) && ui.issues ? '#e0a800' : '#3b2e22'}" stroke-width="${issueAt.has('plate|' + p.id) && ui.issues ? 0.03 * m : 0.015 * m}" data-k="plate" data-id="${p.id}"/>`);
    p.keys.forEach((k, i) => {
      const x = cx - pw / 2 + 0.04 * m + i * kw, y = cy - kh / 2, on = !!sim.key[kid(F, p.id, k)];
      const cid = d.keyCirc[k], c = d.C[cid], sk = J.special_keys[k];
      const lab = c ? c.letter : sk ? (sk.link ? (S[sk.link.floor]?.circuits.find(z => z.id === sk.link.circuit)?.letter || '?') + '↑' : sk.tag) : '–';
      const act = ui.ak && !ui.ak.mk && ui.ak.F === F && ui.ak.plate === p.id && ui.ak.key === k;
      const mid = (p.middle_keys || []).includes(k);
      const bad = !c && !sk;
      out.push(`<g data-k="key" data-f="${F}" data-plate="${p.id}" data-key="${esc(k)}">
        <rect x="${x + 0.015 * m}" y="${y}" width="${kw - 0.03 * m}" height="${kh}" rx="${0.03 * m}" fill="${act ? '#ffe08a' : on ? '#fff3bf' : '#efe9e1'}" stroke="${act ? '#1f4e79' : bad && ui.issues ? '#b7791f' : '#2b2118'}" stroke-width="${act ? 0.035 * m : 0.012 * m}"/>
        <rect x="${x + 0.04 * m}" y="${on ? y + kh * 0.55 : y + 0.03 * m}" width="${kw - 0.08 * m}" height="${kh * 0.4}" rx="${0.02 * m}" fill="${on ? '#e0a800' : '#b9ad9f'}"/>
        ${txt(x + kw / 2, on ? y + kh * 0.36 : y + kh * 0.8, lab, 0.24 * m, `text-anchor="middle" font-weight="bold" fill="${c ? wlColor(c.wl) : '#555'}"`)}
        ${mid ? txt(x + kw / 2, y - 0.05 * m, '中途', 0.13 * m, 'text-anchor="middle" fill="#c62828"') : ''}</g>`);
    });
    out.push(txt(cx, cy - dir[1] * 0 + (dir[1] > 0 ? ph / 2 + 0.28 * m : -ph / 2 - 0.1 * m), p.id, 0.26 * m, `text-anchor="middle" font-weight="bold" fill="#c00000" data-k="plate" data-id="${p.id}"`));
    if (p.gangs === 0 && d.fan[p.id]) {
      const run = sim.key[kid(F, p.id, p.keys[0])] && circuitOn(F, d.C[d.fan[p.id]]);
      const fx = cx + pw / 2 + 0.22 * m, fy = cy;
      out.push(`<g class="${run ? 'fanspin' : ''}"><circle cx="${fx}" cy="${fy}" r="${0.14 * m}" fill="#fff" stroke="#2e86ab" stroke-width="${0.015 * m}"/>${[0, 120, 240].map(a => `<path d="M${fx} ${fy}L${fx + 0.12 * m * Math.cos(a * Math.PI / 180)} ${fy + 0.12 * m * Math.sin(a * Math.PI / 180)}" stroke="${run ? '#2e86ab' : '#aaa'}" stroke-width="${0.035 * m}" stroke-linecap="round"/>`).join('')}</g>`);
    }
    out.push('</g>');
  }
  for (const ds of J.door_switches) {
    const open = !!sim.door[F + '|' + ds.id], sel = ui.sel?.k === 'mk' && ui.sel.F === F && ui.sel.id === ds.id;
    out.push(`<g data-k="mk" data-id="${ds.id}"><rect x="${ds.x - 0.2 * m}" y="${ds.y - 0.11 * m}" width="${0.4 * m}" height="${0.22 * m}" fill="${open ? '#fff3bf' : '#fff'}" stroke="${sel ? '#1f4e79' : '#111'}" stroke-width="${sel ? 0.04 * m : 0.015 * m}"/>${txt(ds.x, ds.y + 0.06 * m, ds.id, 0.15 * m, 'text-anchor="middle" font-weight="bold"')}${txt(ds.x, ds.y + 0.32 * m, open ? '门开' : '门关', 0.13 * m, 'text-anchor="middle" fill="#666"')}</g>`);
  }
  // issue markers on circuits' lamps (warn/error)
  return out.join('');
}

/* ---------------- schematic (电路图) ---------------- */
function renderSchem(host) {
  const el = document.createElement('div'); el.className = 'pane schem'; host.appendChild(el);
  const rows = [], X0 = 300, RH = 76;
  let y = 70;
  const all = [];
  for (const F of FLOORS) for (const [w, def] of Object.entries(S[F].wl)) all.push({ F, w, def });
  all.sort((a, b) => (parseInt(a.w.slice(2)) || 0) - (parseInt(b.w.slice(2)) || 0));
  const LIVE = '#e53935', DEAD = '#9aa3ad';
  const line = (pts, live, wd = 2, extra = '') => `<path d="M${pts.map(p => p.join(' ')).join(' L')}" fill="none" stroke="${live ? LIVE : DEAD}" stroke-width="${wd}" ${live ? 'class="slive"' : ''} ${extra}/>`;
  const tr = ui.trace;
  for (const { F, w, def } of all) {
    const on = sim.brk[w] !== false, col = wlColor(w);
    const cs = S[F].circuits.filter(c => c.wl === w);
    const top = y;
    rows.push(`<g data-k="brk" data-wl="${w}"><rect x="110" y="${y - 14}" width="52" height="28" rx="4" fill="${on ? '#fff' : '#eee'}" stroke="${col}" stroke-width="2"/>
      <path d="M118 ${y}L128 ${y}${on ? `L152 ${y}` : `L150 ${y - 12}`}M152 ${y}L154 ${y}" stroke="${on ? LIVE : '#666'}" stroke-width="2.5" fill="none"/>
      <text x="136" y="${y + 26}" font-size="10" text-anchor="middle" fill="#666">${on ? '合' : '分'}</text></g>`);
    rows.push(line([[80, y], [110, y]], true, 3) + line([[162, y], [220, y]], on, 3));
    const n = wlLights(F, w).length;
    rows.push(`<text x="232" y="${y - 6}" font-size="14" font-weight="bold" fill="${col}">${w}</text><text x="276" y="${y - 6}" font-size="12" fill="#333">${esc(def.name)} · ${esc(def.br)} · 灯 ${n} 盏 · 约 ${wlWatts(F, w)} W${F === 'FF' ? ' · 沿楼梯井引上至二层' : ''}</text>`);
    y += 34;
    const riserTop = y - 34;
    for (const c of cs) {
      const xs = [...D[F].ctrls[c.id]].sort((a, b) => a.middle - b.middle);   // two-way ends, middles inside
      if (xs.length >= 2) { const ends = xs.filter(x => !x.middle), mids = xs.filter(x => x.middle); xs.splice(0, xs.length, ends[0], ...mids, ...ends.slice(1)); }
      const isTr = tr && tr.F === F && tr.c === c.id;
      if (isTr) rows.push(`<rect x="225" y="${y - 42}" width="1180" height="${RH - 2}" fill="#fff6d6"/>`);
      rows.push(line([[220, y], [X0, y]], on, 2));
      rows.push(`<text x="232" y="${y - 26}" font-size="13" font-weight="bold" fill="${col}">${c.letter}</text><text x="248" y="${y - 26}" font-size="11.5" fill="#333">${esc(c.name)}</text>`);
      // switches
      let x = X0, live = on, trav = 0, out = false;
      const st = x_ => !!sim.key[kid(x_.F, x_.plate, x_.key)];
      const lab = (x_, cx) => `<text x="${cx}" y="${y + 30}" font-size="10.5" text-anchor="middle" fill="#444">${x_.F !== F ? FCN[x_.F] + ' ' : ''}${x_.plate}·键${x_.gang}${x_.middle ? ' 中途' : ''}</text>`;
      const hit = (x_, x1, w_) => `<rect x="${x1}" y="${y - 22}" width="${w_}" height="42" fill="transparent" data-k="key" data-f="${x_.F}" data-plate="${x_.plate}" data-key="${esc(x_.key)}"/>`;
      if (!xs.length) { rows.push(`<text x="${x + 10}" y="${y + 4}" font-size="11" fill="#c62828">无开关</text>`); x += 90; out = false; }
      else if (xs.length === 1) {
        const s = st(xs[0]);
        rows.push(line([[x, y], [x + 12, y]], live) + `<circle cx="${x + 12}" cy="${y}" r="3" fill="#333"/><circle cx="${x + 52}" cy="${y}" r="3" fill="#333"/>` +
          line([[x + 12, y], s ? [x + 52, y] : [x + 47, y - 16]], live, 2.5) + lab(xs[0], x + 32) + hit(xs[0], x, 64));
        out = live && s; x += 64; rows.push(line([[x - 12, y], [x, y]], out));
      } else {
        // first two-way: common -> traveller sA
        const sA = st(xs[0]) ? 1 : 0, ty = t => y + (t ? 9 : -9);
        rows.push(line([[x, y], [x + 12, y]], live) + `<circle cx="${x + 12}" cy="${y}" r="3" fill="#333"/>` + line([[x + 12, y], [x + 48, ty(sA)]], live, 2.5) + lab(xs[0], x + 32) + hit(xs[0], x, 64));
        trav = sA; x += 48;
        for (let i = 1; i < xs.length; i++) {
          const xi = xs[i], last = i === xs.length - 1;
          if (!last || xi.middle) {   // intermediate (or a middle in the wrong place): straight / crossed
            const s = st(xi);
            rows.push(line([[x, ty(0)], [x + 40, ty(0)]], live && trav === 0) + line([[x, ty(1)], [x + 40, ty(1)]], live && trav === 1));
            const mx = x + 40;
            rows.push(`<rect x="${mx}" y="${y - 16}" width="44" height="32" fill="none" stroke="#777" stroke-dasharray="3 2"/>` +
              (s ? line([[mx, ty(0)], [mx + 44, ty(1)]], live && trav === 0, 2.5) + line([[mx, ty(1)], [mx + 44, ty(0)]], live && trav === 1, 2.5)
                 : line([[mx, ty(0)], [mx + 44, ty(0)]], live && trav === 0, 2.5) + line([[mx, ty(1)], [mx + 44, ty(1)]], live && trav === 1, 2.5)) + lab(xi, mx + 22) + hit(xi, mx - 4, 52));
            if (s) trav ^= 1; x = mx + 44;
            if (last) { out = false; rows.push(`<text x="${x + 6}" y="${y + 4}" font-size="11" fill="#c62828">缺两路开关</text>`); x += 70; }
          } else {
            const s = st(xi), conn = 1 ^ (s ? 1 : 0);
            rows.push(line([[x, ty(0)], [x + 40, ty(0)]], live && trav === 0) + line([[x, ty(1)], [x + 40, ty(1)]], live && trav === 1));
            const bx = x + 40;
            rows.push(`<circle cx="${bx + 40}" cy="${y}" r="3" fill="#333"/>` + line([[bx + 40, y], [bx + 4, ty(conn)]], live && trav === conn, 2.5) + lab(xi, bx + 22) + hit(xi, bx - 4, 52));
            out = live && trav === conn; x = bx + 40;
            rows.push(line([[x, y], [x + 12, y]], out)); x += 12;
          }
        }
        if (xs.length >= 3 && !xs.some(z => z.middle)) rows.push(`<text x="${X0 + 420}" y="${y - 26}" font-size="10.5" fill="#c62828">⚠ ${modeName(xs.length)}缺中途开关</text>`);
      }
      // door switch in parallel
      const dss = S[F].door_switches.filter(ds => ds.circuit === c.id);
      for (const ds of dss) {
        const open = !!sim.door[F + '|' + ds.id];
        rows.push(line([[X0 - 10, y], [X0 - 10, y + 22], [X0 + 20, y + 22]], live, 1.5) + `<circle cx="${X0 + 20}" cy="${y + 22}" r="2.5"/>` +
          line([[X0 + 20, y + 22], open ? [X0 + 56, y + 22] : [X0 + 52, y + 10]], live, 2) + line([[X0 + 56, y + 22], [x, y + 22], [x, y]], live && open, 1.5) +
          `<text x="${X0 + 64}" y="${y + 19}" font-size="10" fill="#444">${ds.id} 门控（${open ? '门开' : '门关'}）</text><rect x="${X0 + 10}" y="${y + 8}" width="60" height="22" fill="transparent" data-k="mk" data-f="${F}" data-id="${ds.id}"/>`);
        out = out || (live && open);
      }
      // lamps in parallel
      const lx0 = Math.max(x + 30, 760);
      rows.push(line([[x, y], [lx0 + (c.lights.length - 1) * 46, y]], out, 2));
      c.lights.forEach((id, i) => {
        const l = D[F].L[id], lx = lx0 + i * 46, ly = y;
        if (out) rows.push(`<circle cx="${lx}" cy="${ly}" r="20" fill="url(#sglow)"/>`);
        rows.push(`<g data-k="lamp" data-f="${F}" data-id="${esc(id)}"><circle cx="${lx}" cy="${ly}" r="11" fill="${out ? '#ffd54a' : '#fff'}" stroke="#222" stroke-width="1.5"/>` +
          (l?.kind === '筒灯' ? `<circle cx="${lx}" cy="${ly}" r="3" fill="#222"/>` : `<path d="M${lx - 7} ${ly - 7}L${lx + 7} ${ly + 7}M${lx - 7} ${ly + 7}L${lx + 7} ${ly - 7}" stroke="#222" stroke-width="1.3"/>`) +
          `<text x="${lx}" y="${ly + 26}" font-size="9" text-anchor="middle" fill="#555">${esc(short(id).replace('GU10 ', ''))}</text></g>`);
      });
      // fans (FI) on this circuit
      for (const [pid, fc] of Object.entries(D[F].fan)) if (fc === c.id) {
        const p = D[F].P[pid], fon = !!sim.key[kid(F, pid, p.keys[0])], fx = lx0 + c.lights.length * 46 + 30, run = out && fon;
        rows.push(line([[fx - 34, y], [fx - 20, y]], out) + `<circle cx="${fx - 20}" cy="${y}" r="2.5"/>` + line([[fx - 20, y], fon ? [fx + 10, y] : [fx + 6, y - 12]], out, 2) +
          `<rect x="${fx - 24}" y="${y - 20}" width="40" height="40" fill="transparent" data-k="key" data-f="${F}" data-plate="${pid}" data-key="${p.keys[0]}"/>` +
          line([[fx + 10, y], [fx + 22, y]], run) + `<circle cx="${fx + 36}" cy="${y}" r="13" fill="${run ? '#d9f0fb' : '#fff'}" stroke="#2e86ab" stroke-width="1.5"/><text x="${fx + 36}" y="${y + 4}" font-size="12" text-anchor="middle" fill="#2e86ab" font-weight="bold">M</text>` +
          `<text x="${fx + 8}" y="${y + 30}" font-size="10" text-anchor="middle" fill="#444">${pid} FI→排气扇</text>`);
      }
      const m_ = modeName(xs.length);
      rows.push(`<text x="1395" y="${y + 4}" font-size="11" text-anchor="end" fill="${xs.length >= 2 ? '#c62828' : '#666'}">${m_}${dss.length ? ' + 门控' : ''}</text>`);
      y += RH;
    }
    rows.push(line([[220, riserTop], [220, y - RH]], on, 3));
    y += 16;
  }
  const H = y + 20;
  el.innerHTML = `<svg width="1420" height="${H}" viewBox="0 0 1420 ${H}" style="font-family:Microsoft YaHei">
    <defs><radialGradient id="sglow"><stop offset="0" stop-color="#ffe066" stop-opacity=".9"/><stop offset="1" stop-color="#ffd43b" stop-opacity="0"/></radialGradient></defs>
    <style>.slive{stroke-dasharray:7 5;animation:sflow .7s linear infinite}@keyframes sflow{to{stroke-dashoffset:-24}}</style>
    <text x="20" y="30" font-size="16" font-weight="bold" fill="#1f4e79">AL1 照明配电箱（一层楼梯下）→ WL1–WL${all.length} → 开关 → 灯　<tspan font-size="12" font-weight="normal" fill="#666">点开关切换 · 点断路器分合 · 红色流动 = 带电</tspan></text>
    <path d="M80 50V${H - 20}" stroke="${LIVE}" stroke-width="5"/><text x="70" y="62" font-size="11" text-anchor="end" fill="#666">母线</text>
    ${rows.join('')}</svg>`;
  el.addEventListener('pointerdown', ev => {
    const t = ev.target.closest('[data-k]'); if (!t) return;
    const k = t.dataset.k;
    if (k === 'key') { const s = kid(t.dataset.f, t.dataset.plate, t.dataset.key); sim.key[s] = !sim.key[s]; }
    else if (k === 'brk') sim.brk[t.dataset.wl] = sim.brk[t.dataset.wl] === false;
    else if (k === 'mk') { const s = t.dataset.f + '|' + t.dataset.id; sim.door[s] = !sim.door[s]; }
    else if (k === 'lamp') ui.trace = { F: t.dataset.f, light: t.dataset.id, c: D[t.dataset.f].lightCirc[t.dataset.id] };
    const st = el.scrollTop; render(); const nel = document.querySelector('.pane.schem'); if (nel) nel.scrollTop = st;
  });
}

/* ---------------- sidebar ---------------- */
function sideInfo() {
  const h = [];
  const t = ui.trace;
  if (t) {
    const F = t.F, d = D[F], c = d.C[t.c], l = d.L[t.light];
    h.push(`<h3>线路追踪</h3><div class="trace">`);
    if (l) h.push(`<div class="step"><b>灯</b> ${esc(short(l.id))}（${esc(l.kind)}，${esc(d.room[l.id])}）　${lightOn(F, l.id) ? '<span style="color:#b8860b">● 亮</span>' : '<span class="muted">○ 灭</span>'}</div>`);
    if (!c) h.push(`<div class="step" style="color:#c62828">这盏灯没有接到任何回路（没有开关）。</div>`);
    else {
      const xs = d.ctrls[c.id], wl = S[F].wl[c.wl];
      h.push(`<div class="arrow">↑ 同字母灯串接</div><div class="step"><b>回路</b> <span class="chip" style="background:${wlColor(c.wl)}">${c.letter}</span> ${esc(c.name)} · ${c.lights.length} 盏 · <span class="mode">${modeName(xs.length)}</span></div>`);
      h.push(`<div class="arrow">↑ 开关线（点线）</div><div class="step"><b>开关</b><br>${xs.map(x => { const p = S[x.F].plates.find(q => q.id === x.plate); return `· ${x.F !== F ? FCN[x.F] + ' ' : ''}${x.plate} 键 ${x.gang}${x.middle ? '（中途开关）' : xs.length > 1 ? '（两路开关）' : ''} — ${esc(p?.location || '')}　${sim.key[kid(x.F, x.plate, x.key)] ? '▼ 按下' : '▲'}`; }).join('<br>') || '<span style="color:#c62828">无</span>'}
        ${S[F].door_switches.filter(ds => ds.circuit === c.id).map(ds => `<br>· ${ds.id} 门控（并联）— ${esc(ds.location)}`).join('')}</div>`);
      if (xs.length > 1) h.push(`<div class="muted" style="margin-left:10px">开关之间敷设联络线 3C+E（红色长虚线）</div>`);
      h.push(`<div class="arrow">↑ 进线（粗线，先到开关盒）</div><div class="step"><b>配电回路</b> ${c.wl ? `<span class="chip" style="background:${wlColor(c.wl)}">${c.wl}</span> ${esc(wl?.name || '')}<br><span class="muted">${esc(wl?.br || '')} · BV-3×2.5 PC20${F === 'FF' ? ' · 由一层 AL1 沿楼梯井引上' : ''}</span>` : '<span style="color:#c62828">未分配</span>'}</div>`);
      h.push(`<div class="arrow">↑</div><div class="step"><b>AL1</b> 照明配电箱（一层楼梯下，暂定）　${c.wl && sim.brk[c.wl] === false ? '<span style="color:#c62828">断路器已分断</span>' : ''}</div>`);
    }
    h.push(`</div><p class="muted">平面上已高亮这条线路，其余变淡。点空白处取消。</p>`);
    if (c) h.push(`<button id="trtoggle">${circuitOn(F, c) ? '关掉' : '打开'}这个回路</button>`);
    return h.join('');
  }
  const s = ui.sel, o = findSel();
  if (s?.k === 'plate' && o) {
    const F = s.F, d = D[F], p = o, ed = ui.mode === 'edit';
    h.push(`<h3>开关 ${p.id}　<span class="muted">${FCN[F]} · ${p.gangs ? p.gangs + ' 联' : 'FI 排气扇隔离开关'}</span></h3>`);
    h.push(`<div class="kv"><div>位置</div><div>${ed ? `<input type="text" id="ploc" value="${esc(p.location)}">` : esc(p.location)}</div><div>房间</div><div>${esc(roomName(F, p.x, p.y))}</div><div>分区图</div><div>${p.sheet ? `0${p.sheet}（${esc(S[F].zones[p.sheet]?.name || '')}）` : '<span style="color:#b7791f">不在任何分区</span>'}</div><div>联数</div><div>${ed ? `<select id="pgang">${[1, 2, 3, 4].map(g => `<option ${g === p.gangs ? 'selected' : ''}>${g}</option>`).join('')}${p.gangs === 0 ? '<option selected value="0">FI</option>' : ''}</select>` : p.gangs}</div></div>`);
    h.push(`<h3>逐键（从左到右）</h3>`);
    p.keys.forEach((k, i) => {
      const c = d.C[d.keyCirc[k]], sk = S[F].special_keys[k], act = ui.ak && ui.ak.F === F && ui.ak.plate === p.id && ui.ak.key === k;
      const xs = c ? d.ctrls[c.id] : [];
      const desc = c ? `<span class="chip" style="background:${wlColor(c.wl)}">${c.letter}</span> ${esc(c.name)} <span class="mode">${modeName(xs.length)}</span>${(p.middle_keys || []).includes(k) ? ' <span class="mode" style="color:#c62828">中途</span>' : ''}`
        : sk ? esc(sk.text) : '<span style="color:#b7791f">未连灯</span>';
      h.push(`<div class="keyrow ${act ? 'act' : ''}"><div>键 ${i + 1}<br><span class="muted">#${esc(k)}</span></div><div>${desc}</div><div>${ed ? `<button data-act="pick" data-key="${esc(k)}">${act ? '已选' : '选键'}</button>${c || (sk && sk.link) ? ` <button data-act="unlink" data-key="${esc(k)}">解除</button>` : ''}${c && xs.length >= 3 ? ` <button data-act="mid" data-key="${esc(k)}">${(p.middle_keys || []).includes(k) ? '取消中途' : '设中途'}</button>` : ''}` : ''}</div></div>`);
    });
    if (ed) h.push(`<p class="muted">选中键后，在平面上点灯（Shift 拖框可多选）。点到已有回路的灯 = 加入该回路（自动变双控 / 三控）；再点本回路的灯 = 移出。切到另一层点灯 = 跨层控制。</p><button id="pdel">删除这个开关</button>`);
    return h.join('');
  }
  if (s?.k === 'mk' && o) {
    const F = s.F, c = D[F].C[o.circuit];
    h.push(`<h3>门控开关 ${o.id}</h3><div class="kv"><div>位置</div><div>${esc(o.location)}</div><div>回路</div><div>${c ? `<span class="chip" style="background:${wlColor(c.wl)}">${c.letter}</span> ${esc(c.name)}` : '<span style="color:#c62828">未连接（点一盏灯）</span>'}</div><div>并联</div><div>${esc(o.parallel || '—')}</div></div>`);
    if (ui.mode === 'edit') h.push(`<p class="muted">选中后点一盏灯 = 并联到它的回路。</p><button id="mkdel">删除</button>`);
    return h.join('');
  }
  if (s?.k === 'lamp' && o) {
    const F = s.F, c = D[F].C[D[F].lightCirc[o.id]];
    h.push(`<h3>灯 ${esc(short(o.id))}</h3><div class="kv"><div>类型</div><div>${esc(o.kind)}${o.outdoor ? '（户外）' : ''}</div><div>房间</div><div>${esc(D[F].room[o.id])}</div><div>回路</div><div>${c ? `<span class="chip" style="background:${wlColor(c.wl)}">${c.letter}</span> ${esc(c.name)}` : '<span style="color:#c62828">无开关</span>'}</div><div>防护</div><div>${ui.mode === 'edit' ? `<select id="lip">${['IP20', 'IP44', 'IP54', 'IP65', 'IP67'].map(v => `<option ${v === ipStr(F, o) ? 'selected' : ''}>${v}</option>`).join('')}</select>` : ipStr(F, o)}${o.ip ? '' : ' <span class="muted">（默认）</span>'}</div></div>`);
    return h.join('');
  }
  h.push(`<h3>怎么用</h3>
  <p><b>试灯</b>：点平面上开关面板的键（每个小方块 = 一个键，字母 = 它控制的回路），对应的灯会亮。双控 / 三控任意一处都能开关。点灯 → 追踪它从 AL1 到开关再到灯的整条线路。</p>
  <p><b>电路图</b>：AL1 → 断路器 WL → 开关（两路 / 中途）→ 灯，带电部分为红色流动线，可以点开关和断路器。</p>
  <p><b>编辑</b>：「放开关」点墙即放（自动贴墙、门锁侧 150 mm，Alt 不吸附）；点面板上的键选中，再点灯建立控制关系；拖动面板移动；Delete 删除；Ctrl+Z 撤销。</p>
  <p class="muted">线路：粗线 = AL1 引出的 WL（常带电）；细实线 = 同一字母的灯之间；点线 = 开关到灯；红色长虚线 = 双控 / 三控联络线。颜色 = WL。</p>`);
  return h.join('');
}
function sideCirc() {
  const fl = ui.view === 'GF' || ui.view === 'FF' ? [ui.view] : FLOORS, h = [];
  for (const F of fl) {
    h.push(`<h3>${FCN[F]}回路（${S[F].circuits.length}）</h3><table class="lst"><tr><th>字母</th><th>名称</th><th>控制</th><th>WL</th></tr>`);
    for (const c of S[F].circuits) {
      const xs = D[F].ctrls[c.id], on = circuitOn(F, c), cur = ui.trace && ui.trace.F === F && ui.trace.c === c.id;
      h.push(`<tr data-tr="${F}|${c.id}" class="${cur ? 'cur' : ''}"><td><span class="chip" style="background:${wlColor(c.wl)}">${c.letter}</span>${on ? ' 💡' : ''}</td><td>${ui.mode === 'edit' ? `<input type="text" data-cname="${F}|${c.id}" value="${esc(c.name)}">` : esc(c.name)}<div class="muted">${c.lights.length} 盏 · ${xs.map(x => (x.F !== F ? FCN[x.F] : '') + x.plate + '-' + x.gang + (x.middle ? '中' : '')).join(' ')}</div></td><td><span class="mode" style="color:${xs.length >= 2 ? '#c62828' : '#555'}">${modeName(xs.length)}</span></td><td>${ui.mode === 'edit' ? `<select data-cwl="${F}|${c.id}">${Object.keys(S[F].wl).map(w => `<option ${w === c.wl ? 'selected' : ''}>${w}</option>`).join('')}${c.wl ? '' : '<option selected value="">—</option>'}</select>` : c.wl || '—'}</td></tr>`);
    }
    h.push('</table>');
  }
  return h.join('');
}
function sideWL() {
  const h = [];
  for (const F of FLOORS) {
    h.push(`<h3>${FCN[F]}${F === 'FF' ? '（由一层 AL1 沿楼梯井引上）' : '（AL1 楼梯下）'}</h3>`);
    for (const [w, def] of Object.entries(S[F].wl)) {
      const cs = S[F].circuits.filter(c => c.wl === w), on = sim.brk[w] !== false;
      h.push(`<div style="border:1px solid #e3e6ea;border-left:4px solid ${wlColor(w)};border-radius:4px;padding:6px 8px;margin:6px 0">
        <div><b style="color:${wlColor(w)}">${w}</b> ${esc(def.name)}</div><div class="muted">${esc(def.br)} · 灯 ${wlLights(F, w).length} 盏 · 约 ${wlWatts(F, w)} W（估算：筒灯 5 W，主灯 40 W，壁灯 10 W，地灯 3 W）</div>
        <div style="margin-top:4px">${cs.map(c => `<span class="chip" style="background:${wlColor(w)}" title="${esc(c.name)}" data-tr="${F}|${c.id}">${c.letter}</span>`).join('') || '<span class="muted">无回路</span>'}</div>
        <div style="margin-top:4px"><button data-brk="${w}">${on ? '分断（试验）' : '合闸'}</button></div></div>`);
    }
    if (ui.mode === 'edit') h.push(`<button data-addwl="${F}">+ 新增 WL（${FCN[F]}）</button>`);
  }
  h.push(`<p class="muted">改回路的 WL：在「回路」页的下拉框里选（编辑模式）。</p>`);
  return h.join('');
}
function sideChk() {
  const h = [`<h3>规则检查（${ISS.filter(i => i.sev === 'error').length} 错误 · ${ISS.filter(i => i.sev === 'warn').length} 警告 · ${ISS.filter(i => i.sev === 'info').length} 提示）</h3>`];
  h.push(`<p class="muted">红 = 错误（导出前要处理）；黄 = 警告；蓝 = 提示（开关位置等，按现场定）。点一条定位。</p>`);
  ISS.forEach((i, n) => h.push(`<div class="iss ${i.sev}" data-iss="${n}"><b>${FCN[i.F]}</b>${esc(i.msg)}${i.tgt?.fix === 'middle' && ui.mode === 'edit' ? ` <button data-fixmid="${i.F}|${i.tgt.id}">自动设中途</button>` : ''}</div>`));
  if (!ISS.length) h.push('<p>没有问题。</p>');
  return h.join('');
}
function sideOut() {
  const nerr = ISS.filter(i => i.sev === 'error').length, h = [];
  h.push(`<h3>保存 / 打开</h3><button id="savejson">保存 JSON（两层）</button> <button id="openjson">打开 JSON…</button> <button id="reset">恢复 Rev B 数据</button>`);
  h.push(`<h3>生成施工图 PPT</h3>`);
  h.push(SERVER ? `<p class="muted">调用 products/make_lighting_drawings.py（英式）和 make_lighting_drawings_cn.py（国标），两层各一套，输出到 lighting_tool/out/（不覆盖 Downloads 里的 Rev B）。</p>
    <div>文件名标记 <input type="text" id="buildtag" value="工具" style="width:120px"></div><p><button class="prim" id="build">生成 PPT（${nerr ? `有 ${nerr} 个错误` : '检查通过'}）</button></p>`
    : `<p class="muted">离线打开时不能直接跑 Python。要一键出 PPT，请运行：<br><code>3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\server.py</code><br>然后打开 http://127.0.0.1:8765/ 。现在可以先「保存 JSON」。</p>`);
  if (lastBuild) {
    h.push(`<div class="res"><h3>${lastBuild.ok ? '已生成' : '有失败'}</h3>`);
    for (const r of lastBuild.results || []) h.push(`<div>${r.ok ? '✔' : '✘'} ${FCN[r.floor]} ${r.style === 'en' ? '英式' : '国标'} · <a href="${esc(r.file)}">${esc(r.file.split('/').pop())}</a> · ${r.seconds}s ${r.ok ? `<button data-render="${esc(r.file)}">预览</button>` : `<pre style="white-space:pre-wrap;font-size:11px">${esc(r.log)}</pre>`}</div>`);
    if (lastBuild.error) h.push(`<pre>${esc(lastBuild.error)}</pre>`);
    if (lastBuild.pngs) h.push(lastBuild.pngs.map(p => `<a href="${p}" target="_blank"><img src="${p}?t=${Date.now()}"></a>`).join(''));
    h.push('</div>');
  }
  return h.join('');
}

/* ---------------- export ---------------- */
function exportFloor(F) {
  const J = clone(S[F]), O = FLOORS.find(x => x !== F);
  const wlN = (G, defs) => { const o = {}; for (const [w, d] of Object.entries(defs)) o[w] = { ...d, n: S[G].circuits.filter(c => c.wl === w).reduce((a, c) => a + c.lights.length, 0) }; return o; };
  J.wl = wlN(F, J.wl); J.wl_other = wlN(O, S[O].wl);
  J.circuits.forEach(c => { if (c.remote_links) c.remote = c.remote_links.map(r => `${FCN[r.floor]} ${r.plate}`); });
  J.lights.forEach(l => { if (!l.ip) delete l.ip; });
  return J;
}
function download(name, text) { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' })); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); }
async function build() {
  const hard = ISS.filter(i => i.sev === 'error' && i.tgt?.hard), errs = ISS.filter(i => i.sev === 'error');
  if (hard.length) { alert('以下错误会让出图脚本失败，导出已拦下：\n\n' + hard.map(i => FCN[i.F] + ' ' + i.msg).join('\n')); ui.tab = 'chk'; render(); return; }
  if (errs.length && !confirm(`还有 ${errs.length} 个错误：\n\n${errs.slice(0, 8).map(i => FCN[i.F] + ' ' + i.msg).join('\n')}\n\n仍然导出（图上会带着这些问题）？`)) { ui.tab = 'chk'; render(); return; }
  const b = $('#build'); if (b) { b.disabled = true; b.textContent = '生成中（约 20 秒）…'; }
  try {
    const r = await fetch('api/build', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ floors: { GF: exportFloor('GF'), FF: exportFloor('FF') }, tag: $('#buildtag')?.value || '工具' }) });
    lastBuild = await r.json();
  } catch (e) { lastBuild = { ok: false, error: String(e) }; }
  render();
}
async function renderPng(file) {
  toast('PowerPoint 导出预览图…');
  const r = await fetch('api/render', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file }) });
  const j = await r.json(); lastBuild = { ...(lastBuild || {}), pngs: j.pngs }; render();
}

/* ---------------- top-level render & wiring of controls ---------------- */
function layout() {
  const main = $('#main'); main.innerHTML = ''; panes.length = 0;
  if (ui.view === 'schem') { renderSchem(main); return; }
  for (const F of ui.view === 'both' ? FLOORS : [ui.view]) {
    const old = layout.vb?.[F]; const p = new Pane(F, main); if (old) { p.vb = old; p.setVB(); } panes.push(p);
  }
}
layout.vb = {};
function render() {
  panes.forEach(p => layout.vb[p.F] = p.vb);
  if (ui.view === 'schem') { layout(); }
  else if (!panes.length || panes.map(p => p.F).join() !== (ui.view === 'both' ? FLOORS : [ui.view]).join()) layout();
  panes.forEach(p => p.render());
  document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('on', b.dataset.view === ui.view));
  document.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('on', b.dataset.mode === ui.mode));
  document.querySelectorAll('[data-tool]').forEach(b => b.classList.toggle('on', b.dataset.tool === ui.tool));
  document.querySelectorAll('[data-tab]').forEach(b => b.classList.toggle('on', b.dataset.tab === ui.tab));
  $('#edittools').style.display = ui.mode === 'edit' ? '' : 'none';
  $('#simtools').style.display = ui.mode === 'sim' ? '' : 'none';
  $('#undo').disabled = !hist.undo.length; $('#redo').disabled = !hist.redo.length;
  const ne = ISS.filter(i => i.sev === 'error').length, nw = ISS.filter(i => i.sev === 'warn').length;
  $('#nbad').innerHTML = (ne ? `<span class="badge">${ne}</span>` : '') + (nw ? `<span class="badge w">${nw}</span>` : '');
  const side = $('#side'), st = side.scrollTop;
  side.innerHTML = { info: sideInfo, circ: sideCirc, wl: sideWL, chk: sideChk, out: sideOut }[ui.tab]();
  side.scrollTop = st;
  const lit = FLOORS.reduce((a, F) => a + S[F].lights.filter(l => lightOn(F, l.id)).length, 0);
  foot(ui.mode === 'sim' ? `试灯：点开关面板上的键 · 点灯看线路 · 滚轮 / 双指 / ＋－ 缩放、拖动平移　|　亮灯 ${lit} / ${S.GF.lights.length + S.FF.lights.length}`
    : ui.ak ? `已选 ${ui.ak.mk ? ui.ak.mk : `${FCN[ui.ak.F]} ${ui.ak.plate} 键 ${S[ui.ak.F].plates.find(p => p.id === ui.ak.plate)?.keys.indexOf(ui.ak.key) + 1}`} → 点灯建立 / 取消控制（Shift 拖框多选；可切到另一层点灯 = 跨层）· Esc 取消`
    : ui.tool === 'place' ? '放开关：在墙边点一下（自动贴墙 / 门锁侧），类型在工具栏选' : '编辑：点面板上的键选中 → 点灯；拖动面板移动；Delete 删除；Ctrl+Z 撤销');
}
function foot(s) { $('#foot').textContent = s; }
let toastT; function toast(s) { const t = $('#toast'); t.textContent = s; t.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 2600); }
function focusIssue(i) {
  const t = i.tgt; if (!t) return;
  const F = i.F; if (ui.view !== 'both' || ui.view === 'schem') ui.view = F;
  let pt = null;
  if (t.k === 'plate' || t.k === 'key') { const p = S[F].plates.find(q => q.id === t.id); if (p) { pt = [p.x, p.y]; ui.sel = { k: 'plate', F, id: p.id }; } }
  if (t.k === 'lamp') { const l = D[F].L[t.id]; if (l) { pt = [l.x, l.y]; ui.sel = { k: 'lamp', F, id: l.id }; } }
  if (t.k === 'mk') { const m_ = S[F].door_switches.find(q => q.id === t.id); if (m_) { pt = [m_.x, m_.y]; ui.sel = { k: 'mk', F, id: m_.id }; } }
  if (t.k === 'circ') { ui.trace = { F, c: t.id, light: D[F].C[t.id]?.lights[0] }; const l = D[F].L[D[F].C[t.id]?.lights[0]]; if (l) pt = [l.x, l.y]; }
  render();
  const p = panes.find(x => x.F === F); if (p && pt) { p.zoomTo(pt, 6 * M(F)); }
}

function bind() {
  document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { ui.view = b.dataset.view; if (ui.trace && (ui.view === 'GF' || ui.view === 'FF') && ui.view !== ui.trace.F) ui.trace = null; render(); });
  document.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => { ui.mode = b.dataset.mode; ui.ak = null; ui.trace = null; render(); });
  document.querySelectorAll('[data-tool]').forEach(b => b.onclick = () => { ui.tool = b.dataset.tool; render(); });
  document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => { ui.tab = b.dataset.tab; render(); });
  $('#showwires').onchange = e => { ui.wires = e.target.checked; render(); };
  $('#showiss').onchange = e => { ui.issues = e.target.checked; render(); };
  $('#undo').onclick = undo; $('#redo').onclick = redo;
  $('#alloff').onclick = () => { for (const k in sim.key) sim.key[k] = false; for (const k in sim.door) sim.door[k] = false; render(); };
  $('#allon').onclick = () => { for (const F of FLOORS) S[F].circuits.forEach(c => setCircuit(F, c, true)); render(); };
  $('#demo').onclick = demo;
  $('#placetype').onchange = () => { ui.tool = 'place'; render(); };
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.key === 'Escape') { ui.ak = null; ui.trace = null; ui.sel = null; ui.tool = 'select'; render(); }
    if ((e.key === 'Delete' || e.key === 'Backspace') && ui.mode === 'edit' && ui.sel) {
      if (ui.sel.k === 'plate') deletePlate(ui.sel.F, ui.sel.id);
      else if (ui.sel.k === 'mk') { commit(); S[ui.sel.F].door_switches = S[ui.sel.F].door_switches.filter(x => x.id !== ui.sel.id); ui.sel = null; ui.ak = null; derive(); render(); }
    }
    if (e.ctrlKey && e.key.toLowerCase() === 'z') { e.preventDefault(); undo(); }
    if (e.ctrlKey && e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); }
  });
  $('#side').addEventListener('click', e => {
    const t = e.target, ds = t.dataset;
    if (t.id === 'trtoggle') { const c = D[ui.trace.F].C[ui.trace.c]; setCircuit(ui.trace.F, c, !circuitOn(ui.trace.F, c)); render(); return; }
    if (ds.act) { const s = ui.sel, p = S[s.F].plates.find(q => q.id === s.id);
      if (ds.act === 'pick') { ui.ak = ui.ak && ui.ak.key === ds.key && ui.ak.plate === p.id ? null : { F: s.F, plate: p.id, key: ds.key }; render(); }
      if (ds.act === 'unlink') unlinkKey(s.F, p.id, ds.key);
      if (ds.act === 'mid') { commit(); const mk = new Set(p.middle_keys || []); mk.has(ds.key) ? mk.delete(ds.key) : mk.add(ds.key); p.middle_keys = [...mk]; derive(); render(); }
      return; }
    if (t.id === 'pdel') return deletePlate(ui.sel.F, ui.sel.id);
    if (t.id === 'mkdel') { commit(); S[ui.sel.F].door_switches = S[ui.sel.F].door_switches.filter(x => x.id !== ui.sel.id); ui.sel = null; derive(); render(); return; }
    if (ds.brk) { sim.brk[ds.brk] = sim.brk[ds.brk] === false; render(); return; }
    if (ds.addwl) { commit(); let n = 0; FLOORS.forEach(F => Object.keys(S[F].wl).forEach(w => n = Math.max(n, parseInt(w.slice(2)) || 0))); S[ds.addwl].wl['WL' + (n + 1)] = { name: `${FCN[ds.addwl]}新增照明回路`, br: 'C16 1P+N RCBO 30mA', circ: [], n: 0 }; derive(); render(); return; }
    if (ds.fixmid) { const [F, cid] = ds.fixmid.split('|'); autoMiddle(F, cid); return; }
    if (t.closest('[data-iss]')) return focusIssue(ISS[+t.closest('[data-iss]').dataset.iss]);
    const tr = t.closest('[data-tr]');
    if (tr && t.tagName !== 'INPUT' && t.tagName !== 'SELECT') { const [F, c] = tr.dataset.tr.split('|'); ui.trace = ui.trace?.c === c && ui.trace.F === F ? null : { F, c, light: D[F].C[c].lights[0] }; if (ui.view !== 'both' && ui.view !== 'schem') ui.view = F; render(); return; }
    if (t.id === 'savejson') { download('lighting_GF.json', JSON.stringify(exportFloor('GF'), null, 1)); setTimeout(() => download('lighting_FF.json', JSON.stringify(exportFloor('FF'), null, 1)), 400); return; }
    if (t.id === 'openjson') return $('#openfile').click();
    if (t.id === 'reset') { if (confirm('恢复到 Rev B 数据？（可以撤销）')) { commit(); for (const F of FLOORS) S[F] = clone(ORIG[F].json); afterLoad(); } return; }
    if (t.id === 'build') return build();
    if (ds.render) return renderPng(ds.render);
  });
  $('#side').addEventListener('change', e => {
    const t = e.target, ds = t.dataset;
    if (t.id === 'ploc') { commit(); findSel().location = t.value; render(); }
    if (t.id === 'pgang') { setGangs(ui.sel.F, findSel(), +t.value); }
    if (t.id === 'lip') { commit(); findSel().ip = t.value; derive(); render(); }
    if (ds.cname) { const [F, c] = ds.cname.split('|'); commit(); D[F].C[c].name = t.value; derive(); render(); }
    if (ds.cwl) { const [F, c] = ds.cwl.split('|'); commit(`回路 ${D[F].C[c].letter} → ${t.value}`); D[F].C[c].wl = t.value; syncWlCirc(); derive(); render(); }
  });
  $('#openfile').onchange = async e => {
    commit();
    for (const f of e.target.files) { const j = JSON.parse(await f.text()); if (FLOORS.includes(j.floor)) { S[j.floor] = j; } }
    afterLoad(); toast('已载入 ' + [...e.target.files].map(f => f.name).join('、')); e.target.value = '';
  };
}
function syncWlCirc() { for (const F of FLOORS) for (const [w, d] of Object.entries(S[F].wl)) d.circ = S[F].circuits.filter(c => c.wl === w).map(c => c.id); }
function setGangs(F, p, g) {
  commit(); const nk = nextKey(F);
  while (p.keys.length < g) p.keys.push(nk());
  while (p.keys.length > g) { const k = p.keys.pop(); if (!S[F].plates.some(x => x.keys.includes(k))) { S[F].circuits.forEach(c => c.keys = c.keys.filter(x => x !== k)); dropSpecial(F, k); } }
  p.gangs = g; p.panel = `${GNAME[g]} ${p.panel.split(' ').slice(1).join(' ') || p.id}`; derive(); render();
}
async function demo() {
  const b = $('#demo'); if (b.dataset.run) { b.dataset.run = ''; return; }
  b.dataset.run = '1'; b.textContent = '停止演示';
  for (const F of FLOORS) for (const c of S[F].circuits) {
    if (!b.dataset.run) break;
    for (const k in sim.key) sim.key[k] = false;
    setCircuit(F, c, true); ui.trace = { F, c: c.id, light: c.lights[0] }; if (ui.view !== 'both' && ui.view !== 'schem') ui.view = F; render();
    await new Promise(r => setTimeout(r, 1300));
  }
  b.dataset.run = ''; b.textContent = '逐个回路演示'; ui.trace = null; for (const k in sim.key) sim.key[k] = false; render();
}

/* ---------------- plan A / B (power_data.js): same lamps and switches, lighting regrouped onto different breakers ---------------- */
const PLANS = window.POWER_DEFAULT?.plans || null;
const planFromHash = () => { const h = (location.hash || '').replace('#', '').split('-')[0].toUpperCase(); return PLANS && PLANS[h] ? h : (window.POWER_DEFAULT?.default || null); };
function applyPlan(pid) {
  const pl = PLANS && PLANS[pid]; if (!pl || !pl.lighting) return;
  for (const F of FLOORS) {
    S[F].wl = {};
    for (const w of pl.lighting.filter(x => x.floor === F)) {
      S[F].wl[w.id] = { name: w.name, br: w.br, circ: w.circ.filter(id => S[F].circuits.some(c => c.id === id)) };
      for (const cid of w.circ) { const c = S[F].circuits.find(x => x.id === cid); if (c) c.wl = w.id; }
    }
    for (const [w, v] of Object.entries(S[F].wl)) v.n = S[F].circuits.filter(c => c.wl === w).reduce((a, c) => a + c.lights.length, 0);
  }
  for (const F of FLOORS) S[F].wl_other = clone(S[F === 'GF' ? 'FF' : 'GF'].wl);
  ui.plan = pid;
  if (location.hash.replace('#', '').toUpperCase() !== pid) history.replaceState(null, '', '#' + pid);
  document.querySelectorAll('[data-plan]').forEach(b => b.classList.toggle('on', b.dataset.plan === pid));
  const v = document.getElementById('ver'), m = S.GF?.meta; if (v && m) v.textContent = (m.rev_cn || '').split(' ').slice(0, 2).join(' ') + ' · ' + pl.short;
  const n = document.getElementById('plannote'); if (n) n.textContent = '照明 ' + pl.lighting.length + ' 路：' + pl.lighting.map(w => w.id + ' ' + w.name.replace(/（.*|\+.*/, '')).join(' / ');
}

/* ---------------- start ---------------- */
async function start() {
  if (location.protocol.startsWith('http')) { try { SERVER = (await (await fetch('api/ping')).json()).ok; } catch (e) { SERVER = false; } }
  if (!ORIG) { document.body.innerHTML = '<p style="padding:20px">缺少 lighting_data.js，请先运行 export_lighting_json.py。</p>'; return; }
  for (const F of FLOORS) { S[F] = clone(ORIG[F].json); SVGSRC[F] = ORIG[F].svg; }
  for (const F of FLOORS) GEO[F] = buildGeo(F);
  { const v = document.getElementById('ver'), m = S.GF?.meta || S.FF?.meta; if (v && m) v.textContent = (m.rev_cn || '').split(' ')[0] + ' ' + (m.rev_cn || '').split(' ')[1]; }
  if (planFromHash()) applyPlan(planFromHash());
  derive(); bind(); render();
  document.querySelectorAll('[data-plan]').forEach(el => el.onclick = () => { applyPlan(el.dataset.plan); derive(); render(); });
  window.addEventListener('hashchange', () => { const p = planFromHash(); if (p && p !== ui.plan) { applyPlan(p); derive(); render(); } });
  window.APP = { applyPlan, get S() { return S; }, get D() { return D; }, zoom: (F, x, y, w) => panes.find(p => p.F === F)?.zoomTo([x, y], w * M(F)), panes, sim, ui, ISS: () => ISS, exportFloor, GEO, derive, render };
}
start();
