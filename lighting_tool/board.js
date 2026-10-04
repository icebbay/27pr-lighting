/* 配电箱 AL1 page: plan A / B side by side, then the selected plan's single-line diagram, schedule and board.
   The plan is in the URL hash (#A / #B) so a shared link opens the same view. */
const CC = window.CIRCUITS;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const GROUPS = { WL: '照明', WX: '插座', WP: '专线' };
const EV_EXTRA = 1;   // EV RCBO with DC detection is often 2 modules
// Screwfix, 2026-10-04, inc VAT: BG Fortress compact single-module RCBOs (stock clearance — superseded by BG bi-directional, ~£17.99)
const RCBO = { 6: [8.00, '374VF', 'british-general-fortress-6a-30ma-type-a-sp-n-b-curve-compact-rcbo/374vf'],
  10: [4.00, '849VF', 'british-general-fortress-10a-30ma-sp-n-type-b-compact-rcbo/849vf'],
  16: [8.00, '969VF', 'british-general-fortress-16a-30ma-type-a-sp-n-b-curve-compact-rcbo/969vf'],
  20: [8.00, '783VF', 'british-general-fortress-20a-30ma-type-a-sp-n-b-curve-compact-rcbo/783vf'],
  32: [12.00, '368VF', 'british-general-fortress-32a-30ma-type-a-sp-n-b-curve-compact-rcbo/368vf'],
  40: [6.00, '581VF', 'british-general-fortress-40a-30ma-sp-n-type-b-compact-rcbo/581vf'] };
const BLANKS = [1.69, '8285P', 'british-general-fortress-abs-plastic-consumer-unit-blanks-10-pack/8285p'];
const SFX = path => `https://www.screwfix.com/p/${path}`;
const amps = c => /充电桩/.test(c.name) ? 40 : /电梯/.test(c.name) ? 20 : +(String(c.br).match(/B(\d+)/) || [0, 20])[1];
const money = v => '£' + v.toFixed(2);

// rough parts cost: board + one RCBO per circuit + the home run of cable back to the board (rooms' own wiring is the same in both plans)
function homeRun(c) {
  if (c.kind === 'WL') return [25, 0.7];
  if (/环路/.test(c.cable)) return [40, 1.0];   // a ring goes out and comes back
  if (/4 mm²/.test(c.cable)) return [20, 1.8];
  return [20, 1.0];
}
function stats(pid) {
  const C = CC.build(pid), n = k => C.list.filter(c => c.kind === k).length, total = C.list.length;
  const used = total + EV_EXTRA, spare = C.board.ways - used;
  const cable = C.list.reduce((a, c) => { const [m, p] = homeRun(c); return a + m * p; }, 0);
  const rcbo = C.list.reduce((a, c) => a + (RCBO[amps(c)] || RCBO[20])[0], 0), blanks = Math.ceil(Math.max(spare, 0) / 10) * BLANKS[0];
  return { C, n, total, used, spare, cost: { board: C.board.price, rcbo, blanks, cable: Math.round(cable) } };
}
const parts = c => c.board + c.rcbo + c.blanks, sum = c => parts(c) + c.cable;

