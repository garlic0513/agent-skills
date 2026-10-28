# 生成 drawio XML 与改图操作（骨架/样式/删节点/加泳道）

> 从 SKILL.md 下沉（2026-10-28 瘦身重构）。原属 garlic-drawio-flowchart-authoring。

```
旧风格（本技能 §十 及以下全部内容）= 系统泳道 + 层级编号 + 单张全景 + 右侧待确认面板
  → 用途：内部推演 / 跟自己过流程 / 信息密度高

⭐ 公司模板风格 = 角色泳道 + 序号步长10 + 系统小标签 + 主流程/子流程分页下钻
  → 用途：⭐ 对客户、对公司交付（客户和领导看的就是这个）
  → 完整规范 + 生成器写法：references/company-flowchart-template.md
```

⚠️ 用户说「**这是公司流程图模板**」= 指令，不是分享：**后续同类图一律按模板重画**，
不要继续用自己的风格交付。本次因此把入库 5 个主流程 + 3 个通用子流程整套重画成 8 页。

⭐ **角色泳道的角色名：最终定稿格式 = 「部门（岗位）」**，例：`仓储部（仓管员）`

```
模板写：采购员 / 仓管员 / 质检员 / 作业人员            ← 只有岗位，没部门
药企客户实际部门：采购部 / 仓储部 / 质量控制部 / 质量保证部 / 车间 / 销售部
⭐ 用户最终要求：⭐ 部门 + 括号里的岗位 = 仓储部（仓管员）、质量控制部（QC检验员）
  → 不要只写部门（"仓储部"），也不要只写岗位（"仓管员"）——两者都要
  → 从客户 URS 里 grep 部门关键词 + 取原句定名（别自己编部门名）
→ ⭐⭐ 药企 QA（放行审批）与 QC（取样检验）必须分两条泳道 ——
   合并会抹掉「放行」这个关键控制点，审计追溯也断（曾判断错，被用户纠正）
→ ⭐ 仓储部内部分不分「验收员 / 保管员」先别自己拆：默认一条「仓储部（仓管员）」，
   客户确认分工后再拆（曾自作聪明拆成两条，被要求合回）
→ ⭐⭐ **但客户一旦给出编制（2026-10-23 实测：\"设置一个经理和两个员工，权责职务分配一下，
   使其能够完成复核\"）→ 就必须按【行业规范岗位名】拆泳道**，别再写着\"仓管员/复核人员\"这种口语：
   ```
   通行岗位名：收货员 · 保管员 · 复核员 · 验收员 · 发运员 · 账务员（+ 仓储部经理）
   泳道名 = 部门（岗位）：仓储部（收货员）｜仓储部（复核员）｜仓储部（经理）｜采购部（采购员）
   ① 执行岗与复核岗必须【两条泳道】（否则图上看着还是一个人）
   ② 管理岗一般不上日常动作；要它出现在图上，就给它一个【审批类节点】（如 85 超收短收处置审批）
   ③ ⭐ 不要写「兼」：用户明确否掉\"仓储部（复核员·兼）\"——
      编制不足是客户要解决的事，图上标\"兼\"等于替客户承认职责分离不成立
   ④ 泳道列序按【流程先后】排，不按部门排：收货员 → 采购员 → 经理（审批）→ 复核员（确认）
   ```
   ⚠️ 新增泳道后不要急着重画全图：`宽 +230 / 节点 x 平移 / WMS 小标签跟随 / 清航点`
   四件套（见 §四·补2）；加中间泳道时先把**列序**定好再算坐标，否则加完发现顺序反了要重排
→ 完整方法 + 各流程泳道分配表：references/pharma-role-lanes.md
```

⭐ **编号规则（用户 2026-10-19 最终定稿·别再自行发挥）**

```
`流程开始` → `10 XXX` → `20 XXX` → … → `流程结束`

· ⭐ 起止节点【不编号】（流程开始 / 流程结束 前面不加序号）
· ⭐ 第一个动作从【10】起（不是 20、不是 1）
· ⭐ 连续 +10，中间【不留空号】
· 每页独立起号（多页文件每页都从 10 开始）

生成器写法（计数器只对非起止节点自增）：
    _num = 0
    for i, (k, kind, lane, txt, tag, link) in enumerate(nodes):
        if kind in ("start", "end"):
            label = txt
        else:
            _num += 10
            label = f"{_num} {txt}"

⚠️ 早期用 (i+1)*10 → 开头有"流程开始"占掉 10，第一个动作变成 20（被用户纠正）
⚠️ 交付前自查：剥掉标题/泳道/系统小标签后，抓 ^(\d+) 的动作号，
   必须等于 range(10, 10*(n+1), 10)，否则就是有空号

⭐⭐ **补号规则（2026-10-26 用户确认补入）—— 治"后加的节点编号乱飞"**
```
编号 = 流程顺序的序号，不是"想起来就加一个"
① 步长全页统一（默认 10，节点特别密时用 5），不混用
② 必须连续无断号；⭐ 编号大小必须与【图中的上下顺序】一致（不能出现 170 排在 120 之前）
③ 中途插节点，只有两条路：
   a) 整体重排（首选；改完给"旧号→新号"对照表，方便同步流程说明表）
   b) 用中间号插入（15/25/35…，前提是步长本来就留了 5 的余量）
   ⭐ 不允许直接跳到 170/95 这种"随手编号"
