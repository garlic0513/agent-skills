#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_drawio_preview.py —— 把 .drawio 变成可用浏览器打开的 draw.io 真渲染预览页

用法:
    python3 make_drawio_preview.py 图.drawio                 # 全部页 → webapp/_preview/pN.html
    python3 make_drawio_preview.py 图.drawio --pages 2 5     # 只出第 2、5 页
    python3 make_drawio_preview.py 图.drawio --zoom 1.6 --no-resize   # 放大看局部（配滚动）
    python3 make_drawio_preview.py 图.drawio --out /tmp/prev          # 换输出目录

之后:
    cd ~/.cache/drawio-mcp-server/webapp && python3 -m http.server 8899 --bind 127.0.0.1
    browser_navigate http://127.0.0.1:8899/_preview/p2.html

⚠️ 前提: webapp 目录存在（drawio-mcp-server 装过并解包了 draw.war）。
   不存在时本脚本会明确报出来，别猜。
"""
import argparse
import base64
import html
import json
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

DEFAULT_WEBAPP = os.path.expanduser('~/.cache/drawio-mcp-server/webapp')


def models(path):
    """取每页的 mxGraphModel 元素（兼容未压缩 / 压缩两种 <diagram>）"""
    root = ET.parse(path).getroot()
    out = []
    for d in root.findall('diagram'):
        m = d.find('mxGraphModel')
        if m is None:
            t = (d.text or '').strip()
            if not t:
                continue
            m = ET.fromstring(urllib.parse.unquote(
                zlib.decompress(base64.b64decode(t), -15).decode('utf-8')))
        out.append((d.get('name') or 'page', m))
    return out


def make_page(model_xml, zoom, resize, border):
    cfg = json.dumps({"xml": model_xml, "toolbar": "", "nav": False,
                      "resize": resize, "zoom": zoom, "border": border},
                     ensure_ascii=False)
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<style>body{margin:0;background:#fff}</style></head><body>'
        f'<div class="mxgraph" data-mxgraph="{html.escape(cfg, quote=True)}"></div>'
        '<script src="../js/viewer.min.js"></script></body></html>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('drawio')
    ap.add_argument('--out', default=None, help='默认 <webapp>/_preview')
    ap.add_argument('--pages', nargs='*', type=int, default=None)
    ap.add_argument('--zoom', type=float, default=0.85)
    ap.add_argument('--no-resize', action='store_true',
                    help='按 zoom 原样渲染（看局部放大用），需自己滚动')
    ap.add_argument('--border', type=int, default=16)
    ap.add_argument('--webapp', default=DEFAULT_WEBAPP)
    a = ap.parse_args()

    if not os.path.isdir(a.webapp):
        sys.exit(f"⚠️ 找不到 {a.webapp}\n"
                 "   先装 drawio-mcp-server（war 会自动解包到该路径），"
                 "见 references/drawio-mcp-live-connection.md")
    if not os.path.exists(os.path.join(a.webapp, 'js', 'viewer.min.js')):
        sys.exit(f"⚠️ {a.webapp}/js/viewer.min.js 不存在 —— 解包不完整，重新解包 draw.war")

    out = a.out or os.path.join(a.webapp, '_preview')
    os.makedirs(out, exist_ok=True)
    pages = models(a.drawio)
    if not pages:
        sys.exit("⚠️ 文件里没有可取出的 diagram")

    n = 0
    for i, (name, m) in enumerate(pages, 1):
        if a.pages and i not in a.pages:
            continue
        xml = ET.tostring(m, encoding='unicode')
        fp = os.path.join(out, f'p{i}.html')
        open(fp, 'w', encoding='utf-8').write(
            make_page(xml, a.zoom, not a.no_resize, a.border))
        n += 1
        print(f"  ✅ p{i}  {name[:40]}  → {fp}")

    rel = os.path.relpath(out, a.webapp)
    print(f"\n共 {n} 页。下一步：\n"
          f"  cd {a.webapp} && python3 -m http.server 8899 --bind 127.0.0.1\n"
          f"  browser_navigate http://127.0.0.1:8899/{rel}/p1.html")


if __name__ == '__main__':
    main()
