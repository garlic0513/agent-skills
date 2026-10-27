# -*- coding: utf-8 -*-
"""解析任意 .drawio / mxfile：打印页数 + 每页泳道/形状/连线统计；detail 模式打印节点与连线明细。

兼容两种 <diagram> 内容形态（这是最容易踩的坑）：
  A) 未压缩 —— diagram 下有子元素 <mxGraphModel>（ET 里 d.text 为 None，
     ⚠️ 直接 ET.fromstring(d.text or '') 会报 `no element found: line 1, column 0`）
  B) 压缩   —— diagram 的 .text 是 base64(raw deflate) 再 urldecode 的字符串
     解码顺序必须是：base64.b64decode → zlib.decompress(data, -15) → urllib.parse.unquote

用法：
  python3 parse_drawio.py 文件.drawio            # 概览：每页 泳道/形状/连线 数
  python3 parse_drawio.py 文件.drawio detail 关键词   # 明细：匹配页的泳道/节点/连线标签
"""
import base64
import html
import sys
import urllib.parse
import zlib
import xml.etree.ElementTree as ET
from collections import Counter


def get_model(d):
    """取 <diagram> 下的 mxGraphModel，兼容未压缩/压缩两种形态"""
    m = d.find('mxGraphModel')
    if m is not None:                      # 形态 A：未压缩（公司模板多为这种）
        return m
    t = (d.text or '').strip()
    if not t:
        return None
    try:                                   # 形态 B：压缩
        xml = urllib.parse.unquote(
            zlib.decompress(base64.b64decode(t), -15).decode('utf-8'))
        return ET.fromstring(xml)
    except Exception:
        try:
            return ET.fromstring(urllib.parse.unquote(t))
        except Exception:
            return None


def kind_of(style):
    s = style or ''
    if 'swimlane' in s:      return 'swimlane'
    if 'rhombus' in s:       return 'rhombus'
    if 'ellipse' in s:       return 'ellipse'
    if 'shape=process' in s: return 'double'        # 子流程双层框
    if 'shape=document' in s:return 'document'
    if s.startswith('text'): return 'text'
    return 'rect'


def main():
    p = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'summary'
    key = sys.argv[3] if len(sys.argv) > 3 else ''
    root = ET.fromstring(open(p, encoding='utf-8', errors='ignore').read())
    diagrams = root.findall('.//diagram')
    print(f"页数: {len(diagrams)}")

    for i, d in enumerate(diagrams, 1):
        nm = d.get('name') or f'页{i}'
        if mode == 'detail' and key and key not in nm:
            continue
        m = get_model(d)
        if m is None:
            print(f"{i:2d}. 「{nm}」解析失败"); continue
        cells = m.findall('.//mxCell')
        sh = [c for c in cells if c.get('vertex') == '1']
        ed = [c for c in cells if c.get('edge') == '1']
        lanes = [c for c in sh if 'swimlane' in (c.get('style') or '')]

        if mode != 'detail':
            print(f"{i:2d}. 「{nm}」 泳道{len(lanes):2d} 形状{len(sh):3d} 连线{len(ed):3d}")
            continue

        print(f"\n{'='*64}\n【页{i}】{nm}")
        top = [c for c in lanes if c.get('parent') == '1']
        print(f"泳道({len(lanes)}) 顶层泳道({len(top)}):")
        for L in (top or lanes):
            print(f"  · {html.unescape(L.get('value') or '')[:30]}")
        print(f"形状类型: {dict(Counter(kind_of(c.get('style')) for c in sh))}")
        print("\n节点（尺寸 / 底色 / 文字）:")
        for c in sh:
            v = html.unescape(c.get('value') or '').replace('\n', ' ').strip()
            if not v:
                continue
            g = c.find('mxGeometry')
            w = g.get('width') if g is not None else '?'
            h = g.get('height') if g is not None else '?'
            st = c.get('style') or ''
            fill = ''
            for part in st.split(';'):
                if part.startswith('fillColor='):
                    fill = part.split('=', 1)[1]
            print(f"  · [{w}×{h}] fill={fill:8} {v[:64]}")
        print("\n连线标签:")
        for e in ed:
            v = html.unescape(e.get('value') or '').strip()
            if v:
                print(f"  → {v[:50]}")


if __name__ == '__main__':
    main()
