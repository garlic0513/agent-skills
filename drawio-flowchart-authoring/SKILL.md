---
name: garlic-drawio-flowchart-authoring
description: "Generates and validates draw.io flowcharts. 【Garlic 原创】按七步流程（first 定边界 → then 列泳道 → 列动作 → 生成 XML → 几何校验 → 真渲染 → finally 打分）生成并验收 draw.io 业务流程图：先定边界与泳道，再列动作清单，然后写成数据生成 .drawio XML，接着跑几何校验（穿框/交叉），再做真渲染自查，最后按五维打分决定是否交付。USE FOR: 画流程图、泳道图、业务流程图、把 SOP/URS 画成图、流程图太乱/线穿框、流程图编号、流程图质量检查、读 .eddx/.vsdx/.drawio。含节点配色语义、泳道规则、编号规则、布局与路由铁律、单页自适应字号、质量五维打分卡、坑库，配 30 篇专题 reference 与 11 个可执行脚本。"
license: MIT
metadata:
  author: garlic0513（原创）
  version: "2.1"
  created: "2026-10-13"
  slimmed: "2026-10-28（SKILL.md 37.8k→约 4k tokens，细节下沉 references）"
---

# Drawio 流程图生成与验收

> ⭐ 一句话：**流程图不是画出来的，是"定义数据 → 生成 → 几何校验 → 真渲染 → 打分"出来的。**

## USE FOR:

- 「画个流程图 / 泳道图 / 业务流程图」「把这段流程画成图」
- 「这张图太乱 / 线穿过框 / 编号乱了 / 看不清」
- 要把 SOP、URS、岗位职责、会议口述的流程变成可编辑图
- 一次出多张图（一条业务域 10–40 条流程）
- 读别人发来的 `.drawio` / `.eddx`（万兴亿图）/ `.vsdx`（Visio）
- 判断一张图「能不能交付」（打分 / 体检 / 交付前自查）

## DO NOT USE FOR:

- 只要一张示意草图（手画或 Mermaid 更快）
- 客户已有成熟图、只改文字 → 见 [drawio-consistency-audit.md](references/drawio-consistency-audit.md)
- 思维导图、架构图（非流程类图形）
- 只想写文字流程说明、不要图 → 见 [process-description-writing.md](references/process-description-writing.md)

---

## 一、七步工作流（别跳）

```
① 定边界   起点是什么、终点是什么（不定边界必失控）
② 列角色   先定泳道（部门（岗位）或系统），不画框
③ 列动作   用文字列清单："谁 + 动词 + 对象"，此时还没有图
④ 生成     把 ②③ 写成数据（lanes / nodes / edges）→ 脚本生成 XML
⑤ 几何校验 折线穿框 / 交叉 / 折点数（脚本算，不靠肉眼）
⑥ 真渲染   用 draw.io 引擎渲染成图，自己先看一遍
⑦ 打分     质量五维自评，8 分以上才交付
```

⭐ **第③步最关键**：先写字、后画框。直接拖框的人，画到一半必然返工。

## 二、硬规则（已定稿，别自行发挥）

```
① 文字一律写在【图形内部】（图形自己的 label），不用浮动 text 单元格
② 视觉分歧不争论 → 直接出两版真渲染让用户挑
③ 改生成器用 patch / 整份重写，不用 sed；改完 grep 关键串确认（str.replace 遇转义引号会静默失败）
④ 泳道名 = 部门（岗位）或系统名；执行岗与复核岗必须分两条泳道；QC 检验与 QA 放行不能合并
⑤ 编号 = 流程开始 → 10 → 20 … → 流程结束（起止不编号，连续无空号）
⑥ 图的依据是【文档里的流程说明原文】，不是想象；泳道 = 原文每步的操作角色
```

## 三、节点与配色（配色只表达三件事）

