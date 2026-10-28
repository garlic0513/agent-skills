# 解析 .eddx / .vsdx / .drawio（读别人的图）

> 从 SKILL.md 下沉（2026-10-28 瘦身重构）。原属 garlic-drawio-flowchart-authoring。

```python
import zipfile, re
z = zipfile.ZipFile('xxx.eddx')
for n in z.namelist():
    print(n, z.getinfo(n).file_size)

# 文字都在 pages/pageN.xml 里（多页则 page1/page2…）
xml = z.read('pages/page1.xml').decode('utf-8', errors='ignore')
texts = re.findall(r'>([^<>]{1,90})<', xml)
cn = []
for t in texts:
    t = t.strip()
    if t and re.search(r'[\u4e00-\u9fa5]', t) and t not in cn:
        cn.append(t)
print(cn)   # → 流程图里所有节点文字（含判断条件、规则说明）
```

**要点**
- `thumbnail.jpeg` = 内嵌缩略图，可提取，但**分辨率低**（只能看轮廓，读不了字）
- 文字节点顺序 ≈ 图形创建顺序，不是流程顺序 → 需要自己按编号/逻辑重排
- `.vsdx` 同理（也是 ZIP），文字在 `visio/pages/*.xml`
- ⭐⭐ **别停在「提文字」——坐标也要提，而且往往更重要**：
  用户发来的草稿，光看文字读不出 **泳道是横是竖 / 每条带多高 / 流程怎么绕圈**，
  而这些恰恰是「该抄什么」的关键。本次只提文字 → 我按「垂直泳道」重画 → 被连否 8 版；
  解析几何后发现**他自己的版本是横向泳道带**（7 条横带堆叠），方向从一开始就猜错了。
  → 解析方法（Transform 字段 / SwimLane 判定 / 横向带识别 / 实测数据）见
  `references/eddx-geometry-parsing.md`，可直接跑 `scripts/parse_eddx_geometry.py`。

### 📎 配套文件（先看这些，再动手）

