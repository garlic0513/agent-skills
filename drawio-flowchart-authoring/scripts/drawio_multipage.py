#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把多个 .drawio 合并成一个【多页可下钻】mxfile，并注入页间跳转链接。

用法:
    python3 drawio_multipage.py spec.json out.drawio

spec.json:
{
  "pages": [
    {"id": "tree",  "name": "00 流程树总览",   "file": "00-流程树总览图.drawio"},
    {"id": "p-1-1", "name": "1.1 采购收货流程图", "file": "采购收货流程图.drawio"},
    {"id": "p-1-3", "name": "1.3 成品入库流程图", "file": "成品入库流程图.drawio"}
  ],
  "root_page": "tree",
  "links": { "L2_1.1": "p-1-1", "L2_1.3": "p-1-3" },
  "back_label": "⬅ 返回流程树总览"
}

说明:
 · links: 哪个 mxCell id (=流程树上的二级流程节点) 点一下跳到哪一页
 · root_page: 各流程页左上角"返回"按钮的目标页; 不给则不生成返回按钮
 · 会自动跑 4 项自查: mxfile 包裹 / diagram 数 == mxGraphModel 数 / 链接数 / 各页节点数
"""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET

BACK_STYLE = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;"
              "strokeColor=#6c8ebf;fontSize=12;link=#data:page/id,{root};")


def get_model(path):
    """从单页 .drawio 或其 mxfile 包裹中抠出 mxGraphModel。"""
    x = open(path, encoding="utf-8").read()
    m = re.search(r"<mxGraphModel.*?</mxGraphModel>", x, re.S)
    if not m:
        raise SystemExit(f"❌ {path} 里找不到 mxGraphModel")
    return m.group(0)


def inject_links(model, links):
    """给指定 id 的 mxCell 的 style 末尾追加 link=#data:page/id,<pageId>。"""
    for cid, target in links.items():
        model = re.sub(
            rf'(<mxCell id="{re.escape(cid)}"[^>]*style=")([^"]*)(")',
            lambda m: f"{m.group(1)}{m.group(2)};link=#data:page/id,{target}{m.group(3)}",
            model,
        )
    return model


def add_back_button(model, root_page, label):
    btn = (f'<mxCell id="backbtn" value="{html.escape(label)}" '
           f'style="{BACK_STYLE.format(root=root_page)}" vertex="1" parent="1">'
           f'<mxGeometry x="20" y="14" width="150" height="32" as="geometry"/></mxCell>')
    return model.replace("</root>", btn + "</root>", 1)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out_path = sys.argv[2]
    root_page = spec.get("root_page")
    label = spec.get("back_label", "⬅ 返回总览")

    parts = []
    for pg in spec["pages"]:
        model = get_model(pg["file"])
        if pg["id"] == root_page:
            model = inject_links(model, spec.get("links", {}))
        elif root_page:
            model = add_back_button(model, root_page, label)
        parts.append(f'<diagram id="{pg["id"]}" name="{html.escape(pg["name"])}">{model}</diagram>')

    mxfile = ('<mxfile host="app.diagrams.net" modified="2026-01-01T00:00:00.000Z" '
              'agent="Hermes" version="24.0.0" type="device">' + "".join(parts) + "</mxfile>")
    open(out_path, "w", encoding="utf-8").write(mxfile)

    # ---- 自查 ----
    try:
        ET.fromstring(mxfile)
        print("✅ XML 合法")
    except Exception as e:  # noqa: BLE001
        print("❌ XML 非法:", e)
    n_diag = len(re.findall(r"<diagram ", mxfile))
    n_model = len(re.findall(r"<mxGraphModel", mxfile))
    print(f"diagram 数 {n_diag} | mxGraphModel 数 {n_model} "
          f"{'✅' if n_diag == n_model else '❌ 不相等，检查提取逻辑'}")
    print("跳转链接:", len(re.findall(r"link=#data:page/id", mxfile)),
          "（期望 ≈ 树→流程数 + 流程返树数）")
    for m in re.finditer(r'<diagram id="([^"]+)" name="([^"]+)">(.*?)</diagram>', mxfile, re.S):
        pid, nm, body = m.groups()
        print(f"   [{pid}] {nm}: {len(re.findall(r'vertex=.1.', body))} 节点")


if __name__ == "__main__":
    main()