| 类型 | 形状 | 填充 | 语义 |
|---|---|---|---|
| 起止 | 胶囊 | 无填充 | 流程开始 / 结束 |
| 操作·人工 | 直角矩形 | **白** | 人在系统里点/录 |
| 操作·自动 | 直角矩形 | **浅蓝 #DAE8FC** | 系统自动执行 |
| 操作·线下 | 直角矩形 | **浅灰 #EEEEEE** | 纸质/搬运/目检（不碰系统） |
| 判断·系统 | 菱形 | **浅蓝** | 系统校验后分支 |
| 判断·人为 | 菱形 | **浅灰** | 人看图/看货判断 |
| 子流程 | 双竖线框 | 同操作 | 调用另一张图 |
| 单据 | 矩形 + 右下角浅粉 #FDEDEC | — | 产生/打印的单据 |
| 系统标签 | 小方块 #FFF2CC 38×21 | — | WMS / ERP / RF |

⭐ 一句话记：**白＝人在系统里做，蓝＝系统自动做，灰＝不碰系统，粉＝单据，黄＝系统名。**

## 四、泳道

```
· 泳道 = 部门（岗位）或系统；列序按流程先后排，不按部门大小
· 泳道数 ≤ 6；执行/复核、QC/QA 不得合并
· 泳道紧贴（间距 0）或留固定走廊，全图统一
· ⭐ 泳道宽度会连带影响两个参数：宽泳道 → 菱形要加宽（可到 300）、
  「是/否」标签要按分支方向分左右放（窄泳道统一 +66）
```

⚠️ **泳道 z 序**：draw.io 层级 = XML 文档顺序，新泳道必须插在"其他泳道之后、节点之前"，append 到末尾会盖住节点。

## 五、编号规则

```
流程开始 → 10 → 20 → … → 流程结束

① 起止不编号；第一个动作从 10 起
② 步长全页统一（默认 10；密时用 5），必须连续无断号
③ 编号大小必须与【图上上下顺序】一致（不能 170 排在 120 前面）
④ 插节点：整体重排（首选，给旧→新对照表）或 15/25 中间号；禁止随手跳号
⑤ 交付前自查：按图上 y 顺序抓 ^(\d+)，必须严格递增且等差
```

若原文有自己的条目号（如 1、5、6、7、8），图内仍用 10/20 步长，另给「图编号 ↔ 原文序号」映射表。

## 六、布局与路由（治"线乱/穿框"）

**先选布局，再谈连线**：线乱多半是"相连节点在图上离太远"，调锚点救不回来。

| 布局 | 结构 | 适合 |
|---|---|---|
| A 垂直泳道 + 单列 | 一步一行 | 节点 ≤15 |
| B 垂直泳道 + 全局顺序号 | 跨泳道走走廊 | 中等复杂度 |
| C 横向泳道带 + 时间轴 | 一格一节点 | 展示型（宽度会爆炸） |
| D 泳道内两列（旁路左/主干中） | 异常节点占左列 | ⭐ 最常用，交叉降一个数量级 |

**两条铁律**：水平段只走全局行间隙；垂直段只走泳道间走廊（且偏移不得越界）。

⚠️ 更省事：跨泳道长线**不给 waypoints**，只给 `exitX/exitY + entryX/entryY`，交给 `orthogonalEdgeStyle` 自动避让——手算航点更容易穿框。

📄 锚点选择、6 类路由、四类布局实测数据：[routing-and-layout.md](references/routing-and-layout.md)、[flowchart-layout-strategies.md](references/flowchart-layout-strategies.md)

## 七、一条流程压进一页（自适应）

```python
avail  = H - top - bottom                      # A3: 1169-118-26 = 1025
pitch  = avail / (max_row + 1)                  # 行距
node_h = max(17, pitch - 8)                     # 元素高 ≤ 行距-8，否则相邻相切
dia_h  = max(20, pitch - 8)
dia_w  = min(300, lane_w - 100)                 # 菱形宽随泳道走
fs     = clamp(pitch * 0.245, 6, 10)            # 字号
```

