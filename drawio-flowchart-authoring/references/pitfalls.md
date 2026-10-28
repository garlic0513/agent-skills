# 坑库与工具噪音（openpyxl 等）

> 从 SKILL.md 下沉（2026-10-28 瘦身重构）。原属 garlic-drawio-flowchart-authoring。

```
① ⚠️ 泳道内子节点坐标：draw.io 里子元素坐标相对父容器 —— 必须 x=30 这种相对值，
   若写绝对坐标，渲染后所有节点堆到一处/错位。
② ⚠️ 服务器常缺 zip 命令 → 用 python zipfile 打包；rar 用 unrar-free（7z 对部分 RAR5 报 Unsupported Method）。
③ ⚠️ 自动生成的连线若**全部用同一锚点**（如都是 exitX=0.5;exitY=1 → entryX=0.5;entryY=0），
   跨泳道分支必然绕路、穿过其他节点、互相重叠。
   ⭐ 正解 = §九 的【智能锚点 + 航点】，不要再靠"交付时让用户手动微调"糊过去。
④ ⚠️ 布局自查：按泳道分组比对节点 y 区间是否重叠（脚本几十行就能查），交付前必查。
⑤ eddx 里的中文提取：用 >([^<>]+)< 抓文本节点；不要试图解析绘图坐标（结构复杂无必要）。
⑥ 不擅自改需求：画前先确认泳道维度（部门？系统？）、编号规则（是否对应 URS 条款）。
⑦ ⭐ 别用 sed/正则去改**生成器 .py**：替换串含多行中文/引号时会打断字符串字面量
   （本次 `sed -i` 改 notes 列表 → `SyntaxError: unterminated string literal (detected at line 90)`）。
   改脚本一律用 write_file 整份重写 / patch 工具，**不要 sed**。
⑧ ⭐ side 取值【大小写敏感·必须小写】：写 "Left" → `KeyError: 'Left'`（脚本只认 left/right/top/bottom/auto）。
⑨ ⭐ 生成器脚本要落成独立 .py（write_file）再执行，**别用 heredoc 直接喂 python**：
   长中文 + 引号 + `2>/dev/null` 会把真错误吞掉（本次 heredoc 版连续静默失败，落文件后立刻看到 SyntaxError/KeyError）。
⑩ ⭐ 批量场景别一张图一个脚本：整份蓝图 18–22 个流程 = 18 张图，
   把每个流程写成数据（lanes/nodes/edges/notes 列表）→ 一个脚本批量 build → 最后统一跑自查。
   本次两批（5 张 + 9 张）一次跑完，比逐张手画快一个数量级。
⑪ ⭐⭐ 生成器脚本里的**中文文案不能用 ASCII 双引号包词**：
   notes/选项文案写成 `"…（按物料主数据"是否称重"配置）"` → 直接打断 Python 字符串 →
   `SyntaxError: invalid syntax. Perhaps you forgot a comma?`
   （本次连踩两次，都是"笔记/选项文案里的引号"而非代码引号）
   → 统一改用「」或【】；⭐ 落文件后先跑
   `python3 -c "import ast;ast.parse(open('x.py',encoding='utf-8').read())"` 过语法再执行，
   比跑起来看报错快得多。
```

---

```
⚠️ /tmp/xlsxenv 启动时会打印一串无关报错（__editable___skillopt / _distutils_hack）
   → 那是环境里别的包留下的 .pth 报错，**不影响 openpyxl**（实测 3.1.5 正常）
   → 别被吓到去"修环境"；判断真失败看的是【目标文件有没有生成】
⭐ PatternFill 用关键字更稳：PatternFill(fill_type='solid', fgColor='1F4E79')
⭐ 复杂脚本别用 heredoc 直接喂 python（长中文 + 引号易被截断、再配 2>/dev/null 把错藏了）
   → 先 write_file 落成 .py 再执行，报错才看得见
⭐ 生成后必做：load_workbook 回读校验（sheet 名 / 行×列 / 表头 / 抽一行看内容）
⭐ 交付：.xlsx 属常见格式，微信可直发；同时 cp 到 <交付目录>
