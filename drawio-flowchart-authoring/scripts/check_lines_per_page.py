#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_lines_per_page.py —— 逐页连线体检（穿框 / 压线 / 交叉 / 折点 / 线长）
用法: python3 check_lines_per_page.py x.drawio [y.drawio ...]

为什么还需要这个（check_line_overlap.py 之外）：
  · check_line_overlap.py 只认 parent="laneN" 的相对坐标节点；生成器若把节点写成 parent="1"
    绝对坐标，它会报"节点 0" → ①穿框 0 处是假象
  · 它把所有页的点混在一起统计 → 不同页的同一个 y 会被误报成"通道重合"
  · 它不算【交叉次数】和【折点/线】——而这两项才是"线乱不乱"的量化指标

本脚本按页独立统计并输出：
  折点/线（越小越直）、总线长、穿框（真穿节点矩形）、压线（共线重叠 >6px）、交叉（横竖相交）
⭐ 经验基线：好的图 折点/线 ≤ 2.0，交叉 ≤ 节点数的 1/4；折点/线 > 3 = 明显绕远
"""
import sys, re, zlib, base64, urllib.parse, math
import xml.etree.ElementTree as ET


def models(path):
    root = ET.parse(path).getroot()
    out = []
    for d in root.findall('diagram'):
        m = d.find('mxGraphModel')
        if m is None:
            t = (d.text or '').strip()
            m = ET.fromstring(urllib.parse.unquote(
                zlib.decompress(base64.b64decode(t), -15).decode('utf-8')))
        out.append((d.get('name'), m))
    return out


def parse_page(m):
    rects, kinds, edges = {}, {}, []
    for c in m.iter('mxCell'):
        g = c.find('mxGeometry')
        if c.get('vertex') == '1' and g is not None:
            cid = c.get('id')
            try:
                x = float(g.get('x')); y = float(g.get('y'))
                w = float(g.get('width')); h = float(g.get('height'))
            except (TypeError, ValueError):
                continue
            if cid.startswith('lane') or cid == 'frame' or cid.endswith('_tag') \
                    or cid.endswith('_badge'):
                continue
            if w < 40 or h < 20:
                continue
            rects[cid] = (x, y, w, h)
            kinds[cid] = 'D' if 'rhombus' in (c.get('style') or '') else 'P'
        elif c.get('edge') == '1':
            st = c.get('style') or ''
            def num(k, dv):
                mm = re.search(k + r'=([\d.]+)', st)
                return float(mm.group(1)) if mm else dv
            pts = []
            if g is not None:
                arr = g.find('Array')
                if arr is not None:
                    pts = [(float(p.get('x')), float(p.get('y'))) for p in arr.findall('mxPoint')]
            edges.append((c.get('source'), c.get('target'), num('exitX', .5), num('exitY', .5),
                          num('entryX', .5), num('entryY', .5), pts, c.get('value') or ''))
    return rects, kinds, edges


def poly(s, t, ex, ey, nx, ny, pts, rects):
    sx, sy, sw, sh = rects[s]
    tx, ty, tw, th = rects[t]
    return ([(sx + sw * ex, sy + sh * ey)] + list(pts) +
            [(tx + tw * nx, ty + th * ny)])


def segs(p):
    return [(p[i], p[i + 1]) for i in range(len(p) - 1)
            if abs(p[i][0] - p[i + 1][0]) > 1 or abs(p[i][1] - p[i + 1][1]) > 1]


def crosses_rect(a, b, r):
    x, y, w, h = r
    (x1, y1), (x2, y2) = a, b
    if abs(x1 - x2) < 1:
        return x + 1 < x1 < x + w - 1 and not (max(y1, y2) <= y + 1 or min(y1, y2) >= y + h - 1)
    if abs(y1 - y2) < 1:
        return y + 1 < y1 < y + h - 1 and not (max(x1, x2) <= x + 1 or min(x1, x2) >= x + w - 1)
    return False


def seg_overlap(a, b, c, d):
    (x1, y1), (x2, y2) = a, b
    (x3, y3), (x4, y4) = c, d
    if abs(y1 - y2) < 1 and abs(y3 - y4) < 1 and abs(y1 - y3) < 1.5:
        return max(0, min(max(x1, x2), max(x3, x4)) - max(min(x1, x2), min(x3, x4)))
    if abs(x1 - x2) < 1 and abs(x3 - x4) < 1 and abs(x1 - x3) < 1.5:
        return max(0, min(max(y1, y2), max(y3, y4)) - max(min(y1, y2), min(y3, y4)))
    return 0


def seg_cross(a, b, c, d):
    (x1, y1), (x2, y2) = a, b
    (x3, y3), (x4, y4) = c, d
    if abs(y1 - y2) < 1 and abs(x3 - x4) < 1:
        return (min(x1, x2) + 2 < x3 < max(x1, x2) - 2 and
                min(y3, y4) + 2 < y1 < max(y3, y4) - 2)
    if abs(x1 - x2) < 1 and abs(y3 - y4) < 1:
        return (min(y1, y2) + 2 < y3 < max(y1, y2) - 2 and
                min(x3, x4) + 2 < x1 < max(x3, x4) - 2)
    return False


def run(path):
    tot = dict(thru=0, ov=0, cross=0, segs=0, len=0, edges=0)
    print(f"\n===== {path.split('/')[-1]} =====")
    for name, m in models(path):
        rects, kinds, edges = parse_page(m)
        thru = ov = cross = nseg = 0
        length = 0.0
        allsegs = []
        for i, e in enumerate(edges):
            s, t = e[0], e[1]
            if s not in rects or t not in rects:
                continue
            p = poly(s, t, e[2], e[3], e[4], e[5], e[6], rects)
            ss = segs(p)
            nseg += len(ss)
            length += sum(math.dist(a, b) for a, b in ss)
            for a, b in ss:
                for nid, r in rects.items():
                    if nid in (s, t):
                        continue
                    if crosses_rect(a, b, r):
                        thru += 1
                        print(f"   ⚠️ 穿框 {s}->{t} ({a[0]:.0f},{a[1]:.0f})-({b[0]:.0f},{b[1]:.0f}) 穿过 {nid}")
                        break
                allsegs.append((i, s, t, a, b))
        for x in range(len(allsegs)):
            for y in range(x + 1, len(allsegs)):
                i1, s1, t1, a1, b1 = allsegs[x]
                i2, s2, t2, a2, b2 = allsegs[y]
                if i1 == i2:
                    continue
                if seg_overlap(a1, b1, a2, b2) > 6 and not ({s1, t1} & {s2, t2}):
                    ov += 1
                    print(f"   ⚠️ 压线 {s1}->{t1} 与 {s2}->{t2}")
                if seg_cross(a1, b1, a2, b2):
                    cross += 1
        ne = len(edges)
        print(f"  {name[:34]:36} 节点{len(rects):2d} 线{ne:3d} 折点/线{nseg/max(ne,1):.1f} "
              f"总线长{length/1000:.1f}k 穿框{thru} 压线{ov} 交叉{cross}")
        for k2, v in (('thru', thru), ('ov', ov), ('cross', cross), ('segs', nseg),
                      ('len', length), ('edges', ne)):
            tot[k2] += v
    print(f"  ── 合计: 线{tot['edges']} 折点/线{tot['segs']/max(tot['edges'],1):.2f} "
          f"总线长{tot['len']/1000:.1f}k 穿框{tot['thru']} 压线{tot['ov']} 交叉{tot['cross']}")
    return tot


if __name__ == '__main__':
    for p in sys.argv[1:]:
        run(p)
