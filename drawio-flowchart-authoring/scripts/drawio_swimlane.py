#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
泳道流程图生成器（draw.io / mxGraph XML）—— v2

用法：
    python3 drawio_swimlane.py <spec.json> <out.drawio>

spec.json 结构（lane 用下标引用）——
⭐ 节点定位二选一："order"（泳道内逻辑序号 0,1,2… · 推荐·对应规则 A）或 "y"（泳道内绝对纵向位置）
⚠️ 下面是【可直接复制当 JSON 用】的写法，所以不要在里面加注释：

{
  "title": "收货管理-成品入库流程图",
  "legend": "图例：下角=是（主路径）  右角=否  左角=其他 ｜ 条件=分支触发条件",
  "lanes": [
    {"name": "生产车间", "width": 240},
    {"name": "WMS系统-WEB", "width": 330},
    {"name": "WMS系统-RF", "width": 330},
    {"name": "线下动作", "width": 300}
  ],
  "lane_height": 2350,
  "lanes_x": [20, 270, 610, 950],
  "nodes": [
    {"id": "s0",  "lane": 0, "text": "开始", "type": "start", "y": 30},
    {"id": "n1",  "lane": 0, "text": "1.车间生产完工\\n产出半成品", "type": "process", "y": 130},
    {"id": "n10", "lane": 2, "text": "10.是否符合收货", "type": "decision", "y": 1340}
  ],
  "edges": [
    {"from": "s0",  "to": "n1",  "label": ""},
    {"from": "n10", "to": "n11", "label": "是",  "side": "bottom"},
    {"from": "n10", "to": "ne",  "label": "否",  "side": "right"},
    {"from": "n10", "to": "nx",  "label": "其他", "side": "left"}
  ],
  "notes": [
    {"node": "b2", "text": "【对应节点 5. ASN单审核】A. 采购人员 B. 仓库\n⭐我方建议：采购人员一级审核\n客户确认：☐A ☐B"},
    {"text": "【说明·节点 2.】ERP 不打通 → 改为手工建 ASN 单"}
  ]
}

说明：
  · title / legend / side / lanes_x / lane_height / notes 均可省略
  · ⭐ notes = 待客户确认选项，统一渲染到【图最右侧】独立面板·按数组顺序编号【1】【2】…
    （用户规范：橙框不要散落在节点旁，集中放右侧按节点序号排列；panel_width 可调，默认 560）
  · lanes_x 缺省时按各泳道 width 自动横向排布
  · 节点可选 "h" 覆盖默认高（decision 54 / 其他 46）
  · title 存在时，泳道与节点整体自动下移 80（不用自己调 y）

⭐ side（菱形三出口·用户指定规范）：
  bottom = 下角 = 是（主路径）   right = 右角 = 否
  left   = 左角 = 其他（例外）   auto   = 按目标相对位置自动判断（默认）
  ⚠️ 同一个判定节点的两条边不要都用同一个 side，否则重叠

⭐ 连线策略（v2 新增，治"箭头重叠"）：
  按目标相对位置自动选锚点（右侧泳道→右出左进；同泳道下→下出上进），
  跨泳道连线自动加 <Array as="points"> 航点走空白横带，不穿节点。

type: start(椭圆·蓝) / end(椭圆·绿) / decision(菱形·蓝·已确认) /
      confirm(菱形·橙虚线·待客户确认) / optbranch(方框·橙虚线·可选分支) / process(方框·灰)

⭐ v3 硬规则（用户 2026-10-16 逐条指定，已内置）：
  A. 先定泳道 → 泳道内按 order 逻辑自上而下排 → 再连线
  B. 菱形判定节点走【左右】出口；矩形进程节点走【上下】出口
  C. 所有中间通道过全局 Router（唯一坐标 + 冲突 ±channel_gap 偏移）→ 连线不重合
  ⭐ D. 待确认选项（spec.notes）统一放【图最右侧】独立面板·按节点序号排列