| 节点数 | 泳道 | 行距 | 字号 | 观感 |
|:-:|:-:|:-:|:-:|---|
| 13 | 3 | 72 | 10pt | ✅ 舒服 |
| 35 | 5 | 33 | 7.9pt | ⚠️ 打印勉强 |
| 40 | 6 | 29 | 7.2pt | ❌ 糊 |

⭐ **可读上限 ≈ 34 节点/页（6 泳道）**。超过就三选一（合并节点 / 精简泳道 / 拆页），并明确告知"这是数学极限"。

**压到极限五处必改**：行号自动压缩 ｜ 菱形文字 verticalAlign=top ｜ 是/否标签移到侧外 ｜ 系统标签贴右侧外侧（泳道已是系统名就别贴）｜ 并行分支汇入要给固定端口 entryX=0.3/0.7。

📄 完整公式推导与实测：[expanded-flow-single-page.md](references/expanded-flow-single-page.md)

## 八、交付前：质量五维打分

| 维度 | 2 分标准 | 0 分表现 |
|---|---|---|
| 正确性 | 业务同事认可"我们就是这么干的" | 画成产品功能流（点菜单/填框） |
| 完整性 | 每条异常分叉都有终点 | 只有主流程 |
| 可读性 | 新人照图能独立做完 | 一页 40 节点糊成一团 |
| 规范性 | 配色/编号/泳道/图例全符合约定 | 自创图例、判定画成矩形 |
| 可维护性 | 加一步不用重画 | 连号编号、坐标硬编码 |

**每维 0–2 分，8 分以上才交付。** 📄 打分卡 + 12 条自检 + 12 条缺陷库：[quality-scorecard.md](references/quality-scorecard.md)

> 验收问句：**"明天来个新人，拿着这张图能不能独立把这活干完？"** 不能 → 缺的就是要补的。

## 九、常见坑（Top 10，全文见 pitfalls.md）

```
① 泳道内子节点坐标必须相对父容器（x=30），写绝对坐标 → 全堆到一处
② 新泳道 append 到末尾 → 盖住节点
③ f-string 里嵌三元表达式 → SyntaxError；先算变量再嵌
④ str.replace 遇转义引号静默失败 → 改完必须 grep 验证
⑤ 长脚本别用 heredoc 喂 python（报错被 2>/dev/null 吞掉）→ 先落 .py
⑥ 删组合节点（group）：按文字匹配删只删到子 cell，留下空白框 → 值→parent→整组删
⑦ 删判断节点要连它的两条出边一起想清楚
⑧ 图改了，文字说明表必须同步 → 跑图↔表 diff
⑨ 只看 XML 会漏文字溢出/标签压线 → 必须真渲染
⑩ 导出 PNG 按内容裁白（画布高常大于 frame 高）
```

📄 全部坑 + 改图模式 + 加泳道四件套：[pitfalls.md](references/pitfalls.md)、[generation-and-edit.md](references/generation-and-edit.md)

## 十、脚本（scripts/）

| 脚本 | 用途 |
|---|---|
| `drawio_swimlane.py` | 泳道图生成器：JSON spec → .drawio |
| `check_line_overlap.py` | 穿框 / 通道重合 / 菱形误用上下口 |
| `check_lines_per_page.py` | 逐页体检：穿框·压线·交叉·折点/线·总线长 |
| `parse_drawio.py` | 解析 .drawio（兼容压缩/未压缩），概览或 detail |
| `parse_eddx_geometry.py` | 解析 .eddx 几何（泳道横竖/带宽/落位） |
| `make_drawio_preview.py` | 真渲染预览页（配本地 http + 截图） |
| `drawio_multipage.py` | 多页合并 + 页间跳转 |
| `verify_drawio_multipage.py` | 多页逐页几何验证 |
| `template_style_diff.py` | 与参考模板样式逐项 diff |
| `audit_fig_table.py` | 图 ↔ 文档表格一致性核对 |
| `gen_data_dictionary_xlsx.py` | 数据字典三表（Excel） |

## Examples 示例（最小可跑 spec）

