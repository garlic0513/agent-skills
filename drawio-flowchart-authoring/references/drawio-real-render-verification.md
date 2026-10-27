# ⭐ 服务器上做 draw.io 真渲染自查（不再"我无法预览，请你自己打开看"）

> 2026-10-19 打通。此前技能里写的是「服务器没装 draw.io → 只能让用户验收」，
> 那个结论只对了一半：**没有 java / drawio CLI，但有 drawio-mcp-server 解包出来的 webapp**。
> 用它 + 本地 HTTP + 浏览器工具，就能拿到 draw.io 引擎的真实渲染图，自己先验收。

## 一、原理与前置

```bash
~/.cache/drawio-mcp-server/webapp/        # draw.war 解包目录（装 drawio-mcp-server 时生成）
~/.cache/drawio-mcp-server/webapp/js/viewer.min.js   # ⭐ 客户端渲染器，纯前端，不需要 java
```

draw.io 的 viewer 支持一段「嵌入式挂载」语法：页面上放一个
`<div class="mxgraph" data-mxgraph='{"xml":...}'>`，再加载 `js/viewer.min.js`，
它会把 mxGraphModel 用**同一套渲染引擎**画成 SVG（形状/圆角/跨线弧/字体全部真实）。

⚠️ 若该目录不存在 → 先按 `references/drawio-mcp-live-connection.md` 装一次
drawio-mcp-server（war 要国内镜像 `ghfast.top`），装完 war 会自动解包到上面那个路径。

## 二、三步跑通

**第 1 步 · 生成预览页**（别手写，用脚本）

```bash
python3 ~/.hermes/skills/productivity/drawio-flowchart-authoring/scripts/make_drawio_preview.py \
        "路径/图.drawio"            # 默认输出到 webapp/_preview/pN.html
```

**第 2 步 · 起本地静态服务**（必须用 background=true，不要 nohup/&）

```bash
cd ~/.cache/drawio-mcp-server/webapp && python3 -m http.server 8899 --bind 127.0.0.1
# 健康检查（另起一条命令）:
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8899/_preview/p1.html   # 期望 200
```

**第 3 步 · 浏览器打开 + 看图**

```
browser_navigate  http://127.0.0.1:8899/_preview/p2.html
browser_vision    "描述标题条/泳道配色/节点形状/圆角/跨线弧/文字是否溢出"
```

## 三、参数速查（在 make_drawio_preview.py 里改，或直接改 HTML）

```jsonc
{"xml": "<mxGraphModel>…</mxGraphModel>",   // 单页模型，多页文件要逐页取 <diagram> 里的 model
 "toolbar": "", "nav": false,
 "resize": true,     // true=自动缩放铺满窗口（看整体）；false=按 zoom 原样放大，可滚动（看局部）
 "zoom": 0.85,       // ⚠️ resize:true 时 zoom 基本被忽略，要局部放必须 resize:false
 "border": 16}
```

**看局部（如尾部汇聚区、某处跨线弧）**

```js
// 预览页配 resize:false + zoom:1.6~2.0，然后滚到目标区域
(()=>{const s=document.querySelector('svg').getBoundingClientRect();
      window.scrollTo(0, s.height*0.7); return window.scrollY;})()
```

## 四、这一步能抓到的真问题（2026-10-19 实测全中）

| 症状 | 只看 XML / 图例几何会发现吗 | 真渲染后 |
|---|---|---|
| 判定菱形文字横向溢出、压到菱形边框外 | 不会（几何校验只看矩形） | ✅ 一眼看到 |
| 系统小标签贴在节点右中，挡住跨泳道出线 | 不会 | ✅ |
| 第一行节点压住泳道标题条 | 不会（模型坐标明明差 8px，缩略图看着就是压） | ✅ 放大才确认 |
| `shape=terminator / process / document` 是否真生效 | 不会 | ✅ |
| `jumpStyle=arc` 是否真的画出半圆拱 | 不会 | ✅ |
| 泳道底色用模板蓝会不会和蓝色节点糊 | 靠猜 | ✅ 直接看 |

## 五、⭐ 对齐模板的最快路径（本次方法论）

```
① 把【公司标准模板自己的一页】也渲染出来（同一脚本，指定页号）
② 两图并排 → 逐项对：标题条高度/对齐、泳道底色、节点尺寸与字号、判定颜色、
   小标签位置、线是直角还是圆角、跨线弧
③ 改生成器参数 → 重新渲染 → 再对比（一轮就能从"像"变成"一致"）
```

比逐条读 XML 的 style 字符串快一个数量级，而且能发现"读了也看不出来"的问题
（例如模板的判定文字是**独立浮在菱形外**的 text cell，只看 style 不会意识到）。

## 六、坑

```
① 截图里的重叠/位置不能靠眼睛估：缩略图有缩放，8px 间隙会被看成"压住"。
   ⭐ 判断重叠要么看放大图（resize:false + zoom≥1.6），要么用模型坐标算。
② viewer 会给 <foreignObject> 报出缩放后的怪 boundingBox（上万的宽高），
   ⚠️ 别拿它量坐标；要坐标就量 <rect>（node 100×65 → screen 尺寸/前值即 scale）。
③ 端口分开用：3000 = drawio-mcp-server 的编辑器；8899 = 这个本地预览。别互相打架。
④ data-mxgraph 的值必须 html.escape(quote=True)，否则 JSON 里的引号会打断 HTML 属性。
⑤ 预览页只读，不能编辑；要改图仍走生成器或 draw.io 编辑器。
⑥ 渲染 ≠ 校对业务：渲染只保证"看着对"，业务对不对还得回文档核对（见 SKILL.md §五）。
```

## 七、对交付话术的影响（改口径）

```
旧口径：诚实说明「服务器没装 draw.io，我无法预览渲染」→ 请用户打开验证
新口径：交付前我已用 draw.io 引擎渲染自查（图表数：穿框 0 / 压线 0 / 交叉 N / 折点x.x每线），
        并贴一张真实渲染图；仍有疑虑请你在 draw.io 里微调（给的是可编辑 .drawio）
```

⭐ 但**不要**因为能渲染了就省掉几何校验脚本：渲染看"观感"，`check_lines_per_page.py`
看"穿框/压线/交叉"的硬指标，两者互补，都要跑。