生成后自动七项自查（对应 SKILL.md §四 ③④ / §九 / §九·补 / §十 ⑦）：
  ① XML 合法性            ② 每个泳道内节点 y 区间是否重叠
  ③ 锚点种类数 + 航点数    ④ 同一判定节点是否两支出边撞同一角
  ⑤ 菱形是否误用上下出口    ⑥ 水平通道是否有重合
  ⑦ 右侧待确认面板（卡片数 == notes 数 + 面板标题存在）
"""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET

# ⭐ 菱形三出口：exitX, exitY, entryX, entryY
SIDE = {
    "bottom": (0.5, 1.0, 0.5, 0.0),
    "right":  (1.0, 0.5, 0.0, 0.5),
    "left":   (0.0, 0.5, 1.0, 0.5),
    "top":    (0.5, 0.0, 0.5, 1.0),
}
TITLE_OFFSET = 80   # 有 title/legend 时泳道与节点的纵向下移量
DEFAULT_VGAP = 112  # nodes 用 order 定位时的泳道内行距


def is_diamond(t):
    """菱形判定节点（decision=系统判定 / confirm=待客户确认）"""
    return t in ("decision", "confirm")


class Router:
    """⭐ 规则 C：全局通道表 —— 每条线的中间通道分配【唯一】坐标，冲突时 ±gap 递进偏移。

    治的是"每条线各自算中点 → 多条线落在同一条 x（或 y）上而重合"。
    ⚠️ 必须【全局】去重；早期按「源泳道→目标泳道」分组是错的（跨组照样撞）。
    """

    def __init__(self, gap=22):
        self.used_h = set()      # 已占用的水平通道 x
        self.used_v = set()      # 已占用的垂直通道 y
        self.gap = gap

    def _probe(self, base, used):
        v, k = int(round(base)), 0
        while v in used:
            k += 1
            v = int(round(base + (k * self.gap if k % 2 else -k * self.gap)))
        used.add(v)
        return v

    def h(self, base):
        """水平段 midx"""
        return self._probe(base, self.used_h)

    def v(self, base):
        """垂直段 midy"""
        return self._probe(base, self.used_v)


def style(t):
    if t == "start":
        return "ellipse;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;"
    if t == "end":
        return "ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;"
    if t == "decision":     # 已确认的系统判定
        return "rhombus;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=11;"
    if t == "confirm":      # ⭐ 待客户确认的判定点（橙虚线菱形）
        return ("rhombus;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;"
                "fontSize=11;dashed=1;fontStyle=2;")
    if t == "optbranch":    # ⭐ 可选分支节点（橙虚线方框）
        return ("rounded=0;whiteSpace=wrap;html=1;fillColor=#fff8f0;strokeColor=#e0a458;"
                "fontSize=11;dashed=1;fontStyle=2;")
    return "rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=11;"


def build(spec):
    lanes = spec["lanes"]
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    # ⭐ 规则 A：泳道高度未显式给时，按最大 order 自动算
    vgap = spec.get("vgap", DEFAULT_VGAP)
    if "lane_height" in spec:
        lane_h = spec["lane_height"]
    elif any("order" in nd for nd in nodes):
        lane_h = 120 + (max(nd.get("order", 0) for nd in nodes) + 1) * vgap
    else:
        lane_h = 2350

    title = spec.get("title", "")
    legend = spec.get("legend", "")
    top_pad = TITLE_OFFSET if (title or legend) else 0

    # 泳道横向排布：未显式给 lanes_x 就按宽度累加
    lanes_x = spec.get("lanes_x")
    if not lanes_x:
        lanes_x, cur = [], 20
        for ln in lanes:
            lanes_x.append(cur)
            cur += ln["width"] + 10

    # ⭐⭐ 规则 D：待客户确认选项 → 统一放【图最右侧】独立面板（不散落在节点旁）
    # spec.notes = [{"node": "b2", "text": "【对应节点 5.】A… B… 客户确认：☐A ☐B"}] 或 ["纯文本"]
    notes = spec.get("notes", [])
    panel_w = spec.get("panel_width", 560)
    main_right = lanes_x[-1] + lanes[-1]["width"] + 40 if lanes else 1200
    panel_x = main_right + 40 if notes else 0
    page_w = (panel_x + panel_w + 40) if notes else main_right
    panel_need = 0
    if notes:
        for _n in notes:
            _t = _n if isinstance(_n, str) else _n.get("text", "")
            panel_need += 16 * len(_t.split("\n")) + 42
        panel_need += 90
    page_h = max(lane_h + 120 + top_pad, 20 + top_pad + panel_need)

    # ---- ⭐ 规则 A：先定泳道，泳道内按逻辑顺序自上而下排 ----
    # nodes 给 "order"（泳道内逻辑序号 0,1,2…）→ 自动算 y；给 "y" 则按 y
    vgap = spec.get("vgap", DEFAULT_VGAP)
    widths = {i: ln["width"] - 60 for i, ln in enumerate(lanes)}
    pos = {}
    for nd in nodes:
        typ = nd.get("type", "process")
        h = nd.get("h", 54 if is_diamond(typ) else 46)
        lane = nd["lane"]
        y = (60 + nd["order"] * vgap) if "order" in nd else nd["y"]
        pos[nd["id"]] = {
            "x": lanes_x[lane] + 30, "y": y + top_pad,
            "w": widths[lane], "h": h, "lane": lane, "typ": typ,
        }
    router = Router(spec.get("channel_gap", 22))

    def anchors(s, t, side):
        """→ (exitX, exitY, entryX, entryY, waypoints_xml)

        ⭐ 规则 B：菱形→左右优先；矩形→上下优先；跨泳道→按目标相对位置用左右。
        ⭐ 规则 C：所有中间通道走 router，保证全局唯一（不重合）。
        """
        ps, pt = pos[s], pos[t]
        scx, scy = ps["x"] + ps["w"] / 2, ps["y"] + ps["h"] / 2
        tcx, tcy = pt["x"] + pt["w"] / 2, pt["y"] + pt["h"] / 2
        px, pw, ph = ps["x"], ps["w"], ps["h"]

        if side and side != "auto":
            ex, ey, nx, ny = SIDE[side]
            pts = ""
            if side in ("left", "right") and ps["lane"] != pt["lane"]:
                exx = px + pw if side == "right" else px
                txx = pt["x"] if side == "right" else pt["x"] + pt["w"]
                midx = router.h((exx + txx) / 2)
                pts = (f'<Array as="points">'
                       f'<mxPoint x="{midx}" y="{scy:.0f}"/>'
                       f'<mxPoint x="{midx}" y="{tcy:.0f}"/></Array>')
            elif side == "bottom" and abs(scx - tcx) > 20:
                midy = router.v((ps["y"] + ph + pt["y"]) / 2)
                pts = (f'<Array as="points">'
                       f'<mxPoint x="{scx:.0f}" y="{midy}"/>'
                       f'<mxPoint x="{tcx:.0f}" y="{midy}"/></Array>')
            elif side == "left":       # 绕左侧空白带
                off = router.h(px - 28 if px > 60 else px + pw + 28)
                pts = (f'<Array as="points">'
                       f'<mxPoint x="{off}" y="{scy:.0f}"/>'
                       f'<mxPoint x="{off}" y="{tcy:.0f}"/></Array>')
            return ex, ey, nx, ny, pts

        # ---- auto：规则 B 按【源节点类型】+ 目标相对位置 ----
        if pt["lane"] > ps["lane"]:            # 右侧泳道 → 水平线（右出左进）
            ex, ey, nx, ny = 1, 0.5, 0, 0.5
            midx = router.h((px + pw + pt["x"]) / 2)
            pts = (f'<Array as="points"><mxPoint x="{midx}" y="{scy:.0f}"/>'
                   f'<mxPoint x="{midx}" y="{tcy:.0f}"/></Array>')
        elif pt["lane"] < ps["lane"]:          # 左侧泳道
            ex, ey, nx, ny = 0, 0.5, 1, 0.5
            midx = router.h((pt["x"] + pt["w"] + px) / 2)
            pts = (f'<Array as="points"><mxPoint x="{midx}" y="{scy:.0f}"/>'
                   f'<mxPoint x="{midx}" y="{tcy:.0f}"/></Array>')
        elif is_diamond(ps["typ"]) and abs(scx - tcx) < 20:
            # ⭐ 菱形默认【不走上下】（会压住正下方节点）→ 用右口向侧向分流
            ex, ey, nx, ny = 1, 0.5, 0, 0.5
            midx = router.h(px + pw + 40)
            pts = (f'<Array as="points"><mxPoint x="{midx}" y="{scy:.0f}"/>'
                   f'<mxPoint x="{midx}" y="{tcy:.0f}"/></Array>')
        elif tcy > scy:                        # 矩形·同泳道向下（主干垂直）
            ex, ey, nx, ny = 0.5, 1, 0.5, 0
            pts = ""
        else:                                  # 矩形·同泳道向上
            ex, ey, nx, ny = 0.5, 0, 0.5, 1
            pts = ""
        return ex, ey, nx, ny, pts

    out = [
        f'<mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" '
        f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_w}" '
        f'pageHeight="{page_h}" math="0" shadow="0">',
        "<root>", '<mxCell id="0"/>', '<mxCell id="1" parent="0"/>',
    ]

    # ⭐ 顶部图名 + 图例（用户规范：一级流程-二级流程流程图）
    if title:
        out.append(
            f'<mxCell id="title" value="{html.escape(title)}" style="text;html=1;strokeColor=none;'
            f'fillColor=none;align=center;verticalAlign=middle;fontSize=22;fontStyle=1;'
            f'fontColor=#1a3d6d;" vertex="1" parent="1">'
            f'<mxGeometry x="{(page_w - 800) / 2:.0f}" y="12" width="800" height="50" '
            f'as="geometry"/></mxCell>'
        )
    if legend:
        out.append(
            f'<mxCell id="legend" value="{html.escape(legend)}" style="text;html=1;strokeColor=none;'
            f'fillColor=none;align=center;verticalAlign=middle;fontSize=11;fontColor=#666666;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{(page_w - 1000) / 2:.0f}" y="58" width="1000" height="24" '
            f'as="geometry"/></mxCell>'
        )

    # 泳道
    for i, ln in enumerate(lanes):
        out.append(
            f'<mxCell id="lane{i}" value="{html.escape(ln["name"])}" '
            f'style="swimlane;html=1;startSize=34;horizontal=1;fillColor=#ffffff;'
            f'strokeColor=#333333;fontStyle=1;fontSize=13;" vertex="1" parent="1">'
        )
        out.append(
            f'<mxGeometry x="{lanes_x[i]}" y="{20 + top_pad}" width="{ln["width"]}" '
            f'height="{lane_h}" as="geometry"/></mxCell>'
        )

    # 节点（⭐ parent=泳道 id；x 用相对值 30，y 用泳道内纵向位置）
    for nd in nodes:
        lane = nd["lane"]
        typ = nd.get("type", "process")
        h = nd.get("h", 54 if is_diamond(typ) else 46)
        y = (60 + nd["order"] * vgap) if "order" in nd else nd["y"]
        esc = html.escape(nd["text"]).replace("\n", "&#10;")
        out.append(f'<mxCell id="{nd["id"]}" value="{esc}" style="{style(typ)}" vertex="1" parent="lane{lane}">')
        out.append(f'<mxGeometry x="30" y="{y}" width="{widths[lane]}" height="{h}" as="geometry"/></mxCell>')

    # 连线（智能锚点 + 航点）
    for i, ed in enumerate(edges):
        s, t = ed["from"], ed["to"]
        if s not in pos or t not in pos:
            continue
        ex, ey, nx, ny, pts = anchors(s, t, ed.get("side", "auto"))
        lbl = html.escape(ed.get("label", ""))
        out.append(
            f'<mxCell id="ed{i}" value="{lbl}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;'
            f'html=1;exitX={ex};exitY={ey};entryX={nx};entryY={ny};fontSize=9;jettySize=auto;" '
            f'edge="1" parent="1" source="{s}" target="{t}">'
        )
        out.append(f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>')

    # ⭐⭐ 规则 D：右侧「待客户确认选项」面板 —— 按节点序号排列，卡片带【N】前缀
    if notes:
        out.append(
            f'<mxCell id="panel_title" value="⭐ 待客户确认选项（按节点序号排列）" '
            f'style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F4B183;strokeColor=#C55A11;'
            f'fontStyle=1;fontSize=14;fontColor=#833C00;" vertex="1" parent="1">'
            f'<mxGeometry x="{panel_x}" y="{20 + top_pad}" width="{panel_w}" height="44" '
            f'as="geometry"/></mxCell>'
        )
        _y = 20 + top_pad + 56
        for _k, _n in enumerate(notes, 1):
            _txt = _n if isinstance(_n, str) else _n.get("text", "")
            _nid = "" if isinstance(_n, str) else _n.get("node", "")
            _body = html.escape(f"【{_k}】{_txt}").replace("\n", "&#10;")
            _h = 16 * len(_txt.split("\n")) + 26
            _cid = f"card_{_nid}" if _nid else f"card_{_k}"
            out.append(
                f'<mxCell id="{_cid}" value="{_body}" '
                f'style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fffdf5;strokeColor=#d79b00;'
                f'fontSize=11;align=left;verticalAlign=top;spacingLeft=8;spacingTop=6;'
                f'dashed=1;fontColor=#8a5a00;" vertex="1" parent="1">'
                f'<mxGeometry x="{panel_x}" y="{_y}" width="{panel_w}" height="{_h}" '
                f'as="geometry"/></mxCell>'
            )
            _y += _h + 14

    out += ["</root>", "</mxGraphModel>"]
    return "\n".join(out)


def selfcheck(xml_str, spec):
    ok = True
    # ① XML 合法
    try:
        ET.fromstring(xml_str)
        print("✅ XML 合法")
    except Exception as e:
        print("❌ XML 错误:", e)
        ok = False

    # ② 泳道内 y 重叠（支持 order 定位）
    lanes = spec["lanes"]
    vgap = spec.get("vgap", DEFAULT_VGAP)
    per_lane = {i: [] for i in range(len(lanes))}
    for nd in spec.get("nodes", []):
        typ = nd.get("type", "process")
        h = nd.get("h", 54 if is_diamond(typ) else 46)
        y = (60 + nd["order"] * vgap) if "order" in nd else nd["y"]
        per_lane[nd["lane"]].append((y, y + h, nd["text"][:20]))

    print("\n=== 泳道内排布自查 ===")
    for i, ln in enumerate(lanes):
        ns = sorted(per_lane[i])
        bad = False
        prev_end = None
        for y1, y2, _ in ns:
            if prev_end is not None and y1 < prev_end - 1:
                bad = True
            prev_end = max(prev_end or 0, y2)
        flag = "⚠️ 有重叠" if bad else "✅ 无重叠"
        print(f"  [{ln['name']}] {len(ns)} 个节点 → {flag}")
        if bad:
            ok = False
            for y1, y2, t in ns:
                print(f"      y {y1:6.0f}-{y2:6.0f}  {t}")

    # ③ ⭐ 锚点多样性（1 种 = 箭头必然重叠）+ 航点数量
    kinds = sorted(set(re.findall(r"exitX=[\d.]+;exitY=[\d.]+", xml_str)))
    pts = len(re.findall(r'<Array as="points">', xml_str))
    print(f"\n=== 连线质量自查 ===\n  锚点种类 {len(kinds)} 种 {kinds}"
          f"\n  带航点(waypoint)连线 {pts} 条")
    if len(kinds) <= 1 and len(spec.get("edges", [])) > 3:
        print("  ⚠️ 只有一种锚点 → 跨泳道必然重叠，检查 side / 布局")
        ok = False

    # ④ ⭐ 同一判定节点的出边是否撞在同一个角（菱形含 decision / confirm）
    dec_ids = {nd["id"] for nd in spec.get("nodes", []) if is_diamond(nd.get("type", "process"))}
    corner_use = {}
    for ed in spec.get("edges", []):
        if ed["from"] in dec_ids:
            corner_use.setdefault(ed["from"], []).append(ed.get("side", "auto"))
    for nid, sides in corner_use.items():
        dups = [s for s in set(sides) if sides.count(s) > 1 and s != "auto"]
        if dups:
            print(f"  ⚠️ 判定节点 {nid} 的 {dups} 出口被用了 {sides.count(dups[0])} 次 → 会重叠")
            ok = False

    # ⑤ ⭐ 规则 B：菱形是否误用上下出口（会压住正下方节点）
    typ_of = {nd["id"]: nd.get("type", "process") for nd in spec.get("nodes", [])}
    bad_dia = []
    for m in re.finditer(r'exitX=([\d.]+);exitY=([\d.]+)[^\"]*" edge=\"1\" parent=\"1\" source=\"(\w+)\"', xml_str):
        ex, ey, s = m.groups()
        if is_diamond(typ_of.get(s, "")) and (ex, ey) in (
                ("0.5", "1"), ("0.5", "1.0"), ("0.5", "0"), ("0.5", "0.0")):
            bad_dia.append(s)
    if bad_dia:
        print(f"  ⚠️ 菱形用了上下出口（应走左右）: {sorted(set(bad_dia))}")
        ok = False
    else:
        print("  ✅ 菱形出口全走左右")

    # ⑥ ⭐ 规则 C：水平/垂直通道是否有重合（航点中间段）
    hs = [a for a, b in re.findall(
        r'<Array as="points"><mxPoint x="(\d+)" y="\d+"/><mxPoint x="(\d+)" y="\d+"/></Array>', xml_str) if a == b]
    dup_h = {v for v in hs if hs.count(v) > 1}
    if dup_h:
        print(f"  ⚠️ 水平通道重合 x: {sorted(dup_h)} → 应交给 Router 全局去重")
        ok = False
    else:
        print(f"  ✅ 水平通道 {len(hs)} 条·无重合")

    # ⑦ ⭐ 规则 D：右侧待确认面板（每个 note 一张卡 + 一个面板标题）
    n_notes = len(spec.get("notes", []))
    if n_notes:
        cards = re.findall(r'<mxCell id="card_', xml_str)
        has_panel = 'id="panel_title"' in xml_str
        print(f"\n=== 待确认面板自查 ===\n  选项卡 {len(cards)} 张 / 应有 {n_notes} 张"
              f" | 面板标题 {'✅' if has_panel else '❌'}")
        if len(cards) != n_notes or not has_panel:
            ok = False

    return ok


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    xml_str = build(spec)
    open(sys.argv[2], "w", encoding="utf-8").write(xml_str)

    print(f"写入 {sys.argv[2]}")
    print(f"泳道 {len(spec['lanes'])} 个 | 节点 {len(spec.get('nodes', []))} 个 | "
          f"连线 {len(spec.get('edges', []))} 条")
    good = selfcheck(xml_str, spec)
    print("\n✅ 通过，可交付" if good else "\n⚠️ 有告警，修完再交付")


if __name__ == "__main__":
    main()
