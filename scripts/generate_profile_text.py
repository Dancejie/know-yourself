#!/usr/bin/env python3
"""
generate_profile_text.py
根据 know_yourself_stats.json 调用 AI，生成个性化档案文本（各板块英/中双语）。
输出：/tmp/know_yourself_profile.json

用法：python3 generate_profile_text.py \
        --stats /tmp/know_yourself_stats.json \
        --user-name "阑干" \
        --user-code "DANGSI" \
        --agent-name "Alice" \
        --dob "1998-12-31" \
        --affiliation "小红书 · 大模型创新策略研究" \
        --bg "软件工程+金融数学双学位（西北大学），法国审计商学院金融科技MSc，前私募/中金/科大讯飞"
"""

import argparse, json, os, sys, textwrap
from pathlib import Path

# ── 参数 ─────────────────────────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument("--stats",       required=True)
ap.add_argument("--user-name",   default="SUBJECT")
ap.add_argument("--user-code",   default="UNKNOWN")
ap.add_argument("--agent-name",  default="Alice")
ap.add_argument("--dob",         default="REDACTED")
ap.add_argument("--affiliation", default="REDACTED")
ap.add_argument("--bg",          default="")
ap.add_argument("--out",         default="/tmp/know_yourself_profile.json")
args = ap.parse_args()

stats = json.loads(Path(args.stats).read_text())

# ── 整理数字摘要供 AI 使用 ─────────────────────────────────────────────────
topics      = stats["topics"]["distribution"]
top3_topics = sorted(topics.items(), key=lambda x: -x[1]["pct"])[:3]
top3_str    = " / ".join(f"{k}({v['pct']}%)" for k, v in top3_topics)

soul        = stats["soul_scores"]
logos_pct   = soul["logos"]["pct"]
thumos_pct  = soul["thumos"]["pct"]
epi_pct     = soul["epithumia"]["pct"]

caps        = stats["capability_scores"]
cap_sorted  = sorted(caps.items(), key=lambda x: -x[1])
cap_top3    = " / ".join(f"{k}={v}" for k, v in cap_sorted[:3])
cap_low     = " / ".join(f"{k}={v}" for k, v in cap_sorted[-2:])

time_pat    = stats["time_pattern"]["pattern_label"]
peak_hours  = stats["time_pattern"]["peak_hours"][0]

qs_dom      = stats["question_style"]["dominant_style"]
qs_dist     = stats["question_style"]["style_distribution"]
avg_len     = stats["language_style"]["avg_message_length"]
emoji_pct   = stats["language_style"]["emoji_usage_pct"]

keywords    = [kw for kw, _ in stats["top_keywords"][:10]]
kw_str      = " · ".join(keywords)

sessions_n  = stats["session_count"]
date_range  = stats["date_range"]

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT = f"""You are a behavioral intelligence analyst writing a classified dossier in the style of a Cold War intelligence file. Your writing must be:
- Clinical, precise, and formal (like a real psychological assessment or FBI profile)
- Evidence-based: every claim references the data below
- Bilingual: output English first, then Chinese translation in parentheses (中文)
- Specific to THIS individual's data — do NOT use generic archetypes unless the data supports them
- NO emoji, NO bullet-point cards, NO corporate report language
- Chapters should flow as analytical prose paragraphs

SUBJECT DATA:
- Name/Code: {args.user_name} / {args.user_code}
- DOB: {args.dob}
- Affiliation: {args.affiliation}
- Background: {args.bg}
- Sessions analyzed: {sessions_n} ({date_range})
- Top topics: {top3_str}
- Soul scores: Logos={logos_pct}%, Thumos={thumos_pct}%, Epithumia={epi_pct}%
- Capability top: {cap_top3}
- Capability low: {cap_low}
- Time pattern: {time_pat}, peak at {peak_hours}
- Question style: dominant={qs_dom}, distribution={qs_dist}
- Avg message length: {avg_len:.0f} chars
- Emoji usage: {emoji_pct}%
- Top keywords: {kw_str}

Write the following sections. For EACH section output exactly:
SECTION: <section_id>
EN: <English prose, 2-4 sentences>
ZH: <Chinese prose, same content>
---

Sections to write:
1. identity_summary — Who this person is based on behavioral evidence
2. strengths_intro — Opening line for the strengths section
3. str_1 — First and most dominant strength (derive from data, title it meaningfully)
4. str_2 — Second strength
5. str_3 — Third strength
6. str_4 — Fourth strength (if data supports; else note "insufficient data")
7. str_5 — Fifth strength (if data supports; else note "insufficient data")
8. psych_profile — Psychological/behavioral profile based on soul scores + time pattern + question style
9. vuln_1 — First cognitive vulnerability (derive from data)
10. vuln_2 — Second cognitive vulnerability
11. vuln_3 — Third cognitive vulnerability (if data supports)
12. trajectory — Strategic trajectory and career vector
13. analyst_note — Closing analyst note, final archetype classification
"""

