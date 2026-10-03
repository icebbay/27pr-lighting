/* 配电箱 AL1 page: all circuits (lighting + sockets + dedicated), single-line diagram, schedule, module count */
const CC = window.CIRCUITS;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const groups = [['照明', 'WL', '一个区域一路（见「照明」页）'], ['插座', 'WX', '按区域分，一路带几个房间'], ['专线', 'WP', '一样电器一路']];
const n = k => CC.list.filter(c => c.kind === k).length, total = CC.list.length;
const MOD = { main: 2, spd: 2, ways: total, evExtra: 1, spare: CC.spare };
const mods = MOD.main + MOD.spd + MOD.ways + MOD.evExtra + MOD.spare;

function oneLine() {   // incoming -> main switch + SPD -> busbar -> one RCBO per circuit (grouped) -> spare
  const rows = [];
  for (const [g, k] of groups) { rows.push({ head: g }); CC.list.filter(c => c.kind === k).forEach(c => rows.push({ c })); }
  for (let i = 0; i < CC.spare; i++) rows.push({ spare: i + 1 });
  const RH = 26, top = 70, W = 1100, bx = 190, H = top + rows.length * RH + 30, o = [];
  o.push(`<text x="10" y="22" font-size="13" font-weight="bold">进线（供电公司电表 → 总闸）</text>`,
    `<path d="M10 40H90" stroke="#111" stroke-width="3"/><rect x="90" y="28" width="52" height="24" fill="#fff" stroke="#111" stroke-width="2"/><text x="116" y="45" font-size="11" text-anchor="middle">总闸</text>`,
    `<path d="M142 40H${bx}" stroke="#111" stroke-width="3"/><rect x="${bx - 30}" y="52" width="40" height="18" fill="#fff" stroke="#555"/><text x="${bx - 10}" y="65" font-size="10" text-anchor="middle">SPD</text>`,
    `<path d="M${bx} 40V${top + (rows.length - 0.5) * RH}" stroke="#111" stroke-width="5"/>`);
  rows.forEach((r, i) => {
    const y = top + i * RH + RH / 2;
    if (r.head) { o.push(`<text x="${bx + 14}" y="${y + 5}" font-size="12" font-weight="bold" fill="#1f4e79">${r.head}</text>`); return; }
    const col = r.c ? r.c.color : '#999', dash = r.spare ? 'stroke-dasharray="6 4"' : '';
    o.push(`<path d="M${bx} ${y}H${bx + 60}" stroke="${col}" stroke-width="2" ${dash}/><rect x="${bx + 60}" y="${y - 9}" width="34" height="18" fill="#fff" stroke="${col}" stroke-width="2" ${dash}/>`,
      `<path d="M${bx + 94} ${y}H${bx + 150}" stroke="${col}" stroke-width="2" ${dash}/>`);
    if (r.c) o.push(`<text x="${bx + 77}" y="${y + 4}" font-size="10" text-anchor="middle" fill="${col}" font-weight="bold">${r.c.id}</text>`,
      `<text x="${bx + 158}" y="${y + 4}" font-size="12">${esc(r.c.name)}</text><text x="${W - 10}" y="${y + 4}" font-size="11" text-anchor="end" fill="#6b7280">${esc(r.c.br)}</text>`);
    else o.push(`<text x="${bx + 158}" y="${y + 4}" font-size="12" fill="#6b7280">备用 ${r.spare}</text>`);
  });
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;min-width:760px;height:auto">${o.join('')}</svg>`;
}

