# 程序化新增单页流程（坐标纪律 · 2026-10-22 实测）

场景：往客户/同事给的 .drawio 里**新增一页**（如 S1 收货、扫箱/扫托收货）。
审查/修复已有页请看 `references/drawio-consistency-audit.md`；XML 增删改基本操作见 SKILL.md §13。

## 一、坐标纪律（单泳道垂直流，五条）

一轮画完能直接用，靠这五条；少一条就要返工重排。

| # | 规则 | 不加会怎样 |
|:-:|---|---|
| 1 | **左右两列留 30px 间隙**（主列 x=200..320、旁列 x=50..170） | 旁路节点与主干节点贴边，视觉上共用一条边框，像一个大框 |
| 2 | **菱形/节点按列中心对齐**：列中心 = `x + w/2`，起止/菱形共用同一个中心 x | 菱形与矩形中心错位，连线变斜 |
| 3 | **同一行的节点 y 必须完全相等**（旁路节点与主干节点差 4px 就会折线绕行） | 本该水平的线走成 L 形，还压到下面的框 |
| 4 | **菱形 170×80**，文字压到 12 字内（「30 超收/短收在容差内？」） | 134×80 放不下中文，文字溢出菱形边界 |
| 5 | **泳道宽 = 内容右边界 + ~35px**；高 = 末节点底 + ~40px | 右侧/底部大片空白，图看着"没画完" |

行距统一 **112px**（节点高 65、间隙 47），与公司标准模板一致。

## 二、是/否 标签用「独立 text 小节点」，不要用 edge label

```python
V('lbY','是','text;html=1;align=center;verticalAlign=middle;fontSize=10;fontColor=#333333;',252,326,22,16)
V('lbN','否',TXT,118,300,22,16)
```

摆位口诀（垂直流）：
- **是** → 菱形**底部尖角左侧**（x = 中心 − 30，y = 菱形底 − 12）
- **否** → 横向出线段的**下方/内侧**（x = 旁列右边 + 8，y = 横线段 + 8）
- ⭐ 必须**避开 WMS 黄标签**（标签 x = `节点右 − 38`、宽 38、高 21）——本次两个"是"都压在黄标签上，返工一次

用 edge label 的问题：drawio 自动落在中点/源端，同一页多个判定的标签会**叠在同一处**（实测两个标签重合）。

## 三、连线用固定端口，否则 orthogonalEdgeStyle 会乱绕

```python
EDGE = ('edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth=1;'
        'strokeColor=#333333;endArrow=block;endFill=1;')
st = EDGE + f';exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={nx};entryY={ny};entryDx=0;entryDy=0'
```

| 线型 | 端口 |
|---|---|
| 竖向（上下相邻） | `exit(0.5,1) → entry(0.5,0)` |
| 横向（左右相邻） | `exit(1,0.5) → entry(0,0.5)` |
| 旁路折线（左出下行） | `exit(0,0.5) → entry(0.5,0)` |

⭐ 不给端口时，两个同 y 节点之间会出现"绕到下方再回插"的怪回环（箭头从下面顶进目标框底边）——本次第一版最显眼的问题。

## 四、样式字典 + 新页骨架

```
LANE='swimlane;html=1;startSize=20;fontSize=14;fontStyle=0;fillColor=#dae8fc;strokeColor=#6c8ebf;swimlaneFillColor=#ffffff;'
SYS ='rounded=0;whiteSpace=wrap;html=1;verticalAlign=middle;fontSize=12;fillColor=#dae8fc;strokeColor=#6c8ebf;'   # 自动=蓝
PROC='rounded=0;whiteSpace=wrap;html=1;verticalAlign=middle;fontSize=12;fillColor=#ffffff;strokeColor=#333333;'  # 手动=白
SUB ='shape=process;whiteSpace=wrap;html=1;fontSize=12;fillColor=none;strokeColor=#333333;'                      # 子流程=双线框
DEC ='rhombus;whiteSpace=wrap;html=1;fontSize=10.5;fillColor=#dae8fc;strokeColor=#6c8ebf;'
TERM='rounded=1;arcSize=50;whiteSpace=wrap;html=1;fontSize=12;fillColor=#dae8fc;strokeColor=#6c8ebf;'
TAG ='rounded=0;whiteSpace=wrap;html=1;fontSize=9;fillColor=#fff2cc;strokeColor=#d6b656;'                        # 系统小标签
TXT ='text;html=1;align=center;verticalAlign=middle;fontSize=10;fontColor=#333333;'
```

```python
new = ET.SubElement(root,'diagram',{'id':'xxx-page','name':'××子流程 某制药客户'})
m   = ET.SubElement(new,'mxGraphModel',{...grid/page/pageWidth…})
rEl = ET.SubElement(m,'root')
ET.SubElement(rEl,'mxCell',{'id':'0'}); ET.SubElement(rEl,'mxCell',{'id':'1','parent':'0'})
```

## 五、两个业务型分支写法（可直接照抄）

```
① 扫托收货：在「扫描托盘号」之后插判定「托上货品与系统一致？」
   否 → 子流程框「转扫箱收货（页 N）」← 混托是整托收货的唯一风险点，异常要能降级
② 扫箱收货：超收/短收判定「否」→ 35 超收短收处置（采购确认）→ 回「40 收货确认」
   旁路节点与主干节点同 y，横向入主干，0 折点
```

⭐ 通则：**凡是"一次确认一大批"的节点，后面都要挂一个一致性判定**（托 vs 系统、箱规 vs 实物），
否则错误范围是按批算的，不是按件算的。

## 六、验收节奏（最多 3 轮，每轮只盯一类）

| 轮次 | 只看 |
|:-:|---|
| 1 | 结构：流程是否闭合、分支是否都有出口、泳道够不够装 |
| 2 | 标签与文字：是/否位置、菱形文字溢出、长节点换行 |
| 3 | 对齐与留白：左右间隙、同 y 对齐、泳道宽高、连线是否水平 |

回话只报"这轮修了哪类 + 修完的指标"，别一次解释全部细节。