④ 交付前自查：把 ^(\d+) 抓出来按【图上的 y 顺序】排列，必须严格递增且等差
   典型坏图：10…90 → 95 → 170 → 120 → 130 → 140 → 160（步长乱 + 倒挂 + 缺 100/110/150）
```
```

⭐⭐ **两个阶段的泳道策略**（用户定的分工）

```
甲方流程【未确认】→ 推演版：自己按 URS + 行业惯例判断泳道与分支，不套死模板、不找公司架构团队
甲方【确认后】　　→ 交付版：严格按公司标准模板 + 对接公司架构团队 + 特殊模板走邮件申请
判断某个分支敢不敢加：能被 URS 条款或 GMP 硬要求支撑的 → 敢加；
                     只是模板里有 / 别家有的 → 做成待确认选择题，别画死
```


⭐ **首选：用现成脚本**（写一份 JSON spec 即可，不必每次手写下面的 Python 模板）：

```bash
python3 ~/.hermes/skills/productivity/garlic-drawio-flowchart-authoring/scripts/drawio_swimlane.py spec.json out.drawio
```

spec.json = `{title?, legend?, lanes:[{name,width}], nodes:[{id,lane,text,type,y}], edges:[{from,to,label,side?}]}`；
`side` 取 `bottom|right|left|top|auto`（见 §十 ② 三出口规范）。
脚本自动生成泳道/节点/连线/图名/图例，并跑**XML 合法性 + 泳道内 y 重叠 + 锚点多样性**三项自查。
下面的手写模板是脚本不够用时的参考（自定义样式/特殊边）。

### 骨架

```python
out = ['<mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" page="1" pageWidth="1700" pageHeight="2600" math="0" shadow="0">',
       '<root>', '<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
```

### 泳道（swimlane）

```python
out.append(f'<mxCell id="lane0" value="WMS系统-WEB" style="swimlane;html=1;startSize=34;horizontal=1;'
           f'fillColor=#ffffff;strokeColor=#333333;fontStyle=1;fontSize=13;" vertex="1" parent="1">')
out.append(f'<mxGeometry x="270" y="20" width="330" height="2250" as="geometry"/></mxCell>')
```

### ⭐ 节点（放泳道内）

```python
# ⚠️ 关键：parent = 泳道 id；x 用【相对泳道】的 30，y 用绝对纵向位置
out.append(f'<mxCell id="n1" value="1.采购订单" style="{style}" vertex="1" parent="lane0">')
out.append(f'<mxGeometry x="30" y="130" width="270" height="46" as="geometry"/></mxCell>')
```

样式约定（沿用企业流程图的通用观感）：

```python
def style(t):
    if t == "start":    return "ellipse;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;"
    if t == "end":      return "ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;"
    if t == "decision": return "rhombus;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=11;"
    # ⭐ 用户图里出现过的其余形态（照抄即可）
    if t == "confirm":    return "rhombus;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=11;dashed=1;fontStyle=2;"   # 🟠待客户确认判定点
    if t == "optbranch":  return "rounded=0;whiteSpace=wrap;html=1;fillColor=#fff8f0;strokeColor=#e0a458;fontSize=11;dashed=1;fontStyle=2;"  # 🟠可选/旁路节点
    if t == "qc":         return "rounded=0;whiteSpace=wrap;html=1;fillColor=#e6f0ff;strokeColor=#5b8dd6;fontSize=11;"                        # 质量/QA 泳道节点
    if t == "subprocess": return "shape=process;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#333333;fontSize=11;"                    # ⭐双层边框=子流程（用户图里 20 上架流程/21 质检流程 就这么画）
    return "rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=11;"
```

### 连线

```python
out.append(f'<mxCell id="ed0" value="6.2 是" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;'
           f'exitX=0.5;exitY=1;entryX=0.5;entryY=0;fontSize=10;" edge="1" parent="1" source="n1" target="n2">')
out.append('<mxGeometry relative="1" as="geometry"/></mxCell>')
```

多行文字用 `&#10;`（先生成 `html.escape(text).replace('\n','&#10;')`）。

### 打包 + 校验

```python
import zipfile, os, xml.etree.ElementTree as ET
xs = '\n'.join(out)
open('x.drawio','w',encoding='utf-8').write(xs)
ET.fromstring(xs)            # 校验 XML 合法
with zipfile.ZipFile('x.zip','w',zipfile.ZIP_DEFLATED) as z:   # 要分发时打包
    for root,_,fs in os.walk('.'):
        for f in fs: z.write(os.path.join(root,f))
```

---

2026-10-22 实战：要删掉客户图上的 4 个装车节点 + 5 个 ERP 节点，第一遍按 **value 文字匹配**删，
结果图上留下**一堆空白菱形/空白矩形**（用户会立刻发现），白改一轮。

