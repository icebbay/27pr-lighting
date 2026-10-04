# 27PR 照明施工图 · 平面图照明 workflow

27PR 住宅改造的灯具、开关、回路资料，以及一个网页工具。在网页上可以直接按开关试灯、看每盏灯的线路从配电箱 AL1 怎么接到开关、再接到灯。

**在线打开（不用安装）：https://icebbay.github.io/27pr-lighting/**

另外两页（照明页不变），都有 **方案 A / 方案 B** 切换，链接末尾加 `#A` 或 `#B` 可以直接打开某个方案，方便发给别人讨论：
- **配电箱 AL1（两个方案对比）**：https://icebbay.github.io/27pr-lighting/lighting_tool/board.html （A 专业 18 路 vs B 精简 15 路：路数、配电箱、备用位、材料估算、优缺点，以及各自的单线图和回路表）
- **插座 / 动力**：https://icebbay.github.io/27pr-lighting/lighting_tool/power.html#A 、[#B](https://icebbay.github.io/27pr-lighting/lighting_tool/power.html#B) （每个插座、电器属于哪一路，点一路只看这一路）

3D 漫游（可以在房子里走、开门；与本照明图同一版户型 v38）：https://icebbay.github.io/27pr-cgi/walkthrough/

> 状态：照明 Rev G（4 路）。全屋回路还在 A / B 两个方案之间讨论：A 专业 18 路（照明 4 + 插座 9 + 专线 5，BG CF236MS31 31 位），B 精简 15 路（照明 2 + 插座 8 + 专线 5，BG CF22MS19-01 19 位）。规格为建议值，需要电工按 BS 7671 / Part P 复核。

## 施工图（Rev G）

| 文件 | 内容 |
|---|---|
| [一层 · 英式](lighting_tool/drawings/27PR_一层照明施工图_RevG_英式.pptx) | E-GF-00 索引 → 01–03 分区放大 → 04 开关面板表（逐键）→ 05 回路表 |
| [一层 · 国标](lighting_tool/drawings/27PR_一层照明施工图_RevG_国标.pptx) | 电施-01 说明 / 图例 / 灯具表 → 02 全层平面 → 03–05 放大 → 06 AL1 系统图 → 07 面板表 + 回路表 |
| [二层 · 英式](lighting_tool/drawings/27PR_二层照明施工图_RevG_英式.pptx) | E-FF-00–04 |
| [二层 · 国标](lighting_tool/drawings/27PR_二层照明施工图_RevG_国标.pptx) | 电施-11–16 |

不想下载 PPT 的话，每一页的图片在 [`lighting_tool/drawings/png/`](lighting_tool/drawings/png/)。

**Rev G：全屋按专业方案定为 18 路，照明合为 4 路**
- 照明：一层前区 WL1（22 盏）、一层后区 WL2（14 盏，原 WL2 + WL6）、户外 WL3（7 盏）、二层 WL4（16 盏，原 WL4/5/7）。按已购灯具估算一层室内约 680 W、二层约 320 W，LED 负载很小；分路是为了跳闸时不整屋黑（BS 7671 314.1），楼梯壁灯和吊灯在不同回路。
- 插座 9 路：一路最多一个「电脑 + 电视」房间（每台对地漏电 1–5 mA，30 mA RCBO 平时不超过 9 mA）；厨房、洗衣、户外（32A，可用花园工具）各自一路。
- 专线 5 路：烤箱、电梯、空调 ×2、充电桩。配电箱预留 1 位给大功率工具。

**Rev F 相对 Rev E 的改动：二层照明也按区域分，3 路**

| 断路器 | 区域 | 开关 |
|---|---|---|
| WL7（新） | 主卧区：主卧、北卫 | S3、S4、S9 |
| WL4 | 西区：衣帽间、盥洗室、西卫、卧室 2 | S1、S2、S5、S6、S7 |
| WL5 | 东区：走廊、卧室 3、楼梯、书房、后卫 | S8、S10–S14 |

配电箱 AL1 现在一共 7 路照明（一层 4 路、二层 3 路）+ 1 路备用。

**Rev E 相对 Rev D 的改动：一层照明按区域分 4 路，配电箱里每区一个断路器**

| 断路器 | 区域 | 开关 |
|---|---|---|
| WL1 | 前厅：门廊、门厅、起居室、G07 餐厅、楼梯 | S1–S6 |
| WL2 | 侧厅：G15 区、卫生间（含排气扇） | S8、S9、S10 |
| WL6（新） | 厨房：厨房、吧台区、洗衣房 | S13、S14 |
| WL3 | 户外：后花园壁灯、围栏地灯 | S7、S11、S12、S15 |

厨房原来和侧厅共用 WL2，现在单独一路，各区互不影响。网页里开一盏灯，只有 AL1 到这个开关的那一段供电线会流动，不再整路一起动；各路从 AL1 出来并排走，不重叠。