function compare() {
  const S = Object.fromEntries(CC.plans.map(p => [p, stats(p)])), [a, b] = CC.plans, row = (k, f) => `<tr><td>${k}</td>${CC.plans.map(p => `<td>${f(S[p])}</td>`).join('')}</tr>`;
  const diff = sum(S[a].cost) - sum(S[b].cost);
  return `<div class="box"><h2>两个方案对比（还在讨论，可以发给别人一起看）</h2>
    <table class="sch cmp"><tr><th></th>${CC.plans.map(p => `<th><a href="#${p}" class="plan-pick ${p === cur ? 'on' : ''}">${esc(S[p].C.plan.name)}</a></th>`).join('')}</tr>
      ${row('<b>这个方案的特点</b>', s => `<ul class="notes">${s.C.plan.diff.map(x => `<li>${esc(x)}</li>`).join('')}</ul>`)}
      ${row('合计回路', s => `<b>${s.total}</b> 路`)}
      ${row('照明', s => `${s.n('WL')} 路：${s.C.list.filter(c => c.kind === 'WL').map(c => esc(c.name.replace(/（.*|\+.*/, '').replace('照明', ''))).join(' / ')}`)}
      ${row('插座', s => `${s.n('WX')} 路`)}
      ${row('专线', s => `${s.n('WP')} 路（烤箱、电梯、空调 ×2、充电桩）`)}
      ${row('配电箱', s => `${esc(s.C.board.model)}<div class="muted">${s.C.board.ways} 位 · ${esc(s.C.board.size)}</div>`)}
      ${row('剩余备用位', s => `${s.spare}（${esc(s.C.board.reserve.replace('预留 1 位：', '其中 1 位预留给'))}）`)}
      ${row('配电箱 + RCBO（Screwfix）', s => `<b>${money(parts(s.cost))}</b><div class="muted">箱子 ${money(s.cost.board)} + ${s.total} 个 RCBO ${money(s.cost.rcbo)} + 挡板 ${money(s.cost.blanks)} · <a href="#${s.C.pid}-buy">采购清单</a></div>`)}
      ${row('再加回配电箱的线（估算）', s => `约 £${s.cost.cable} → 合计约 <b>£${Math.round(sum(s.cost))}</b>`)}
      ${row('优势', s => `<ul class="notes">${s.C.plan.pros.map(x => `<li>${esc(x)}</li>`).join('')}</ul>`)}
      ${row('劣势', s => `<ul class="notes">${s.C.plan.cons.map(x => `<li>${esc(x)}</li>`).join('')}</ul>`)}
    </table>
    <p class="muted">合计差价约 £${Math.round(Math.abs(diff))}（${diff > 0 ? a : b} 贵）。房子是空的，人工差别很小，所以主要看材料。RCBO 按 Screwfix 现价（BG Fortress 单模块，清仓中）；回配电箱的线按每路 20–40 m（环路往返算双倍），2.5 mm² 约 £1 / m、4 mm² 约 £1.8 / m；房间里的线、底盒、插座两个方案一样，不计入。充电桩、电梯的 RCBO 先按 40A、20A 暂列，以设备要求为准。</p>
    <p class="muted"><b>决定的关键</b>：楼梯下放得下 483 mm 高的双排箱 → A；更在意简单、省、小箱子 → B。两个方案的插座点位、开关和灯都一样，只是分路不同。</p></div>`;
}

function oneLine(s) {   // incoming -> main switch + SPD -> busbar -> one RCBO per circuit (grouped) -> reserve + spare
  const rows = [];
  for (const k of Object.keys(GROUPS)) { rows.push({ head: GROUPS[k] }); s.C.list.filter(c => c.kind === k).forEach(c => rows.push({ c })); }
  rows.push({ reserve: true }); if (s.spare > 1) rows.push({ spare: s.spare - 1 });
  const RH = 26, top = 70, W = 1100, bx = 190, H = top + rows.length * RH + 30, o = [];
  o.push(`<text x="10" y="22" font-size="13" font-weight="bold">进线（供电公司电表 → 总闸）</text>`,
    `<path d="M10 40H90" stroke="#111" stroke-width="3"/><rect x="90" y="28" width="52" height="24" fill="#fff" stroke="#111" stroke-width="2"/><text x="116" y="45" font-size="11" text-anchor="middle">总闸</text>`,
    `<path d="M142 40H${bx}" stroke="#111" stroke-width="3"/><rect x="${bx - 30}" y="52" width="40" height="18" fill="#fff" stroke="#555"/><text x="${bx - 10}" y="65" font-size="10" text-anchor="middle">SPD</text>`,
    `<path d="M${bx} 40V${top + (rows.length - 0.5) * RH}" stroke="#111" stroke-width="5"/>`);
  rows.forEach((r, i) => {
    const y = top + i * RH + RH / 2;
    if (r.head) { o.push(`<text x="${bx + 14}" y="${y + 5}" font-size="12" font-weight="bold" fill="#1f4e79">${r.head}</text>`); return; }
    const col = r.c ? r.c.color : '#999', dash = r.c ? '' : 'stroke-dasharray="6 4"';
    o.push(`<path d="M${bx} ${y}H${bx + 60}" stroke="${col}" stroke-width="2" ${dash}/><rect x="${bx + 60}" y="${y - 9}" width="34" height="18" fill="#fff" stroke="${col}" stroke-width="2" ${dash}/>`,
      `<path d="M${bx + 94} ${y}H${bx + 150}" stroke="${col}" stroke-width="2" ${dash}/>`);
    if (r.c) o.push(`<text x="${bx + 77}" y="${y + 4}" font-size="10" text-anchor="middle" fill="${col}" font-weight="bold">${r.c.id}</text>`,
      `<text x="${bx + 158}" y="${y + 4}" font-size="12">${esc(r.c.name)}</text><text x="${W - 10}" y="${y + 4}" font-size="11" text-anchor="end" fill="#6b7280">${esc(r.c.br)}</text>`);
    else if (r.reserve) o.push(`<text x="${bx + 158}" y="${y + 4}" font-size="12" fill="#b7791f">${esc(s.C.board.reserve)}</text>`);
    else o.push(`<text x="${bx + 158}" y="${y + 4}" font-size="12" fill="#6b7280">其余备用 × ${r.spare}</text>`);
  });
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;min-width:760px;height:auto">${o.join('')}</svg>`;
}