| 文件 | 用途 |
|------|------|
| ⭐⭐ `references/quality-scorecard.md` | **流程图质量五维打分卡**：正确性/完整性/可读性/规范性/可维护性（各 0–2 分，8 分才可评审）· 12 条快速自检 · 12 条高频缺陷库（症状→病因→修法）· 四级练习阶梯 · 每图五步法（定边界→列角色→列动作→连判定→三遍查）· 素材来源 |
| ⭐⭐ `references/flowchart-node-writing.md` | **节点怎么写**：业务为中心 vs 产品为中心（+两个一秒判据、三种图分工）· RF 端不是节点是标签（三错误 + 分工口径）· 配色三问答（蓝底语义 / 泳道标题条易混 / 打印类要加粉色单据标签）· 「只要编号对照表自己改图」的交付纪律 |
| `scripts/drawio_swimlane.py` | 泳道图生成器：智能锚点 + 菱形三出口 + 顶部图名，含 3 项自查 |
| `scripts/check_line_overlap.py` | ⭐ **交付前必跑**：几何校验连线是否穿过节点框 + 通道重合 + 菱形误用上下口（三道一起查） |
| `scripts/check_lines_per_page.py` | ⭐ **逐页体检**（穿框/压线/**交叉**/折点每线/总线长）：判"线乱不乱"的量化指标，支持 parent="1" 绝对坐标节点。经验基线 折点/线≤2.0、交叉≤节点数1/4 |
| ⭐ `scripts/template_style_diff.py` | **交付前样式对齐**：公司模板 vs 我方按 frame/lane/判定/子流程/节点/连线 六类抽样 diff，只报关键属性差异 + 给修法（治"用户一条条挑视觉"） |
| ⭐⭐ `scripts/make_drawio_preview.py` | **真渲染预览页生成器**：`.drawio` → `webapp/_preview/pN.html`，配本地 http.server + browser 截图 = 交付前自己验收（见下条 reference） |
| ⭐⭐ `references/drawio-real-render-verification.md` | **服务器上做 draw.io 真渲染自查**：draw.war 解包 webapp + `viewer.min.js` 挂载 + 本地 http + 浏览器看图。能抓到菱形文字溢出 / 标签压线 / 形状没生效 / 跨线弧没画出来；含"把公司模板自己也渲染出来并排对齐"的方法 |
| `scripts/drawio_multipage.py` | 把多个 .drawio 合并成【多页可下钻】mxfile + 注入页间跳转链接（见 §十三） |
| ⭐ `references/flowchart-layout-strategies.md` | **布局四选一实测对比**（垂直泳道/全局顺序/横向时间轴/⭐横向蛇形=贪吃蛇）＋ 画布尺寸实测 ＋ 沟通纪律。**连线穿框/太乱先读这篇** |
| `references/wms-flow-architecture.md` | ⭐ 流程体系三件套模板（一级/二级清单 · 流程树 · 选项清单）＋归类判据 |
| `references/pharma-wms-glossary.md` | 药企 WMS 行话速查（监管码/请验/复验/让步收货/U8C/委托加工）·可直接照抄的回答口径 |
| ⭐⭐ `references/wms-inventory-rules.md` | **业务规则口径库**：出库分配【两层模型】+ 可直接进 URS 的排序键 + 库存状态【三态+锁定 / 3×2 矩阵】+ 待检区×状态字段缺一失效 + Hold 牌要素 + 监管码全链路（生产线 5 步 / 仓库 5 步 / WMS 边界）+ 法规锚点（211.80 / 211.86 / Annex 11·15·19） |
| `references/garlic-full-branch-flowchart-method.md` | ⭐⭐ 全分支流程图工作法 FBF（用户原创方法论）：四步法 · 通用分支库 18 条 · 选项怎么长在图里 |
| `references/scope-change-and-gap-audit.md` | 客户环境/接口范围变化 → 反查 URS 失效条款 + 全量扫图 + 风险建议（验证顾问标准动作） |
| ⭐ `references/eddx-geometry-parsing.md` | **解析 .eddx 几何**（泳道横竖 / 带宽 / 圈数 / 节点落位）＋ 实测案例：用户自己的草稿是「横向泳道带」 |
| ⭐ `scripts/parse_eddx_geometry.py` | 跑它 → 打印泳道清单（含坐标/宽高）+ 节点文字清单，用于读懂用户/客户发来的亿图草稿 |
| ⭐ `scripts/parse_drawio.py` | 解析任意 `.drawio`/mxfile（**兼容未压缩 + 压缩两种 `<diagram>` 形态**）：概览每页泳道/形状/连线数，`detail 关键词` 打印某页节点与连线标签。读公司模板/客户图必用 |
| ⭐ `scripts/verify_drawio_multipage.py` | **多页**文件的几何验证（逐页线段×节点矩形求交）→ 交付话术直接用它的"0 处穿框"数字 |
| ⭐⭐ `references/company-flowchart-template.md` | **公司企业模板体系**：37 页结构 + 角色泳道/序号步长10/系统小标签/配色语义 + 与"系统泳道"旧风格的 9 处差异 + 抄模板去残留清单 |
| `references/flow-description-from-drawio.md` | ⭐ **按图反写流程说明**：两种体例（叙述式 4.x.3 / 表格式四列）· 从 .drawio 自动提节点清单的代码 · ⭐ 用户发来新一版图时**先做页级 diff 再定范围**（10 页→40 页这种是换体系）· 每节必带的分支说明/待确认/⭐图面不一致 9 类体检表 · md→docx 收口 |
| ⭐⭐ `references/drawio-consistency-audit.md` | **接手别人发来的 .drawio：体检→修复→复验**：七项体检（断链/重号/重名泳道/标题未改/语义重复/编号混用）· ⚠️ cells 的父是 `<root>` 不是 mxGraphModel（`m.remove` 必报错）· 改名整串替换（清掉 `<div><span>` 脏壳）· 补节点要复制同页样式 + 对齐行距 · 交付用「原问题→处理→状态」表。**用户说"把这些问题修掉"时先读这篇** |
| ⭐⭐ `references/programmatic-page-build.md` | **程序化新增单页**：单泳道垂直流的五条坐标纪律（左右列留 30px / 同 y 必须相等 / 菱形 170×80 / 泳道=内容+35px）· ⭐ 是/否用**独立 text 小节点**而非 edge label（label 会叠在一起并压 WMS 黄标签）· ⭐ 连线必须给固定端口 exit/entry 否则同 y 节点间出现回插回环 · 样式字典 + 新页骨架 · 两个业务写法（扫托的一致性判定 / 扫箱的旁路处置）· 三轮验收节奏 |
| ⭐⭐ `references/fill-client-docx-template.md` | **在甲方/公司模板 docx 上批量填表**（蓝图 V1.0 → V1.1）：保留模板样式只填内容 · 四个必踩坑（清空行连带删表头 / `p is h` 失效 / `addnext` 插到标题后 / 找表偷了下一节的表）· 内容优先级（已定稿 md → drawio 节点 → 关键词规则）· 交付要声明哪几节是规则补写 |
| ⭐ `references/docx-figure-and-toc-surgery.md` | **在别人的 docx 里换图 / 并排 / 重建静态目录**：按「流程图」四级标题定位换图 · ⚠️只清标题下会漏掉概述上方的重复旧图 · 并排图按**等高**（等宽会顶端错位）· 列宽 gridCol 与 tcW 都要改 · 静态 TOC 条目重建（页码从 PDF 反查 + 显式 tab_stop 点线）· 变更清单按用户手上版本做基线 |
| ⭐ `references/docx-cn-font-and-justify.md` | **中文 docx→PDF 字距被拉开的两层原因**：justify 继承（中文两端对齐只能在字间加空隙）+ 服务器缺楷体导致逐字回退 → `apt install fonts-arphic-ukai` + fontconfig 别名 + `align or LEFT` 兜底 · 台词稿排版三条（字号/整段不跨页/并排等高） |
| ⭐⭐ `scripts/audit_fig_table.py` | **图↔表一致性核对**：逐节把 docx「流程描述」表的节点名与对应 drawio 页节点双向 diff，输出"表有图无 / 图有表无"。交付蓝图前必跑 —— 评审最容易抓的不是线乱，是**图和说明对不上** |
| `references/md-to-docx-deliverable.md` | **流程说明 md → Word 收口**：⚠️`/tmp/xlsxenv` 的 python-docx 已坏 → 新建 `/tmp/docxenv`（pip install python-docx pymupdf）· 现成转换器 `<工作目录> SRC/OUT 即复用）· 五个坑（正则字符类 `[:-\\s|]` 报 bad character range / 封面重复 skip_intro / wikilink 未剥 / PAGE 域不刷新 / 表头不跨页重复）· 验证=转 PDF 数页数+抽检文字 · **流程说明四列体例**（3.x.1 概述 / 3.x.2 图 / 3.x.3 步骤-节点-处理逻辑-输入-输出） |
| ⭐⭐ `references/expanded-flow-single-page.md` | **全展开版单页 A3 自适应引擎**（方案C）：行距/字号公式 · 实测 35 节点→7.9pt / 38→7.5pt · **≥36 节点就该拆两页** · 紧凑布局三处跟随（系统标签贴右侧 / 结束节点回泳道 / 长文案改写）· 复查清单 · 本机 `flowgen_C.py` 用法 |
| ⭐ `references/pharma-role-lanes.md` | **药企角色泳道怎么划**：从 URS 扒部门原词的方法（关键词计数 + 取原句）+ ⭐QA/QC 必须分两条泳道 + 各流程泳道分配表 + ⭐起止节点不编号 + 推演版/交付版两阶段策略 |
| ⭐ `references/over-short-receipt-handling.md` | **超收/短收处置**：容差机制（原辅料 0 容差 / 包材 ±2%）+ 五步（登记差异→隔离→采购确认→经理审批→按批准入库）+ 三条硬要求（隔离 / 确认≠审批 / 改单留痕）+ 13 节点子流程画法 + 五个坑 + 与复核·审批·放行·让步收货的分界 |
| ⭐⭐ `references/gmp-concepts-plain-language.md` | **面向非药企同事的通用表述库**：术语→人话替换表 · 「复核=第二人核对」三件套（一句话/银行柜台类比/三个不是什么）· 流程说明「处理逻辑」≤25 字规则 · 先收货后质检 / 复核属收货末环 / 上架两次 → 三个高频口径 · 向 PM 复述式确认大框架的话术 · 四个必问 Q&A · 可直接发群的说明块 |
| ⭐⭐ `references/template-scoping.md` | **模板范围裁剪**（客户问「我们要走哪些流程」时）：三档分类（必做/待确认/不做/二期）+ ⚠️超模板项需邮件申请偏离 + **六个判据一次问清**（单仓？委外？整箱？托码？库位分级？接口？）+ 结论要带百分比。⚠️ 判据会翻案（本次"扫托不做"因托码在推进而改判） |

---

和 `.eddx` 不同，`.drawio` 是纯 XML（`<mxfile><diagram>…`），但**`<diagram>` 的内容有两种形态**，
只处理一种必失败（本次 37 页公司模板连续 37 页全报 `no element found: line 1, column 0`）：

```python
# A) 未压缩：diagram 下有子元素 <mxGraphModel>  → d.text 是 None！
#    直接 ET.fromstring(d.text or '') 必然报 no element found
# B) 压缩：d.text = base64(raw deflate) 再 urldecode 的字符串
#    解码顺序必须是 base64 → zlib.decompress(data, -15) → urllib.parse.unquote

def get_model(d):
    m = d.find('mxGraphModel')
    if m is not None:            # A
        return m
    t = (d.text or '').strip()
    if not t: return None
    try:                         # B
        return ET.fromstring(urllib.parse.unquote(
            zlib.decompress(base64.b64decode(t), -15).decode('utf-8')))
    except Exception:
        return None
```

⭐ 直接跑 `scripts/parse_drawio.py 文件.drawio`（概览）/ `… detail 关键词`（明细），别重写。
⭐ 拿到页名清单先看**页数 + 页名**——公司模板的页名本身就是它完整的流程清单（本次 37 页=主流程6+流程9+子流程22）。