```json
// spec.json
{"lanes":[{"name":"仓储部（收货员）"},{"name":"质量部（QC）"}],
 "nodes":[
   {"id":"s","lane":0,"text":"流程开始","type":"start","y":0},
   {"id":"a","lane":0,"text":"10 扫码收货","type":"process","y":1},
   {"id":"d","lane":0,"text":"20 数量一致？","type":"decision","y":2},
   {"id":"b","lane":1,"text":"30 取样检验","type":"process","y":3},
   {"id":"e","lane":0,"text":"流程结束","type":"end","y":4}],
 "edges":[{"from":"s","to":"a"},{"from":"a","to":"d"},
          {"from":"d","to":"b","label":"是"},{"from":"b","to":"e"}]}
```

```bash
python3 scripts/drawio_swimlane.py spec.json out.drawio   # 出图
python3 scripts/check_lines_per_page.py out.drawio         # 体检：穿框/交叉/折点
python3 scripts/make_drawio_preview.py out.drawio          # 真渲染预览
```

期望结果：`check_lines_per_page` 报 穿框 0、压线 0、折点/线 ≤2。

## 故障排查 Troubleshooting

| 症状 | 原因 | 修法 |
|---|---|---|
| 节点全堆到左上角 | 子节点用了绝对坐标 | 改成相对父容器（x=30） |
| 新加的泳道里没有节点 | swimlane append 到末尾盖住了节点 | 插到"其他泳道之后、节点之前" |
| 线穿过节点框 | 相连节点距离太远 / 手算了航点 | 改布局，或去掉 waypoints 只给 exit/entry |
| 菱形文字压边框 | 菱形宽度没随泳道放大 | `dia_w = min(300, lane_w-100)` |
| 是/否标签压住旁边节点 | 标签偏移方向写死 | 按分支方向分左右（是→左，否→右） |
| 生成器改动没生效 | `str.replace` 遇转义引号静默失败 | 改完 `grep` 关键串确认 |

## 十一、交付前检查清单

```
□ 图能打开、页数/页名正确
□ 几何校验：穿框 0、压线 0、交叉 ≤ 节点数/4、折点/线 ≤ 2
□ 真渲染看过：文字不溢出、标签不压字、泳道里真有节点
□ 编号连续等差、与图上顺序一致
□ 配色只三色；泳道=系统名时节点不贴系统标签
□ 每条分叉有终点，每个判断有是/否
□ 图 ↔ 流程说明表逐节点一致
□ 五维打分 ≥ 8
```

## 自带评测（evals/ · 2026-10-28 建）

```
evals/
├── eval.yaml          waza schema 2.0（graders: must_exist / content_patterns / custom 几何）
├── tasks/T1~T9.yaml   10 题：基础画图 / 编号 / 泳道职责分离 / 判定标签 / 修图 / 负样本
│                     / T7a 大页只查几何(300s) / T7b 大页含视觉迭代(900s) / 两页子流程 / 超收短收三分支
├── fixtures/broken.drawio   修图任务用的坏样例（编号 10/20/45/170 + 悬空边 n45→n999）
├── runner.py          hermes -z 跑任务 → grader 打分；--mode with-skill|without-skill|both
└── optimize.py        用本 eval 当 reward 的轻量优化循环（DeepSeek 出锚点补丁）
```

```bash
python3 evals/runner.py --mode with-skill --tasks T1,T3,T4,T5   # 单跑
python3 evals/runner.py --mode both --tasks T1,T3               # A/B 对照
python3 evals/optimize.py --tasks T1,T3,T4 --dry                # 只诊断，不改文件
```

**基线（v2.1 · 10 题，2026-10-28 二轮实测）**

| 有技能 | 无技能对照 |
|---|---|
| **8/8 通过**（穿框 0、交叉 0；T7a 43 节点 178s 通过） | 2/4（T1 穿框 60、T3 穿框 50、T9 穿框 30） |