```python
# 根因：这类图的节点是【组合节点】
#   <mxCell id="A" style="group" vertex="1">        ← 真正的图形（value 为空）
#     <mxCell id="A-1" value="180 是否装车？" ...>   ← 文字在子 cell 里
# 按 value 匹配只能删到子 cell → 图形壳还留着

# ⭐ 正确做法：值命中的 id → 取其 parent（group）→ 连 group 带所有子 cell 一起删
labels = {i for i, v in info.items() if '装车' in (v or '')}
groups = {info[i]['parent'] for i in labels if info[i]['parent'] and info[i]['parent'] != '1'}
drop   = groups | labels | {i for i, p in parent.items() if p in groups}
```

删完必查三件事（缺一样就会露馅）：

```
① 图上一眼看：还有没有空白框 / 断头线（真渲染截图，别只看 XML）
② 边：连线是引用【group id】的，不是引用文字子 cell 的 → 删前先把 source/target 命中 group 的边收集出来
   删完补一条「上游 → 下游」的新边，否则流程断链（本例 110 批次调整 →「流程结束」）
③ 表：文档里对应的行同步删（否则图↔表对不上，跑 scripts/audit_fig_table.py 会报）
```

⭐ **先备份再动手**：本次从 `<交付目录>` 里的旧副本恢复了原页重做一遍才弄干净。
每次大改前把 drawio 复制一份到 file-exchange（顺带成为可回滚版本）。

---

2026-10-23 实战：用户要求把「收货确认/生成库存」切到新泳道「仓储部（经理·复核）」，
第一版渲染出来**第三条泳道整片空白、节点全不见了** —— 因为泳道盖住了节点。

```
⭐⭐ 根因：drawio 的 z 序 = XML 文档顺序（后出现的画在上层）
   新增 swimlane 若 append 到 root 末尾 → 它盖在所有节点之上 → 节点"消失"
   ⭐ 正解：插到【同层其他泳道之后、所有节点之前】
     kids = list(rEl)
     pos = next(i for i,e in enumerate(kids)
                if 'swimlane' in (e.get('style') or '') and '采购部' in val(e))
     rEl.insert(pos + 1, new_lane)
   ⚠️ 同理：任何"新增容器/背景框"都不要 append 到末尾
```

移动一组节点到新泳道的成套动作（漏一项就错位）：

```python
# ① 外框先加宽：新增一条泳道 = 宽 +230（本例 460 → 690）
# ② 节点 x 整体平移列宽（本例 +460），y 不动 → 流程先后关系不变
# ③ ⭐ 右上角「WMS」小标签是【独立 cell】，必须跟着平移（y 相同区间一起 +460）
# ④ ⭐ 清掉受影响连线的 <Array as="points"> 航点，让 orthogonalEdgeStyle 重新自动路由
#    （不清的话旧航点还在原坐标 → 线从新位置斜插回旧位置）
# ⑤ 长文字节点顺带加宽：100×65 → 150×78，WMS 标签移到 (x+w-38, y-13) 贴右上角外侧
#    ⚠️ 不加宽时，WMS 标签会压住最后一行字（"录入收货数量"的"数量"被盖住）
```

渲染后必须看的四件事（肉眼，不是查 XML）：

```
□ 新泳道里有没有节点（没有 = 又踩 z 序）
□ 进新泳道的线是不是从上游节点的正确一侧出来、有没有绕大圈
□ 长文字节点的 WMS 标签是否压字
□ 底部是否残留大片空白（泳道高可裁到 内容底 + 80）
```

⭐ **只交一张图时的交付形**：原文件是多页 mxfile → 复制该 `<diagram>` 进一个新 `<mxfile>`
输出**单页 .drawio**（用户要自己微调时用），同时给 2× PNG（插文档/发群用）。
用户说「只要重新出这一张图」= 不要顺手改其他页，也不要把 42 页整包发回去。

---

改图**不是手改 XML**，而是**回脚本改两个列表后重新生成**。删节点时有个必须成套的动作：

```
① 从 N（节点清单）删掉该节点
② 从 EDGES 删掉所有指向它 / 从它出发的边
③ ⭐ 补一条"上游 → 下游"的直连边，别让流程断链
   （本次：删「1.采购订单」后出现两个断口——"开始"没下游、"3.ASN单"没上游
     → 把 s1 → n2 接起来；删「是否让步收货」判断后同理：15 → n112 直连）
④ 重新算 y 坐标（删完会有空档；或保留原坐标，视觉上略松不碍事）
⑤ 回话只报三样：删了什么 / 加了什么 / 节点数与连线数变化（如 38→34 节点、41→36 连线）
```

⚠️ 删完**必跑 XML 合法性 + 泳道内 y 重叠**两项自查（见 §四 ④），再说"已改好"。

⭐ **删一个判断节点 ≠ 只删一个框**：判断节点通常带两条出边（是/否），
删它时要想清楚"剩下那条分支还算不算"——本次删「是否让步收货」时，
连带删掉它的一条分支节点（11.1.1 更新让步字段），把主链直连过去。
