# -*- coding: utf-8 -*-
"""多页 .drawio 几何验证：逐页检查连线线段是否穿过节点矩形。

只检查带 waypoints（<Array as="points">）的边 —— 没给 waypoints 的边由 draw.io
的 orthogonalEdgeStyle 自动避让，无数据可查属正常。

用法：
  python3 verify_drawio_multipage.py 文件.drawio
输出：每页 连线数 / 穿框数；末尾给总计（交付话术直接用这个数字）。

⭐ 交付前必跑；报告"0 处穿框"才算画好。因为服务器端无法预览渲染，
   几何求交是唯一能把"不穿框"变成可判定事实的手段。
"""
import sys
import xml.etree.ElementTree as ET


def rect_of(c):
    g = c.find('mxGeometry')
    if g is None or g.get('x') is None:
        return None
    return (float(g.get('x')), float(g.get('y')),
            float(g.get('width')), float(g.get('height')))


def seg_hits_rect(p1, p2, rc, pad=2, eps=0.5):
    x1, y1, w, h = rc
    x1 += pad; y1 += pad
    x2 = x1 + w - 2 * pad; y2 = y1 + h - 2 * pad
    ax, ay = p1; bx, by = p2
    if abs(ay - by) < eps:                       # 水平段
        if not (y1 < ay < y2):
            return False
        lo, hi = sorted((ax, bx))
        return lo < x2 and hi > x1
    if abs(ax - bx) < eps:                       # 垂直段
        if not (x1 < ax < x2):
            return False
        lo, hi = sorted((ay, by))
        return lo < y2 and hi > y1
    return False


def main():
    p = sys.argv[1]
    root = ET.parse(p).getroot()
    total_bad = 0
    for d in root.findall('.//diagram'):
        m = d.find('mxGraphModel')
        if m is None:
            continue
        cells = m.findall('.//mxCell')
        nodes = {}
        for c in cells:
            if c.get('vertex') != '1':
                continue
            st = c.get('style') or ''
            if 'swimlane' in st or st.startswith('text'):
                continue
            rc = rect_of(c)
            if rc:
                nodes[c.get('id')] = rc
        bad = checked = 0
        for c in cells:
            if c.get('edge') != '1':
                continue
            s, t = c.get('source'), c.get('target')
            g = c.find('mxGeometry')
            pts = [(float(q.get('x')), float(q.get('y')))
                   for q in g.findall('.//mxPoint')] if g is not None else []
            if len(pts) < 2:
                continue
            checked += 1
            for i in range(len(pts) - 1):
                for nid, rc in nodes.items():
                    if nid in (s, t):
                        continue
                    if seg_hits_rect(pts[i], pts[i + 1], rc):
                        bad += 1
                        print(f"  ⚠️ [{d.get('name')}] {s}→{t} 段{i} 穿过 {nid}")
                        break
        total_bad += bad
        print(f"  {'✅' if bad == 0 else '❌'} {str(d.get('name'))[:34]:36} "
              f"连线{checked:3d}  穿框 {bad}")
    print(f"\n{'✅ 全部通过：0 处穿框' if total_bad == 0 else f'❌ 共 {total_bad} 处穿框'}")


if __name__ == '__main__':
    main()