⭐ 两个数记住就够：**看穿框和交叉，不看"能不能出图"**。
⭐ **区分度只有 3 题**（T1/T3/T9，全是几何穿框类）；T2/T4/T5/T6/T8 双模式都过 = 无信息量。
⚠️ **T7 原版超时（420s）不是能力问题、是任务设计问题**：要求"30+ 节点 + 顺带真渲染视觉迭代"跑不完；
拆成 T7a（只查几何，300s，178s 过）与 T7b（视觉迭代，900s）后才有意义。重任务必须拆粒度。
⚠️ 有技能已 **8/8 打满 → 没有失败样本 → optimize.py 无输入**；without-skill 的失败是"功劳证明"，
不是"待改点"。要继续优化只能加严判据或加更难任务（跨系统边界页 / 状态机图 / 6 泳道 40+ 节点）。

⭐ 结论值得记住：**不加载技能模型也能出图、编号也对，但线穿节点框 50–60 处** ——
本技能的价值在"能不能交付"，不在"会不会画"。改 SKILL.md 后必须重跑本 eval 对比基线，
且 grader 必须量几何质量（只查"文件存在"会让 A/B 零差异）。

⚠️ `hermes -z` 不跟随 shell cwd → runner 已把绝对输出目录写进 prompt，别自己再写裸 subprocess（会全 0 分）。
方法论（含 waza 静态检查、SKILL.md 瘦身、优化循环）：技能 `agent-skill-optimization`。

## 参考资料索引

> 全部为按需加载（progressive disclosure）：SKILL.md 只留骨架，细节下沉到这里。

**核心方法**
- [流程图质量五维打分卡（自评 / 互评 / 交付前体检）](references/quality-scorecard.md)
- [节点怎么写：业务为中心 / RF 端 / 配色三问答](references/flowchart-node-writing.md)
- [RF（手持终端 / PDA）在流程图里怎么画 + 现场作业时间线](references/rf-operations-in-flowcharts.md)
- [锚点·航点·路由·布局策略（治连线穿框/交叉）](references/routing-and-layout.md)
- [泳道流程图布局策略（蚂蚁搬家式试错记录 + 贪吃蛇正解）](references/flowchart-layout-strategies.md)
- [全展开版流程图 · 单页 A3 自适应引擎（方案C）](references/expanded-flow-single-page.md)
- [先全展开后提子流程 · 单页自适应字号](references/two-phase-and-single-page.md)

**画法与规范**
- [公司交付规范（图名/三出口/条件标记/待确认面板/判定节点判据/复核控制层级）](references/conventions-company.md)
- [业务为中心的画法约定（文档为唯一依据 / 以客户草稿为模板）](references/conventions-business.md)
- [生成 drawio XML 与改图操作（骨架/样式/删节点/加泳道）](references/generation-and-edit.md)
- [坑库与工具噪音（openpyxl 等）](references/pitfalls.md)

**文件解析与交付**
- [解析 .eddx / .vsdx / .drawio（读别人的图）](references/parsing-files.md)
- [解析 .eddx 几何（读懂用户/客户发来的亿图草稿）](references/eddx-geometry-parsing.md)
- [接手别人的 .drawio：一致性体检 + 修复（2026-10-22 实测）](references/drawio-consistency-audit.md)
- [树状总览 · 产品反推 · 多页下钻 · 边界页 · 数据字典](references/advanced-patterns.md)
- [交付、格式转换与 MCP 真连接](references/delivery-and-mcp.md)

**渲染与 MCP**
- [真连接 draw.io（MCP live connection）—— 装法 + 坑](references/drawio-mcp-live-connection.md)
- [⭐ 服务器上做 draw.io 真渲染自查（不再"我无法预览，请你自己打开看"）](references/drawio-real-render-verification.md)

**流程说明**
- [流程说明（4.x.3）怎么写：图与说明是一对](references/process-description-writing.md)
- [4.x.3 流程说明 · 模板规格与仿写参考](references/process-description-template.md)

**进阶**
- [程序化新增单页流程（坐标纪律 · 2026-10-22 实测）](references/programmatic-page-build.md)

