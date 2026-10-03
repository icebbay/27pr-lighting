# 27PR 照明施工图 · 平面图照明 workflow

27PR 住宅改造的灯具、开关、回路资料，以及一个网页工具。在网页上可以直接按开关试灯、看每盏灯的线路从配电箱 AL1 怎么接到开关、再接到灯。

**在线打开（不用安装）：https://icebbay.github.io/27pr-lighting/**

> 状态：Rev C（2026-10-03）。回路划分（WL1–WL5）和配电箱 AL1 的位置是暂定的，需要电工按 BS 7671 / Part P 复核。

## 施工图（Rev C）

| 文件 | 内容 |
|---|---|
| [一层 · 英式](lighting_tool/drawings/27PR_一层照明施工图_RevC_英式.pptx) | E-GF-00 索引 → 01–03 分区放大 → 04 开关面板表（逐键）→ 05 回路表 |
| [一层 · 国标](lighting_tool/drawings/27PR_一层照明施工图_RevC_国标.pptx) | 电施-01 说明 / 图例 / 灯具表 → 02 全层平面 → 03–05 放大 → 06 AL1 系统图 → 07 面板表 + 回路表 |
| [二层 · 英式](lighting_tool/drawings/27PR_二层照明施工图_RevC_英式.pptx) | E-FF-00–04 |
| [二层 · 国标](lighting_tool/drawings/27PR_二层照明施工图_RevC_国标.pptx) | 电施-11–16 |

不想下载 PPT 的话，每一页的图片在 [`lighting_tool/drawings/png/`](lighting_tool/drawings/png/)。

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
| `lighting_tool/lighting_GF.json`、`lighting_FF.json` | 当前数据（Rev C）：灯、开关面板、逐键、回路、WL、配电箱 |
| `lighting_tool/ref_RevB/` | Rev B 原始数据（测试标准答案）；`apply_revC.py` 由它生成 Rev C |
| `lighting_tool/walls_*.svg` | 墙体（Blender 1.2 m 剖切，来自 `source_pptx/`） |
| `make_lighting_drawings.py` / `_cn.py` | 英式 / 国标出图脚本 |
| `source_pptx/` | 用户标注的户型 PPT（墙体、灯位、开关位置点） |
| `照明施工图_工作流程.md` | 规则、标注约定、出图规范、测试计划 T1–T6 |
| `lighting_tool/screenshots/` | 测试截图（T1–T5、试灯、追踪、电路图） |

测试：用 Rev B 数据回放，出图与原 Rev B 逐页完全一致（`lighting_tool/compare_pptx.py`）。T3（新增开关）、T4（规则检查）、T5（双控识别）都已在网页上实测通过。还没有做的：T6（与 Blender 模型双向同步）。
