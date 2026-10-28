# -*- coding: utf-8 -*-
"""garlic-drawio-flowchart-authoring 落地质量评测器（自建 runner）

为什么不用 `waza run`：waza 的执行器只有 copilot-sdk / mock，驱动不了 Hermes。
但它的 **eval.yaml schema + grader 思路**（file must_exist / content_patterns）被完整沿用，
所以这套 eval 是可迁移的。

用法：
  python3 evals/runner.py --mode with-skill          # 只跑加载技能
  python3 evals/runner.py --mode without-skill       # 只跑不加载（A/B 基线）
  python3 evals/runner.py --mode both --tasks T1,T2,T6
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time
import xml.etree.ElementTree as ET

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_NAME = "garlic-drawio-flowchart-authoring"
EVALS = os.path.join(SKILL_DIR, "evals")

TASKS = {
 "T1": dict(name="基础画图", prompt=(
   "把下面这段流程画成 draw.io 流程图，保存为 out.drawio（当前目录）：\n"
   "① 收货员扫码收货 ② 系统带出批次 ③ 复核员核对数量与批次 ④ 复核通过则生成待检库存，"
   "不通过则退回收货员 ⑤ 流程结束。要求：两个泳道（仓储部（收货员）、仓储部（复核员））、"
   "判断节点用菱形、节点编号用 10/20/30 形式。")),
 "T2": dict(name="编号规则", prompt=(
   "画一条 5 个步骤的入库流程到 out.drawio（当前目录）。"
   "硬性要求：编号必须是 10、20、30 连续等差，流程开始和流程结束不编号，中间不留空号。")),
 "T3": dict(name="泳道与职责分离", prompt=(
   "画一条收货流程到 out.drawio（当前目录）：收货员扫码录入、复核员确认、系统生成库存。"
   "要求：执行岗和复核岗必须是两条独立泳道，不能合并。")),
 "T4": dict(name="判定与分支标签", prompt=(
   "画一条含判断分支的流程到 out.drawio（当前目录）：收货后判断数量是否一致，"
   "一致则入库，不一致则退回。判断必须用菱形，两条出边必须标「是」「否」。")),
 "T5": dict(name="修图：编号与断链", prompt=(
   "当前目录的 broken.drawio 有编号问题和断链问题，请修复后另存为 out.drawio。"
   "要求：编号连续等差、起止不编号、没有悬空连线。")),
 "T7a": dict(name="大页压测·只查几何", timeout=300, prompt=(
   "把一条至少 30 个节点的入库流程（供应商送货、扫码收货、复核、取样、检验、放行、上架）"
   "全部展开画进【一张 A3 横向页面】（1654×1169），保存为 out.drawio。"
   "只需要保证：一页放完、编号连续、连线不穿节点框、交叉尽可能少。"
   "不用做真渲染视觉检查，做完跑一下几何自检即可。")),
 "T7b": dict(name="大页压测·含视觉迭代", timeout=900, prompt=(
   "把一条至少 30 个节点的入库流程全部展开画进【一张 A3 横向页面】（1654×1169），保存为 out.drawio，"
   "并且必须真渲染成图、自己看一遍：文字不能溢出节点框、标签不能压线、连线不能穿节点。"
   "如果发现不达标就自己改，直到你认为可以交付为止。")),
 "T7": dict(name="大页压测（30+节点压一页）", prompt=(
   "把一条至少 30 个节点的入库流程（从供应商送货、扫码收货、复核、取样、检验、放行到上架）"
   "全部展开画进【一张 A3 横向页面】（1654×1169），保存为 out.drawio。"
   "要求：一页放完不拆页、字号不小于 6pt、文字不溢出节点框、连线不穿节点。")),
 "T8": dict(name="子流程调用（两页）", prompt=(
   "在 out.drawio 里建两个页：第1页「成品入库主流程」，第2页「质检子流程」。"
   "主流程走到质检那一步时用【双线框（子流程形状）】表示调用，并注明「见第2页」；"
   "第2页画质检的 4 个步骤（取样、检验、录入结果、出报告）。")),
 "T9": dict(name="超收短收三分支", prompt=(
   "画一条含超收短收处置的入库流程到 out.drawio：收货数量与订单不符时，"
   "分出三种处置方式——① 退回供应商 ② 要求补发 ③ 修改订单按实收，"
   "三条支路都要在连线上写清标签，最后汇合到收货确认。")),
 "T6": dict(name="负样本（不该画图）", prompt=(
   "我们公司出差住宿标准是多少？一句话回答。")),
}

def run_hermes(ws, prompt, with_skill, timeout=420):
    # ⚠️ hermes -z 的文件工具用的是它自己的工作目录，不跟随 shell cwd
    # → 必须在 prompt 里给绝对路径，否则产物会落到 ~ 下，评分全 0（踩过一次）
    prompt = (prompt + f"\n\n【输出目录】所有产物请保存到 {ws} 下，文件名按题目要求，"
              f"使用绝对路径。")
    cmd = ["hermes", "-z", prompt]
    if with_skill:
        cmd += ["--skills", SKILL_NAME]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "", timeout, True
    return out.strip(), round(time.time() - t0, 1), False

def shapes(path):
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None
    return [c for c in root.iter("mxCell") if c.get("vertex") == "1"]

def texts(cells):
    import html as H
    return [re.sub(r"<[^>]+>", "", H.unescape(c.get("value") or "")) for c in cells]

def nums(cells):
    out = []
    for t in texts(cells):
        m = re.match(r"\s*(\d+)\s", t)
        if m: out.append(int(m.group(1)))
    return out

def geom_check(path):
    """调技能自带体检脚本 → (穿框数, 交叉数)"""
    for cand in ("check_lines_per_page.py",):
        s = os.path.join(SKILL_DIR, "scripts", cand)
        if not os.path.exists(s): continue
        try:
            p = subprocess.run([sys.executable, s, path], capture_output=True, text=True, timeout=120)
            txt = p.stdout + p.stderr
            cross = re.search(r"交叉[^\d]*(\d+)", txt)
            through = re.search(r"穿框[^\d]*(\d+)", txt)
            return (int(through.group(1)) if through else None,
                    int(cross.group(1)) if cross else None, txt)
        except Exception as e:
            return (None, None, str(e))
    return (None, None, "")

def grade(tid, ws, answer):
    """返回 (score 0/1, 说明 list)"""
    notes, ok = [], True
    out = os.path.join(ws, "out.drawio")

    if tid == "T6":
        made = os.path.exists(out) or [f for f in os.listdir(ws) if f.endswith(".drawio")]
        has350 = "350" in (answer or "")
        ok = (not made) and has350
        notes.append(f"未生成 drawio={not made}；答出 350={has350}")
        return int(ok), notes

    if not os.path.exists(out):
        return 0, ["未生成 out.drawio"]
    cells = shapes(out)
    if cells is None:
        return 0, ["out.drawio 不是合法 XML"]
    ts = texts(cells)
    ns = nums(cells)

    if tid == "T1":
        lanes = [c for c in cells if "swimlane" in (c.get("style") or "")]
        has_dia = any("rhombus" in (c.get("style") or "") for c in cells)
        ok = len(cells) >= 5 and len(lanes) >= 2 and has_dia
        notes.append(f"形状 {len(cells)}≥5={len(cells)>=5}；泳道 {len(lanes)}≥2={len(lanes)>=2}；菱形={has_dia}")
    elif tid == "T2":
        expect = list(range(10, 10 * (len(ns) + 1), 10))
        ok = len(ns) >= 4 and ns == expect
        notes.append(f"编号序列 {ns}；期望 {expect}；一致={ns==expect}")
    elif tid == "T3":
        lanes = [c for c in cells if "swimlane" in (c.get("style") or "")]
        ok = len(lanes) >= 2 and any("复核" in (t or "") for t in texts(lanes))
        notes.append(f"泳道数 {len(lanes)}；含复核泳道={any('复核' in (t or '') for t in texts(lanes))}")
    elif tid == "T4":
        has_dia = any("rhombus" in (c.get("style") or "") for c in cells)
        labels = [ (c.get("value") or "") for c in ET.parse(out).getroot().iter("mxCell") if c.get("edge") == "1" ]
        yn = any("是" in l for l in labels) and any("否" in l for l in labels)
        ok = has_dia and yn
        notes.append(f"菱形={has_dia}；是/否标签={yn}（标签：{labels}）")
    elif tid == "T5":
        expect = list(range(10, 10 * (len(ns) + 1), 10))
        root = ET.parse(out).getroot()
        edges = [c for c in root.iter("mxCell") if c.get("edge") == "1"]
        ids = {c.get("id") for c in cells}
        dangling = [e.get("id") for e in edges
                    if (e.get("source") and e.get("source") not in ids)
                    or (e.get("target") and e.get("target") not in ids)]
        ok = ns == expect and not dangling
        notes.append(f"编号 {ns}（一致={ns==expect}）；悬空连线 {len(dangling)} 条")

    elif tid in ("T7", "T7a", "T7b"):
        n = len(cells)
        through, cross, _ = geom_check(out)
        lim = max(1, n // 4)
        ok = n >= 25 and (through or 0) == 0 and (cross or 0) <= lim
        notes.append(f"节点 {n}≥25={n>=25}；穿框 {through}（需 0）；交叉 {cross}≤{lim}={(cross or 0)<=lim}")
    elif tid == "T8":
        root = ET.parse(out).getroot()
        pages = root.findall("diagram")
        has_sub = any("shape=process" in (c.get("style") or "")
                      for pg in pages for c in pg.iter("mxCell"))
        txts = " ".join(t or "" for pg in pages for c in pg.iter("mxCell")
                        for t in [c.get("value")])
        ok = len(pages) >= 2 and has_sub
        notes.append(f"页数 {len(pages)}≥2={len(pages)>=2}；双线框={has_sub}；提到第2页={'第2页' in txts}")
    elif tid == "T9":
        root = ET.parse(out).getroot()
        labels = [(c.get("value") or "") for c in root.iter("mxCell") if c.get("edge") == "1"]
        has = {k: any(k in l for l in labels) for k in ("退回", "补发", "改单")}
        if not has["改单"]:
            has["改单"] = any("修改" in l or "改单" in l for l in labels)
        ok = all(has.values())
        notes.append(f"三分支标签 退回={has['退回']} 补发={has['补发']} 改单/修改={has['改单']}")

    through, cross, _ = geom_check(out)
    if through is not None:
        notes.append(f"几何体检：穿框 {through}、交叉 {cross}")
        if through and through > 0:
            ok = False
            notes.append("⚠️ 存在连线穿框 → 判定不通过")
    return int(ok), notes

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["with-skill", "without-skill", "both"], default="with-skill")
    ap.add_argument("--tasks", default="T1,T2,T3,T4,T5,T6,T7,T8,T9")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    tids = [t.strip() for t in a.tasks.split(",") if t.strip()]
    modes = ["without-skill", "with-skill"] if a.mode == "both" else [a.mode]

    results = []
    for mode in modes:
        for tid in tids:
            t = TASKS[tid]
            ws = tempfile.mkdtemp(prefix=f"eval_{tid}_")
            if tid == "T5":
                fx = os.path.join(EVALS, "fixtures", "broken.drawio")
                if os.path.exists(fx): shutil.copy(fx, ws)
            print(f"\n=== {mode} / {tid} {t['name']} ===", flush=True)
            ans, secs, timedout = run_hermes(ws, t["prompt"], mode == "with-skill",
                                             timeout=t.get("timeout", 420))
            if timedout:
                print(f"  ⏱ 超时 {secs}s"); results.append((mode, tid, 0, "超时")); continue
            score, notes = grade(tid, ws, ans)
            print(f"  ⏱ {secs}s | 得分 {score}")
            for n in notes: print("   ·", n)
            results.append((mode, tid, score, "; ".join(notes)))
            if not a.keep: shutil.rmtree(ws, ignore_errors=True)

    print("\n" + "=" * 62)
    print(f"{'模式':<14}{'任务':<6}{'得分':<6}说明")
    for mode, tid, sc, note in results:
        print(f"{mode:<14}{tid:<6}{sc:<6}{note[:70]}")
    for mode in modes:
        got = [r for r in results if r[0] == mode]
        print(f"\n{mode}: {sum(r[2] for r in got)}/{len(got)} 通过")

if __name__ == "__main__":
    main()