# ── 调用 AI（通过 OpenClaw 内部 API）────────────────────────────────────────
import subprocess, re

def call_ai(prompt: str) -> str:
    """通过 clawd 内部路由调用当前配置的 AI 模型"""
    # 使用环境变量中的 gateway token（如果有），否则尝试 stdin 传递
    # 本脚本通过 exec tool 从 Alice 调用，直接用 Python http 请求 localhost gateway
    import urllib.request, urllib.error
    
    payload = json.dumps({
        "model": "anthropic/claude-4.6-sonnet-google",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "temperature": 0.3,
    }).encode()
    
    # 尝试 OpenAI-compatible endpoint（OpenClaw gateway 默认暴露）
    endpoints = [
        "http://127.0.0.1:3000/v1/chat/completions",
        "http://localhost:3000/v1/chat/completions",
    ]
    
    for ep in endpoints:
        try:
            req = urllib.request.Request(ep, data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception:
            continue
    
    raise RuntimeError("无法连接到 OpenClaw Gateway API，请确保 gateway 在运行")

# ── 解析 AI 输出 ──────────────────────────────────────────────────────────────
def parse_sections(raw: str) -> dict:
    """解析 SECTION/EN/ZH 格式输出"""
    result = {}
    current_id = None
    current_en = []
    current_zh = []
    mode = None
    
    for line in raw.split("\n"):
        line = line.rstrip()
        if line.startswith("SECTION:"):
            if current_id:
                result[current_id] = {
                    "en": " ".join(current_en).strip(),
                    "zh": " ".join(current_zh).strip()
                }
            current_id = line.split(":", 1)[1].strip()
            current_en = []
            current_zh = []
            mode = None
        elif line.startswith("EN:"):
            mode = "en"
            current_en.append(line[3:].strip())
        elif line.startswith("ZH:"):
            mode = "zh"
            current_zh.append(line[3:].strip())
        elif line == "---":
            continue
        elif mode == "en" and line:
            current_en.append(line)
        elif mode == "zh" and line:
            current_zh.append(line)
    
    # 最后一个
    if current_id:
        result[current_id] = {
            "en": " ".join(current_en).strip(),
            "zh": " ".join(current_zh).strip()
        }
    return result

# ── 主流程 ────────────────────────────────────────────────────────────────────
print("正在调用 AI 生成个性化档案文本...", flush=True)

raw = call_ai(PROMPT)
sections = parse_sections(raw)

# 组装输出
output = {
    "meta": {
        "user_name":   args.user_name,
        "user_code":   args.user_code,
        "agent_name":  args.agent_name,
        "dob":         args.dob,
        "affiliation": args.affiliation,
        "bg":          args.bg,
        "date_range":  date_range,
        "sessions_n":  sessions_n,
    },
    "soul": {
        "logos":      logos_pct,
        "thumos":     thumos_pct,
        "epithumia":  epi_pct,
    },
    "topics":    {k: v["pct"] for k, v in topics.items()},
    "cap_scores": caps,
    "keywords":  keywords,
    "sections":  sections,
    "raw_ai":    raw,
}

Path(args.out).write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(f"✓ 输出: {args.out}")
print(f"✓ 解析了 {len(sections)} 个板块: {list(sections.keys())}")