function schedule(s) {
  const h = ['<table class="sch"><tr><th>编号</th><th>楼层</th><th>回路</th><th>带什么</th><th>断路器</th><th>线缆</th><th>备注</th></tr>'];
  for (const k of Object.keys(GROUPS)) {
    h.push(`<tr class="grp"><td colspan="7">${GROUPS[k]}（${s.n(k)} 路）</td></tr>`);
    for (const c of s.C.list.filter(x => x.kind === k))
      h.push(`<tr><td><span class="chip" style="background:${c.color}">${c.id}</span></td><td>${c.floor ? CC.FCN[c.floor] : '—'}</td><td>${esc(c.name)}</td>
        <td>${esc(c.count)}${c.letters ? `<div class="muted">灯字母 ${esc(c.letters)}</div>` : ''}</td><td>${esc(c.br)}</td><td>${esc(c.cable)}</td><td>${esc(c.note || '')}</td></tr>`);
  }
  h.push(`<tr class="grp"><td colspan="7">备用 ${s.spare} 位（${esc(s.C.board.reserve.replace('预留 1 位：', '其中 1 位预留给'))}）</td></tr></table>`);
  return h.join('');
}

function buy(s) {   // Screwfix shopping list for this plan
  const cnt = {}; s.C.list.forEach(c => { const a = RCBO[amps(c)] ? amps(c) : 20; (cnt[a] = cnt[a] || []).push(c.id); });
  const rows = [`<tr><td><a href="${s.C.board.url}" target="_blank" rel="noopener">${esc(s.C.board.model)}</a>（${s.C.board.code}）</td><td>1</td><td>${money(s.C.board.price)}</td><td>${money(s.C.board.price)}</td><td>配电箱，已带总闸和 SPD</td></tr>`];
  for (const a of Object.keys(cnt).map(Number).sort((x, y) => x - y)) { const [pr, code, path] = RCBO[a];
    rows.push(`<tr><td><a href="${SFX(path)}" target="_blank" rel="noopener">BG Fortress ${a}A RCBO</a>（${code}）</td><td>${cnt[a].length}</td><td>${money(pr)}</td><td>${money(pr * cnt[a].length)}</td><td>${cnt[a].join('、')}</td></tr>`); }
  const nb = Math.ceil(Math.max(s.spare, 0) / 10);
  if (nb) rows.push(`<tr><td><a href="${SFX(BLANKS[2])}" target="_blank" rel="noopener">BG 空位挡板 10 个装</a>（${BLANKS[1]}）</td><td>${nb}</td><td>${money(BLANKS[0])}</td><td>${money(BLANKS[0] * nb)}</td><td>盖住 ${s.spare} 个空位</td></tr>`);
  return `<h3 id="${s.C.pid}-buy" style="margin:12px 0 6px;color:var(--accent);font-size:13px">采购清单（Screwfix，含 VAT）</h3><table class="sch" style="min-width:0"><tr><th>产品</th><th>数量</th><th>单价</th><th>小计</th><th>用在</th></tr>${rows.join('')}
    <tr><td colspan="3"><b>合计</b></td><td><b>${money(parts(s.cost))}</b></td><td></td></tr></table>
    <ul class="notes"><li>RCBO 是 BG Fortress 单模块款，Screwfix 正在清仓（已被新款双向 RCBO 取代，约 £17.99 / 个，可能占 2 格）。趁清仓建议多买 2–3 个 20A / 32A 备着。</li>
    <li>充电桩、电梯的 RCBO 先别买，等定了型号按说明书配；以后接太阳能那一路要用新款双向 RCBO。下单前让电工看一眼这张单子。</li></ul>`;
}