function schedule() {
  const h = ['<table class="sch"><tr><th>编号</th><th>楼层</th><th>回路</th><th>带什么</th><th>断路器</th><th>线缆</th><th>备注</th></tr>'];
  for (const [g, k, d] of groups) {
    h.push(`<tr class="grp"><td colspan="7">${g}（${n(k)} 路）— ${d}</td></tr>`);
    for (const c of CC.list.filter(x => x.kind === k))
      h.push(`<tr><td><span class="chip" style="background:${c.color}">${c.id}</span></td><td>${c.floor ? CC.FCN[c.floor] : '—'}</td><td>${esc(c.name)}</td>
        <td>${esc(c.count)}${c.letters ? `<div class="muted">灯字母 ${esc(c.letters)}</div>` : ''}</td><td>${esc(c.br)}</td><td>${esc(c.cable)}</td><td>${esc(c.note || '')}</td></tr>`);
  }
  h.push(`<tr class="grp"><td colspan="7">备用（${CC.spare} 路）</td></tr></table>`);
  return h.join('');
}

document.getElementById('ver').textContent = `${CC.lightRev} · ${total} 路`;
document.getElementById('main').innerHTML = `
  <div class="cards">
    <div class="card"><b>${n('WL')}</b>照明</div><div class="card"><b>${n('WX')}</b>插座</div><div class="card"><b>${n('WP')}</b>专线</div>
    <div class="card total"><b>${total}</b>合计（+ 总闸）</div><div class="card"><b>${CC.spare}</b>备用</div><div class="card total"><b>≈ ${mods}</b>模块（module）</div>
  </div>
  <div class="box"><h2>单线系统图</h2>${oneLine()}</div>
  <div class="box"><h2>回路表</h2>${schedule()}</div>
  <div class="box"><h2>配电箱要多大（模块数）</h2>
    <table class="sch" style="min-width:0"><tr><th>部件</th><th>模块</th></tr>
      <tr><td>总闸（主开关）</td><td>${MOD.main}</td></tr>
      <tr><td>防雷涌浪保护 SPD（BS 7671 现行版基本都要求）</td><td>${MOD.spd}</td></tr>
      <tr><td>${total} 路 RCBO（单模块型，一路一格）</td><td>${MOD.ways}</td></tr>
      <tr><td>充电桩 RCBO 带直流检测，常见双模块</td><td>+${MOD.evExtra}</td></tr>
      <tr><td>备用</td><td>${MOD.spare}</td></tr>
      <tr><td><b>合计</b></td><td><b>≈ ${mods}</b></td></tr></table>
    <ul class="notes">
      <li><b>21 / 22 模块的箱子不够</b>：装完总闸和 SPD 只剩 18–19 格，${total} 路放不下。</li>
      <li>21 和 22 模块只差一格（18 mm 宽、多插一个断路器）。更要紧的是问清厂家的 <b>usable ways（装完总闸后还剩几个回路位）</b>：同样写 22，实际能装的回路可能差 3–4 个。本方案需要 26 个以上可用位。</li>
      <li>建议 <b>双排 2 × 18 = 36 模块</b>（或单排 28–30 模块）。也可以把充电桩单独装一个小箱子放在门口，主箱少占 1–2 格。</li>
    </ul></div>
  <div class="box"><h2>给电工的说明</h2><ul class="notes">
    <li>每一路都是带 30 mA 漏电保护的 RCBO：哪一路出问题只断哪一路。</li>
    <li>充电桩：一般 7 kW、单独 32A；安装前要通知供电公司（DNO），通常由充电桩安装商代办。</li>
    <li>总负荷：电梯 + 烤箱 + 2 台空调 + 充电桩 + 洗衣烘干同时用会很大。英国住宅进户一般 60–100A，请按实际功率算；不够可以给充电桩加负载管理，比升级进户便宜。</li>
    <li>煤气灶只要一个点火插座（接厨房插座 WX3）；洗碗机经带保险开关接 WX3；烤箱、冰箱 FCU 的对应关系待现场定。</li>
    <li>空调 2 台位置待定；电梯按厂家要求配隔离开关。断路器规格、线径为建议值，以电工按 BS 7671 / Part P 复核为准。</li>
  </ul></div>
  <p class="muted">数据：照明来自照明工具（${esc(CC.lightRev)}），插座 / 专线来自 v6 PPT 插座页 + ${esc(CC.rev)}。</p>`;
