/* AL1 circuit list shared by power.html and board.html: lighting (WL, from lighting_data.js) + sockets (WX) + dedicated (WP), from power_data.js */
(function () {
  const L = window.LIGHTING_DEFAULT, P = window.POWER_DEFAULT;
  const FCN = { GF: '一层', FF: '二层' };
  const LPAL = ['#e07a1f', '#2e86ab', '#3b9c5a', '#8e5cc5', '#00838f', '#c2185b', '#6d4c41', '#d1495b'];   // same as the lighting tool
  const XPAL = ['#1565c0', '#6a1b9a', '#ef6c00', '#00897b', '#ad1457', '#2e7d32'];
  const PPAL = ['#b71c1c', '#4e342e', '#283593', '#37474f', '#0277bd', '#00838f', '#558b2f'];
  const out = [];
  for (const F of ['GF', 'FF']) {
    const J = L[F].json;
    for (const [w, v] of Object.entries(J.wl)) {
      const n = parseInt(w.replace(/\D/g, ''), 10) || 1;
      out.push({ id: w, kind: 'WL', group: '照明', floor: F, name: v.name, br: v.br, cable: '1.5 mm²（英国常用；图上按国标标 BV-2.5）', color: LPAL[(n - 1) % LPAL.length],
        count: `${v.n} 盏灯`, letters: v.circ.map(c => J.circuits.find(x => x.id === c)?.letter).join(' ') });
    }
  }
  const nS = id => ['GF', 'FF'].reduce((a, F) => a + P[F].sockets.filter(s => s.c === id).length, 0);
  P.circuits.WX.forEach((c, i) => out.push({ ...c, kind: 'WX', group: '插座', color: XPAL[i % XPAL.length], count: `${nS(c.id)} 个插座` +
    (['GF', 'FF'].some(F => P[F].items.some(t => t.c === c.id)) ? ' + ' + ['GF', 'FF'].flatMap(F => P[F].items.filter(t => t.c === c.id).map(t => t.label)).join('、') : '') }));
  P.circuits.WP.forEach((c, i) => out.push({ ...c, kind: 'WP', group: '专线', color: PPAL[i % PPAL.length],
    floor: ['GF', 'FF'].find(F => P[F].items.some(t => t.c === c.id)) || null,
    count: ['GF', 'FF'].flatMap(F => P[F].items.filter(t => t.c === c.id).map(t => t.label)).join('、') || '位置待定' }));
  window.CIRCUITS = { list: out, byId: Object.fromEntries(out.map(c => [c.id, c])), FCN, board: P.circuits.board, rev: P.circuits.rev,
    lightRev: (L.GF.json.meta.rev_cn || '').split(' ')[0] + ' ' + ((L.GF.json.meta.rev_cn || '').split(' ')[1] || '') };
})();
