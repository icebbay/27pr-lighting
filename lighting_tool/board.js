/* 配电箱 AL1 page: all circuits (lighting + sockets + dedicated), single-line diagram, schedule, module count */
const CC = window.CIRCUITS;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const groups = [['照明', 'WL', '一层两路、二层一路、户外一路（见「照明」页）'], ['插座', 'WX', '一路最多一个「电脑 + 电视」房间；厨房、洗衣、户外各自一路'], ['专线', 'WP', '大功率 / 固定接线设备，一样一路']];
const n = k => CC.list.filter(c => c.kind === k).length, total = CC.list.length;
const BD = window.POWER_DEFAULT.circuits.board, evExtra = 1, used = total + evExtra, spare = BD.ways - used;

function oneLine() {   // incoming -> main switch + SPD -> busbar -> one RCBO per circuit (grouped) -> spare
  const rows = [];
  for (const [g, k] of groups) { rows.push({ head: g }); CC.list.filter(c => c.kind === k).forEach(c => rows.push({ c })); }
  rows.push({ reserve: true }); rows.push({ spare: spare - 1 });
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
    else if (r.reserve) o.push(`<text x="${bx + 158}" y="${y + 4}" font-size="12" fill="#b7791f">${esc(BD.reserve)}</text>`);
    else o.push(`<text x="${bx + 158}" y="${y + 4}" font-size="12" fill="#6b7280">其余备用 × ${r.spare}</text>`);
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
  h.push(`<tr class="grp"><td colspan="7">备用 ${spare} 位（其中 1 位${esc(BD.reserve.replace('预留 1 位：', '预留给'))}）</td></tr></table>`);
  return h.join('');
}

document.getElementById('ver').textContent = `${CC.lightRev} · ${total} 路`;
document.getElementById('main').innerHTML = `
  <div class="cards">
    <div class="card"><b>${n('WL')}</b>照明</div><div class="card"><b>${n('WX')}</b>插座</div><div class="card"><b>${n('WP')}</b>专线</div>
    <div class="card total"><b>${total}</b>合计（+ 总闸）</div><div class="card"><b>${spare}</b>备用位</div><div class="card total"><b>${BD.ways}</b>位配电箱</div>
  </div>
  <div class="box"><h2>单线系统图</h2>${oneLine()}</div>
  <div class="box"><h2>回路表</h2>${schedule()}</div>
  <div class="box"><h2>推荐配电箱</h2>
    <table class="sch" style="min-width:0">
      <tr><td>型号</td><td><b>${esc(BD.model)}</b></td></tr>
      <tr><td>可用回路位（装完总闸、SPD 后）</td><td>${BD.ways}</td></tr>
      <tr><td>本方案占用</td><td>${total} 路 + 充电桩 RCBO 可能多占 ${evExtra} 格 = ${used}</td></tr>
      <tr><td>剩余备用</td><td>${spare}（其中 1 位${esc(BD.reserve.replace('预留 1 位：', '预留给'))}）</td></tr>
      <tr><td>总闸 / SPD</td><td>${esc(BD.main)} · ${esc(BD.spd)}</td></tr>
      <tr><td>尺寸</td><td>${esc(BD.size)}</td></tr>
      <tr><td>断路器</td><td>${esc(BD.rcbo)}：每路一个，共 ${total} 个，必须同品牌单模块</td></tr></table>
    <ul class="notes">
      <li>${total} 路超过单排箱子的容量（最大约 19–21 位，装完还要留备用），所以选双排 31 位：差价不大，以后加太阳能、家用电池、热泵、第 3 台空调都放得下。</li>
      <li>单排替代：MK Sentry 21 位（YS5721SMET）装完只剩 2 个备用；BG CF22MS19-01（19 位）不够。楼梯下放不下 483 mm 高的箱子时再考虑。</li>
      <li>买之前问清 <b>usable ways</b>（装完总闸后还剩几个回路位），并让电工确认品牌 —— 他要给整套线路签字。</li>
    </ul></div>
  <div class="box"><h2>给电工的说明</h2><ul class="notes">
    <li>每一路都是带 30 mA 漏电保护的 RCBO：哪一路出问题只断哪一路。</li>
    <li>充电桩：一般 7 kW、单独 32A；安装前要通知供电公司（DNO），通常由充电桩安装商代办。</li>
    <li>总负荷：电梯 + 烤箱 + 2 台空调 + 充电桩 + 洗衣烘干同时用会很大。英国住宅进户一般 60–100A，请按实际功率算；不够可以给充电桩加负载管理，比升级进户便宜。</li>
    <li>为什么书房、卧室各自一路：电脑、电视正常工作时每台对地漏电 1–5 mA，BS 7671 要求一路 30 mA RCBO 平时漏电不超过 30%（9 mA），一路放一个「电脑 + 电视」房间（约 4–8 mA）才不会误跳。</li>
    <li>煤气灶只要一个点火插座、冰箱和洗碗机经带保险开关，都接厨房 WX3；洗衣机 + 烘干机接洗衣房 WX4；烤箱 FCU 对应关系待现场定。电热毛巾架 ×2 经带保险开关接所在卫生间那一路。</li>
    <li>大功率工具位置未定：户外 WX9 已做成 32A；配电箱预留 1 位；趁墙打开可往储物间 / 后花园预埋一根空管。</li>
    <li>空调 2 台位置待定；电梯按厂家要求配隔离开关。断路器规格、线径为建议值，以电工按 BS 7671 / Part P 复核为准。</li>
  </ul></div>
  <p class="muted">数据：照明来自照明工具（${esc(CC.lightRev)}），插座 / 专线来自 v6 PPT 插座页 + ${esc(CC.rev)}。</p>`;