**Rev D 相对 Rev C 的改动**
1. 一层 S7 改为双联中途开关，控后花园壁灯 p 和围栏地灯 q：p、q 三控 = S11、S12（两路）+ S7（中途）。G15 区筒灯 l 改回 S8、S9 双控。
2. 一层 S6（楼梯底）控制的是二层楼梯吊灯 F06（在楼上）。现在一层平面上也在 F06 的对应位置画了虚线灯，标“二层楼梯吊灯 F06（在楼上，S6 控）”，网页里按 S6 它也会亮。
3. 网页工具：开关面板贴近自己的安装点，不再被挤到远处（原来 S2 的面板画在 MK 旁边，容易看错）；面板到安装点的引线改成红色。

**Rev C 相对 Rev B 的改动**
1. 门廊壁灯 G25（回路 c）改由 WL1（一层前区）供电，不再从后面的 WL3 户外回路拉线到前门。门厅开关 S1 只接一路 WL。
2. 取消卫生间排气扇隔离开关（原一层 S11、二层 S3、S16）。排气扇接所在卫生间的灯回路（随灯开、延时关）。电工请确认所选风扇是否另需维修隔离开关。
3. 开关编号重排，没有空号：一层 S1–S15，二层 S1–S14。楼梯吊灯 F06 三控 = 一层 S6 + 二层 S12（两路）+ 二层 S11 键 2（中途）。

## 网页工具怎么用

- **试灯**：平面上每个开关旁的小面板，每个键都可以点（键上的字母 = 它控制的回路）。双控、三控在任意一处都能开关，一楼和二楼的楼梯灯也能互相控制。
- **看线路**：
  - 粗线 = AL1 引出的回路 WL（颜色区分 WL）；
  - 细线 = 同一字母的灯串在一起；
  - 点线 = 开关到灯；
  - 红色长虚线 = 双控 / 三控之间的联络线。
  - 正在亮的灯，线路上会有流动的虚线。
- **点一盏灯**：只高亮这盏灯的整条线路（AL1 → WL → 开关 → 灯），右边列出经过的每一级。
- **电路图**：AL1 母线 → 各 WL 断路器 → 开关（两路 / 中途）→ 灯。可以点开关，也可以点断路器做分闸试验。
- **编辑**（给设计用）：放开关（自动贴墙、放在门锁侧）、选键后点灯建立控制关系、调 WL、规则检查、保存 JSON。

手机、电脑浏览器都能打开。也可以下载整个仓库（Code → Download ZIP），离线双击 `lighting_tool/index.html` 使用。

## 给设计 / 出图的人

需要 Python 3 和 `python-pptx`；预览图要本机装有 PowerPoint。

```bash
# 本地服务（网页里的「生成 PPT」按钮要用）
python lighting_tool/server.py            # 然后打开 http://127.0.0.1:8765/

# 直接用 JSON 出图
FLOOR=GF LIGHTING_JSON=lighting_tool/lighting_GF.json DST_OVERRIDE=out.pptx python make_lighting_drawings.py      # 英式
FLOOR=GF LIGHTING_JSON=lighting_tool/lighting_GF.json DST_OVERRIDE=out.pptx python make_lighting_drawings_cn.py   # 国标
```

| 路径 | 说明 |
|---|---|
| `lighting_tool/lighting_GF.json`、`lighting_FF.json` | 当前数据（Rev G）：灯、开关面板、逐键、回路、WL、配电箱 |
| `lighting_tool/ref_RevB/`、`ref_RevC/`、`ref_RevD/` | 历史数据；`apply_revC/D/E.py` 依次由上一版生成下一版 |
| `lighting_tool/walls_*.svg` | 墙体（Blender 1.2 m 剖切，来自 `source_pptx/`） |
| `make_lighting_drawings.py` / `_cn.py` | 英式 / 国标出图脚本 |
| `lighting_tool/build_power.py` | 从 v6 PPT 插座页读插座点位（按两页共有的墙体换算坐标），按方案 A / B 分回路 → `power_*.json`、`power_plans.json`、`power_data.js` |
| `lighting_tool/power.html`、`board.html` | 插座 / 动力页、配电箱页（`circuits.js` 按方案合并照明 WL + 插座 WX + 专线 WP；方案取自链接 `#A` / `#B`） |
| `source_pptx/` | 用户标注的户型 PPT（墙体、灯位、开关位置点） |
| `照明施工图_工作流程.md` | 规则、标注约定、出图规范、测试计划 T1–T6 |
| `lighting_tool/screenshots/` | 测试截图（T1–T5、试灯、追踪、电路图） |

测试：用 Rev B 数据回放，出图与原 Rev B 逐页完全一致（`lighting_tool/compare_pptx.py`）。T3（新增开关）、T4（规则检查）、T5（双控识别）都已在网页上实测通过。还没有做的：T6（与 Blender 模型双向同步）。
