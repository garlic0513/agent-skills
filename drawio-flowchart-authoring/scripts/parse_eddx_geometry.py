#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 .eddx（万兴亿图 EdrawMax）的【几何 + 文字】，用来读懂用户/客户发来的流程图草稿。

用法:
    python3 parse_eddx_geometry.py 图.eddx
    python3 parse_eddx_geometry.py 图.eddx --page 1 --maxtext 120

输出:
    ① 泳道清单（坐标/宽高/横竖判定）        ← 决定你该用横向带还是垂直列布局
    ② 节点文字清单（去重·按 y,x 排序）      ← 决定节点内容与顺序
    ③ 形状类型统计 / 画布大致尺寸

为什么需要它: 只提文字读不出「泳道是横是竖 / 每条带多高 / 流程怎么绕圈」，
而这些恰是「该照抄什么」的关键。详见 references/eddx-geometry-parsing.md
"""
import sys, re, html, zipfile, argparse
import xml.etree.ElementTree as ET


def localname(tag):
    return tag.split('}')[-1]


def gv(el, name):
    """取 <name V="..."/> 的 V 值"""
    e = el.find(f'.//{name}')
    return e.get('V') if e is not None else None


def fnum(v):
    try:
        return float(v)
    except Exception:
        return None


def gettext(el):
    t = el.find('.//Text')
    if t is None:
        return ''
    return re.sub(r'\s+', ' ', html.unescape(''.join(t.itertext()))).strip()


def parse(xml_bytes):
    raw = xml_bytes.decode('utf-8', errors='ignore')
    x = re.sub(r'\sxmlns(:\w+)?="[^"]*"', '', raw)   # ⚠️ 必须去命名空间，否则遍历不到
    root = ET.fromstring(x)

    shapes = []
    for el in root.iter():
        if localname(el.tag) != 'Shape':
            continue
        tr = el.find('Transform')
        if tr is None:
            continue
        w = fnum(gv(tr, 'Width')); h = fnum(gv(tr, 'Height'))
        gx = fnum(gv(tr, 'GPinX')); gy = fnum(gv(tr, 'GPinY'))
        lpx = fnum(gv(tr, 'LocPinX')) or 0.0
        lpy = fnum(gv(tr, 'LocPinY')) or 0.0
        ang = fnum(gv(tr, 'Angle')) or 0.0
        if None in (w, h, gx, gy):
            continue
        left, top = gx - lpx, gy - lpy
        if abs(ang - 90) < 1 or abs(ang - 270) < 1:
            left, top, w, h = top, left, h, w          # ⚠️ 旋转 → 宽高互换
        shapes.append(dict(id=el.get('ID'), typ=el.get('Type'), x=left, y=top,
                           w=w, h=h, ang=ang, txt=gettext(el)))
    return shapes


def report(shapes, maxtext=200):
    from collections import Counter
    print(f"形状总数: {len(shapes)}")
    print("类型分布:", dict(Counter(s['typ'] for s in shapes)))

    lanes = [s for s in shapes if s['typ'] == 'SwimLane']
    if not lanes:   # 兜底：按尺寸猜
        lanes = [s for s in shapes if (s['w'] > 3000 and s['h'] < 600) or (s['h'] > 1200 and s['w'] < 900)]
    lanes.sort(key=lambda s: (s['y'], s['x']))
    print(f"\n=== 泳道 ({len(lanes)}) ===")
    for s in lanes:
        ori = '横向带' if s['w'] > s['h'] else '垂直列'
        print(f"  [{ori}] x={s['x']:8.0f} y={s['y']:8.0f} w={s['w']:7.0f} h={s['h']:7.0f}"
              f" ang={s['ang']:3.0f} | {s['txt'][:40]}")
    if lanes:
        lane_ids = {id(s) for s in lanes}
        wmax = max(s['x'] + s['w'] for s in lanes)
        hmax = max(s['y'] + s['h'] for s in lanes)
        print(f"  → 画布大致 {wmax:.0f} × {hmax:.0f}")
        n_rows = max((s['h'] for s in lanes), default=0)
        print(f"  → 单条带最高 {n_rows:.0f}px"
              f"（若 ≈200~280 说明【每条带只有一行节点】= 多圈推进式布局）")

    nodes = [s for s in shapes if s['txt'] and s['typ'] != 'SwimLane']
    seen, uniq = set(), []
    for s in nodes:                       # ⚠️ Edraw 会把同一段文字存两遍（Group+Shape）
        t = re.sub(r'\s+', '', s['txt'])
        if t in seen:
            continue
        seen.add(t); uniq.append(s)
    uniq.sort(key=lambda s: (round(s['y'] / 80), s['x']))
    print(f"\n=== 带文字的节点 ({len(uniq)}) 按 (y,x) ===")
    for s in uniq[:maxtext]:
        print(f"  x={s['x']:7.0f} y={s['y']:7.0f} {s['w']:5.0f}x{s['h']:5.0f} | {s['txt'][:80]}")
    if len(uniq) > maxtext:
        print(f"  …（还有 {len(uniq) - maxtext} 条，用 --maxtext 调大）")
    return lanes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--page', type=int, default=1, help='第几页（默认 1）')
    ap.add_argument('--maxtext', type=int, default=200)
    a = ap.parse_args()

    z = zipfile.ZipFile(a.path)
    names = [n for n in z.namelist() if re.match(rf'pages/page{a.page}\.xml$', n)]
    if not names:
        print('包内文件:', [n for n in z.namelist()]); sys.exit(1)
    shapes = parse(z.read(names[0]))
    print(f"# 文件: {a.path}\n# 页: {names[0]}\n")
    report(shapes, a.maxtext)


if __name__ == '__main__':
    main()
