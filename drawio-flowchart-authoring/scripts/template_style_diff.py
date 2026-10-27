#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前【模板样式逐项 diff】—— 别再等用户一条条挑视觉差异。

起因（2026-10-19）：入库流程图交付后，用户连续四轮挑出「文字要写在图形里」
「泳道间要贴着」「是/否 标签要贴尖角」「标题不要太粗」……
最后我手动跑了一次「模板 vs 我方」样式抽样对比，一次就发现剩下 4 处不一致。
→ 正确姿势：交付前先跑这个脚本，把 frame/lane/判定/子流程/普通节点/连线 各抽一条比。

用法：
    python3 template_style_diff.py 公司模板.drawio 我的图.drawio [模板页序] [我的页序]
    页序从 0 开始，可省略（默认在全部页面里自动找第一个含该类形状的页）

输出：每个形状类别一行「模板: 我方:」+ ⚠️ 只列出【双方取值不同】的关键属性，
      并给一句可直接照做的修法建议。
"""
import sys
import re
import base64
import zlib
import urllib.parse
import xml.etree.ElementTree as ET

# 关心的样式属性（其余属性如 html/whiteSpace/pointerEvents 与观感无关，忽略）
KEYS = ["fillColor", "swimlaneFillColor", "strokeColor", "fontColor",
        "fontSize", "fontStyle", "startSize", "spacing", "verticalAlign",
        "align", "rounded", "arcSize", "dashed", "strokeWidth",
        "jumpStyle", "labelBackgroundColor"]


def get_model(diagram):
    """兼容未压缩（diagram 下有 mxGraphModel）与压缩（base64+deflate+unquote）两种形态。"""
    m = diagram.find("mxGraphModel")
    if m is not None:
        return m
    t = (diagram.text or "").strip()
    if not t:
        return None
    try:
        raw = zlib.decompress(base64.b64decode(t), -15).decode("utf-8")
        return ET.fromstring(urllib.parse.unquote(raw))
    except Exception:
        return None


def load(path):
    root = ET.parse(path).getroot()
    out = []
    for d in root.findall(".//diagram"):
        m = get_model(d)
        if m is not None:
            out.append((d.get("name") or "?", m))
    return out


def style_dict(style):
    d = {}
    for part in (style or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            d[k.strip()] = v.strip()
        elif part.strip():
            d[part.strip()] = "1"      # 形如 rounded 这类无值开关
    return d


def rect(c):
    g = c.find("mxGeometry")
    if g is None:
        return None
    try:
        return (float(g.get("x") or 0), float(g.get("y") or 0),
                float(g.get("width") or 0), float(g.get("height") or 0))
    except ValueError:
        return None


def sample(model, kind):
    """按类别抽第一个匹配的样式：frame / lane / dec / sub / proc / edge。"""
    if kind == "edge":
        for c in model.iter("mxCell"):
            if c.get("edge") == "1":
                return c.get("style") or ""
        return None
    for c in model.iter("mxCell"):
        if c.get("vertex") != "1":
            continue
        st = c.get("style") or ""
        r = rect(c)
        if r is None:
            continue
        w, h = r[2], r[3]
        if kind == "frame" and "swimlane" in st and w > 700 and h > 700:
            return st
        if kind == "lane" and "swimlane" in st and w <= 700:
            return st
        if kind == "dec" and ("rhombus" in st or "decision" in st):
            return st
        if kind == "sub" and "shape=process" in st and w < 320:
            return st
        if kind == "proc" and 80 < w < 140 and "swimlane" not in st \
                and "rhombus" not in st and "shape=process" not in st \
                and "ellipse" not in st and "terminator" not in st:
            return st
    return None


LABEL = {
    "frame": "外框（顶层泳道容器）",
    "lane": "普通泳道",
    "dec": "判定菱形",
    "sub": "子流程双线框",
    "proc": "普通动作节点",
    "edge": "连线",
}

ADVICE = {
    "fontStyle": "模板不加粗就删掉 fontStyle=1（标题更贴模板观感）",
    "startSize": "标题条高度对齐模板（公司模板 31）",
    "spacing": "标题左右内边距对齐模板（公司模板 2）",
    "swimlaneFillColor": "⭐ 泳道/外框【主体】颜色：留空=白底（对方深色主题下会露白），"
                         "要与主题反相配合就显式写浅色",
    "fontColor": "字色跟随模板（模板多不写字色=默认黑）",
    "fontSize": "字号对齐模板；中文问题长的判定别硬上模板 12 号，会折成怪行",
    "verticalAlign": "判定菱形模板用 top（文字靠上），我方若用 middle 属可接受差异",
    "fillColor": "⭐ swimlane 的 fillColor 只涂标题条，主体是 swimlaneFillColor，别搞混",
    "jumpStyle": "交叉处才加 jumpStyle=arc，别全局开",
    "rounded": "模板连线 rounded=1（圆角正交）",
}


def diff(a, b):
    da, db = style_dict(a), style_dict(b)
    rows = []
    for k in KEYS:
        va, vb = da.get(k, "(默认)"), db.get(k, "(默认)")
        if va != vb:
            rows.append((k, va, vb))
    return rows


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    tpl_pages = load(sys.argv[1])
    my_pages = load(sys.argv[2])
    try:
        ti = int(sys.argv[3]) if len(sys.argv) > 3 else None
        mi = int(sys.argv[4]) if len(sys.argv) > 4 else None
    except ValueError:
        ti = mi = None
    tpl_models = [tpl_pages[ti][1]] if ti is not None else [m for _, m in tpl_pages]
    my_models = [my_pages[mi][1]] if mi is not None else [m for _, m in my_pages]

    total = 0
    for kind in ["frame", "lane", "dec", "sub", "proc", "edge"]:
        a = b = None
        for m in tpl_models:
            a = sample(m, kind)
            if a:
                break
        for m in my_models:
            b = sample(m, kind)
            if b:
                break
        print("=" * 68)
        print(f"【{kind}】{LABEL[kind]}")
        if not a or not b:
            print(f"  模板: {'有' if a else '未找到'} | 我方: {'有' if b else '未找到'}")
            continue
        rows = diff(a, b)
        if not rows:
            print("  ✅ 关键属性一致")
            continue
        total += len(rows)
        for k, va, vb in rows:
            print(f"  ⚠️ {k:22} 模板={va:18} 我方={vb}")
            if k in ADVICE:
                print(f"     → {ADVICE[k]}")
    print("=" * 68)
    print(f"共 {total} 处关键属性差异（形如 html/whiteSpace 的无关属性已忽略）")
    print("⚠️ 逐项确认后再交付：用户往往会一条条挑出来，一次对齐省四轮来回。")


if __name__ == "__main__":
    main()