function detail(s) {
  const B = s.C.board;
  return `<div class="box"><h2>${esc(s.C.plan.name)} · 单线系统图</h2>${oneLine(s)}</div>
  <div class="box"><h2>${esc(s.C.plan.name)} · 回路表</h2>${schedule(s)}</div>
  <div class="box"><h2>${esc(s.C.plan.name)} · 推荐配电箱</h2>
    <table class="sch" style="min-width:0">
      <tr><td>型号</td><td><b>${esc(B.model)}</b>（约 £${B.price}）</td></tr>
      <tr><td>可用回路位（装完总闸、SPD 后）</td><td>${B.ways}</td></tr>
      <tr><td>本方案占用</td><td>${s.total} 路 + 充电桩 RCBO 可能多占 ${EV_EXTRA} 格 = ${s.used}</td></tr>
      <tr><td>剩余备用</td><td>${s.spare}（${esc(B.reserve.replace('预留 1 位：', '其中 1 位预留给'))}）</td></tr>
      <tr><td>总闸 / SPD</td><td>${esc(B.main)} · ${esc(B.spd)}</td></tr>
      <tr><td>尺寸</td><td>${esc(B.size)}</td></tr>
      <tr><td>断路器</td><td>${esc(B.rcbo)}：每路一个，共 ${s.total} 个，必须同品牌单模块</td></tr>
      <tr><td>其他选择</td><td>${esc(B.alt)}</td></tr></table>
    ${buy(s)}
    <p class="muted">买之前问清 <b>usable ways</b>（装完总闸后还剩几个回路位）。21 和 22 模块只差一格，但不同厂家「22」的可用位可能差 3–4 个。让电工确认品牌 —— 他要给整套线路签字。</p></div>`;
}

const NOTES = `<div class="box"><h2>给电工的说明（两个方案通用）</h2><ul class="notes">
    <li>每一路都是带 30 mA 漏电保护的 RCBO：哪一路出问题只断哪一路。</li>
    <li>漏电：电脑、电视正常工作时对地漏电（实际约 0.5–1.5 mA / 台，上限 3.5–5 mA）；BS 7671 要求一路 30 mA RCBO 平时不超过 9 mA。A 方案一路一个「电脑 + 电视」房间；B 方案两个书房合一路（约 3–7 mA），两个书房各拉一根线回配电箱，误跳时挪一根线到预留位即可拆开。</li>
    <li>回路面积（IET On-Site Guide）：32A 环路 ≤ 100 m²；20A 径向 2.5 mm² ≤ 50 m²；32A 径向 4 mm² ≤ 75 m²。</li>
    <li>充电桩：一般 7 kW、单独 32A；安装前要通知供电公司（DNO），通常由充电桩安装商代办。</li>
    <li>总负荷：电梯 + 烤箱 + 2 台空调 + 充电桩 + 洗衣烘干同时用会很大。英国住宅进户一般 60–100A，请按实际功率算；不够可以给充电桩加负载管理，比升级进户便宜。</li>
    <li>煤气灶只要一个点火插座、冰箱和洗碗机经带保险开关，都接厨房 WX3；洗衣机 + 烘干机接洗衣房 WX4；烤箱 FCU 对应关系待现场定。电热毛巾架 ×2 经带保险开关接所在卫生间那一路。</li>
    <li>照明：按已购灯具估算一层室内约 680 W、户外约 60 W、二层约 320 W，全部 LED。GU10 筒灯必须选 LED（≤ 7 W），不得换卤素灯。</li>
    <li>大功率工具位置未定：插头式工具最大 13A；以后要固定接线的大设备用备用位另拉专线，趁墙打开可往储物间 / 后花园预埋一根空管。</li>
    <li>空调 2 台位置待定；电梯按厂家要求配隔离开关。断路器规格、线径为建议值，以电工按 BS 7671 / Part P 复核为准。</li>
  </ul></div>`;

let cur = CC.pick();
function render() {
  cur = CC.pick(); const s = stats(cur);
  document.getElementById('ver').textContent = s.C.plan.short;
  document.querySelectorAll('[data-plan]').forEach(b => b.classList.toggle('on', b.dataset.plan === cur));
  document.getElementById('main').innerHTML = `
    <div class="cards">
      <div class="card"><b>${s.n('WL')}</b>照明</div><div class="card"><b>${s.n('WX')}</b>插座</div><div class="card"><b>${s.n('WP')}</b>专线</div>
      <div class="card total"><b>${s.total}</b>合计（+ 总闸）</div><div class="card"><b>${s.spare}</b>备用位</div><div class="card total"><b>${s.C.board.ways}</b>位配电箱</div>
    </div>
    ${compare()}${detail(s)}${NOTES}
    <p class="muted">数据：灯和开关来自照明工具（${esc(CC.lightRev)}，照明页也能切换方案 A / B），插座点位来自 v6 PPT 插座页，${esc(CC.rev)}。</p>`;
}
document.querySelectorAll('[data-plan]').forEach(b => b.onclick = () => { location.hash = b.dataset.plan; });
window.addEventListener('hashchange', render);
render();
