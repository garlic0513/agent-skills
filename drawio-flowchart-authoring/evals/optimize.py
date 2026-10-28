# -*- coding: utf-8 -*-
"""轻量优化循环（SkillOpt 思路的本机实现）

为什么不用官方 skillopt-train：它要求先按规范写一个自定义 benchmark env
（loader + rollout + evaluator，约 200 行），且目标模型是直连 LLM、不支持 Hermes
文件产出。这里用 **本技能自带的 e2e eval 当 reward**，用 DeepSeek 当 optimizer
提出**锚点式补丁**（anchor + insert），人工确认后应用——保守、可控、今天就能跑。

用法：
  python3 evals/optimize.py --tasks T1,T3,T4 --dry     # 只诊断，不改文件
"""
import argparse, json, os, re, subprocess, sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
RUNNER = os.path.join(SKILL_DIR, "evals", "runner.py")

def cfg_key():
    p = os.path.expanduser("~/.hermes/config.yaml")
    txt = open(p, encoding="utf-8").read()
    m = re.search(r"^  deepseek:.*?api_key:\s*(\S+)", txt, re.S | re.M)
    return m.group(1).strip('"\'') if m else None

def run_eval(tasks):
    p = subprocess.run([sys.executable, RUNNER, "--mode", "with-skill", "--tasks", tasks],
                       capture_output=True, text=True, timeout=1800)
    log = p.stdout + p.stderr
    rows = re.findall(r"^(with-skill)\s+(T\d)\s+(\d)\s+(.*)$", log, re.M)
    return [(t, int(s), note) for _, t, s, note in rows], log

def ask_optimizer(key, skill_text, failures):
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content":
             "你是 agent skill 的优化器。给定一个 SKILL.md 和它在评测中的失败记录，"
             "输出【最小补丁】：只补缺失的规则/判据，不要重写全文。"
             "严格输出 JSON：{\"diagnosis\":\"一句话\",\"edits\":[{\"anchor\":\"SKILL.md 中已存在的唯一一行片段\","
             "\"insert_after\":\"要插入的 markdown（≤6 行）\"}]}"},
            {"role": "user", "content":
             f"# SKILL.md（节选）\n{skill_text[:9000]}\n\n# 失败记录\n{json.dumps(failures, ensure_ascii=False, indent=2)}"}
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
    }
    p = subprocess.run(["curl", "-s", "--max-time", "120",
                        "https://api.deepseek.com/v1/chat/completions",
                        "-H", f"Authorization: Bearer {key}",
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(body, ensure_ascii=False)],
                       capture_output=True, text=True)
    try:
        d = json.loads(p.stdout)
        return json.loads(d["choices"][0]["message"]["content"])
    except Exception as e:
        return {"diagnosis": f"优化器调用失败: {e}", "edits": [], "raw": p.stdout[:300]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="T1,T3,T4,T5")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    print(f"① 跑基线 eval：{a.tasks}")
    rows, log = run_eval(a.tasks)
    total = sum(r[1] for r in rows) or 0
    print(f"   基线：{total}/{len(rows)} 通过")
    for t, s, n in rows:
        print(f"   {t} {'✅' if s else '❌'} {n[:90]}")

    fails = [{"task": t, "note": n} for t, s, n in rows if s == 0]
    if not fails:
        print("\n✅ 全部通过，无需优化")
        return

    print(f"\n② 优化器诊断（{len(fails)} 个失败任务）")
    key = cfg_key()
    if not key:
        print("❌ 找不到 DeepSeek key"); return
    skill = open(SKILL_MD, encoding="utf-8").read()
    prop = ask_optimizer(key, skill, fails)
    print("   诊断：", prop.get("diagnosis"))
    out = os.path.join(SKILL_DIR, "evals", "optimizer-proposal.json")
    open(out, "w", encoding="utf-8").write(json.dumps(prop, ensure_ascii=False, indent=2))
    for i, e in enumerate(prop.get("edits", []), 1):
        print(f"\n   --- 补丁 {i} ---\n   锚点：{e.get('anchor','')}\n   插入：\n{e.get('insert_after','')}")
        if e.get("anchor") and e["anchor"] not in skill:
            print("   ⚠️ 锚点在 SKILL.md 中找不到，需人工调整")
    print(f"\n③ 提案已存：{out}（--dry 模式不自动改文件）")

if __name__ == "__main__":
    main()
