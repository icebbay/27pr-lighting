/* AL1 circuit list for one plan, shared by power.html and board.html.
   Plan A lighting = the lighting tool's own WL (lighting_data.js); plan B regroups the same lighting circuits (power_data.js).
   The plan comes from the URL hash (#A / #B) so a shared link opens the same plan. */
(function () {
  const L = window.LIGHTING_DEFAULT, P = window.POWER_DEFAULT;
  const FCN = { GF: '一层', FF: '二层' };
  const LPAL = ['#e07a1f', '#2e86ab', '#3b9c5a', '#8e5cc5', '#00838f', '#c2185b', '#6d4c41', '#d1495b'];   // same as the lighting tool
  const XPAL = ['#1565c0', '#6a1b9a', '#ef6c00', '#00897b', '#ad1457', '#2e7d32', '#5d4037', '#c62828', '#283593'];
  const PPAL = ['#b71c1c', '#4e342e', '#283593', '#37474f', '#0277bd', '#00838f', '#558b2f'];
  const lamps = (F, ids) => ids.reduce((a, id) => a + (L[F].json.circuits.find(c => c.id === id)?.lights.length || 0), 0);
  const letters = (F, ids) => ids.map(id => L[F].json.circuits.find(c => c.id === id)?.letter).join(' ');

  function build(pid) {
    const pl = P.plans[pid], out = [];
    const items = id => ['GF', 'FF'].flatMap(F => P[F].items.filter(t => t.c[pid] === id).map(t => t.label));
    const wl = pl.lighting || ['GF', 'FF'].flatMap(F => Object.entries(L[F].json.wl).map(([id, v]) => ({ id, floor: F, name: v.name, br: v.br, circ: v.circ })));
    for (const w of wl) {
      const n = parseInt(w.id.replace(/\D/g, ''), 10) || 1;
      out.push({ ...w, kind: 'WL', group: '照明', color: LPAL[(n - 1) % LPAL.length], cable: '1.5 mm²（英国常用；图上按国标标 BV-2.5）',
        count: `${lamps(w.floor, w.circ)} 盏灯`, letters: letters(w.floor, w.circ) });
    }
    const nS = id => ['GF', 'FF'].reduce((a, F) => a + P[F].sockets.filter(s => s.c[pid] === id).length, 0);
    pl.WX.forEach((c, i) => { const it = items(c.id);
      out.push({ ...c, kind: 'WX', group: '插座', color: XPAL[i % XPAL.length], count: `${nS(c.id)} 个插座` + (it.length ? ' + ' + it.join('、') : '') }); });
    pl.WP.forEach((c, i) => out.push({ ...c, kind: 'WP', group: '专线', color: PPAL[i % PPAL.length],
      floor: ['GF', 'FF'].find(F => P[F].items.some(t => t.c[pid] === c.id)) || null, count: items(c.id).join('、') || '位置待定' }));
    return { pid, plan: pl, list: out, byId: Object.fromEntries(out.map(c => [c.id, c])), board: pl.board };
  }

  const pick = () => { const h = (location.hash || '').replace('#', '').split('-')[0].toUpperCase(); return P.plans[h] ? h : P.default; };
  window.CIRCUITS = { FCN, build, pick, plans: Object.keys(P.plans), rev: P.rev,
    lightRev: (L.GF.json.meta.rev_cn || '').split(' ').slice(0, 2).join(' ') };
})();
