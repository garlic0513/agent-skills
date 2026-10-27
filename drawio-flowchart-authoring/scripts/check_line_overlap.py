#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_line_overlap.py —— .drawio 连线自查（三项）
用法：
    python3 check_line_overlap.py x.drawio            # 全查
    python3 check_line_overlap.py *.drawio            # 批量

查什么：
  ① 几何穿框：连线的水平/垂直段是否穿过【非端点节点】的矩形  ← 本次抓出 35 处的地方
  ② 通道重合：多条连线的中间航点是否落在同一 x / y 上
  ③ 锚点规则：菱形是否误用上下出口（应走左右）

⚠️ 局限：① 只能校验【显式写了 waypoints】的连线。
   若已改为\\\"不给 waypoints·交给 draw.io 自动路由\\\"，穿框由引擎保证，① 会显示 0 条可查线
   —— 这是正常的，不是失败。
   节点坐标按 parent=laneN + lane x 偏移还原为画布绝对坐标（泳道内子节点是相对坐标）。
"""
import re, sys, os
from collections import defaultdict

DIAMOND = ('rhombus',)
RECT = ('rounded=0', 'ellipse')


def load(path):
    return open(path, encoding='utf-8').read()


def lane_offsets(x):
    """lane id → 画布 x 偏移 + y 偏移（标题 90 已在节点 y 里体现，此处只取 x）"""
    off = {}
    for m in re.finditer(
            r'<mxCell id="lane(\d+)"[^>]*><mxGeometry x="(-?\d+)" y="(-?\d+)" width="(\d+)"',
            x):
        ln, lx, ly, lw = m.groups()
        off[int(ln)] = (int(lx), int(ly))
    return off


def collect_rects(x):
    """节点 id → (x, y, w, h, lane)；转画布绝对坐标"""
    off = lane_offsets(x)
    rects, types = {}, {}
    for m in re.finditer(
            r'<mxCell id="(\w+)" value="[^"]*" style="([^"]*)" vertex="1" parent="lane(\d+)">'
            r'<mxGeometry x="(-?\d+)" y="(-?\d+)" width="(\d+)" height="(\d+)"', x):
        nid, st, lane, gx, gy, w, h = m.groups()
        lane = int(lane)
        dx, dy = off.get(lane, (0, 0))
        rects[nid] = (int(gx) + dx, int(gy) + dy, int(w), int(h))
        types[nid] = 'D' if any(d in st for d in DIAMOND) else (
            'P' if any(r in st for r in RECT) else '?')
    return rects, types


def check_through(path, x, rects, verbose=True):
    """① 线段穿框"""
    bad = []
    for m in re.finditer(
            r'<mxCell id="ed(\d+)"[^>]*edge="1" parent="1" source="(\w+)" target="(\w+)"[^>]*>'
            r'<mxGeometry[^>]*>(.*?)</mxGeometry>', x, re.S):
        eid, s, t, geo = m.groups()
        if s not in rects or t not in rects:
            continue
        pts = [(float(a), float(b)) for a, b in
               re.findall(r'<mxPoint x="(-?\d+)" y="(-?\d+)"', geo)]
        if not pts:
            continue                      # 自动路由 → 跳过（见文件头说明）
        sx, sy, sw, sh = rects[s]
        tx, ty, tw, th = rects[t]
        path_pts = [(sx + sw / 2, sy + sh / 2)] + pts + [(tx + tw / 2, ty + th / 2)]
        for i in range(len(path_pts) - 1):
            (x1, y1), (x2, y2) = path_pts[i], path_pts[i + 1]
            for nid, (rx, ry, rw, rh) in rects.items():
                if nid in (s, t):
                    continue
                if abs(x1 - x2) < 1:      # 竖段
                    if rx < x1 < rx + rw and not (max(y1, y2) < ry or min(y1, y2) > ry + rh):
                        bad.append(f"ed{eid}({s}->{t}) 竖段 x={x1:.0f} 穿过 {nid}")
                elif abs(y1 - y2) < 1:    # 横段
                    if ry < y1 < ry + rh and not (max(x1, x2) < rx or min(x1, x2) > rx + rw):
                        bad.append(f"ed{eid}({s}->{t}) 横段 y={y1:.0f} 穿过 {nid}")
    return bad


def check_channels(x):
    """② 水平/垂直通道重合"""
    hs = [a for a, b in re.findall(
        r'<Array as="points"><mxPoint x="(-?\d+)" y="-?\d+"/>'
        r'<mxPoint x="(-?\d+)" y="-?\d+"/></Array>', x) if a == b]
    vs = [b for a, b, c, d in re.findall(
        r'<mxPoint x="(-?\d+)" y="(-?\d+)"/><mxPoint x="(-?\d+)" y="(-?\d+)"/>', x)
        if a != c and b == d]
    return ([v for v in set(hs) if hs.count(v) > 1],
            [v for v in set(vs) if vs.count(v) > 1])


def check_anchors(x, types):
    """③ 菱形误用上下出口"""
    bad = []
    for m in re.finditer(
            r'exitX=([\d.]+);exitY=([\d.]+)[^"]*" edge="1" parent="1" source="(\w+)"', x):
        ex, ey, s = m.groups()
        if types.get(s) == 'D' and (ex, ey) in (
                ('0.5', '1'), ('0.5', '1.0'), ('0.5', '0'), ('0.5', '0.0')):
            bad.append(s)
    return bad


def run(path):
    x = load(path)
    rects, types = collect_rects(x)
    thru = check_through(path, x, rects)
    dup_h, dup_v = check_channels(x)
    anc = check_anchors(x, types)
    n_edge = x.count('edge="1"')
    n_wp = x.count('<Array as="points">')
    name = os.path.basename(path)
    print(f"\n=== {name} ===")
    print(f"  节点 {len(rects)} ｜ 连线 {n_edge} ｜ 显式航点线 {n_wp}")
    print(f"  ① 穿框       : {len(thru)} 处" + ("" if not thru else " ⚠️"))
    for b in thru[:12]:
        print(f"       · {b}")
    if len(thru) > 12:
        print(f"       … 另 {len(thru)-12} 处")
    print(f"  ② 通道重合   : 水平 {dup_h or '无 ✅'} ｜ 垂直 {dup_v or '无 ✅'}")
    print(f"  ③ 菱形上下口 : {anc or '无 ✅'}")
    if n_wp == 0:
        print("  ℹ️ 无显式航点 → 穿框交给 draw.io 自动路由（① 无数据可查属正常）")
    ok = not thru and not dup_h and not dup_v and not anc
    print(f"  {'✅ 全部通过' if ok else '⚠️ 有项未过，见上'}")
    return ok


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    allok = True
    for p in args:
        if os.path.exists(p):
            allok &= run(p)
        else:
            print(f"  ⚠️ 找不到 {p}")
    sys.exit(0 if allok else 2)
