#!/usr/bin/env python3
"""
gen_incremental_content.py
增量更新模式：对比新旧 stats，找出有实质变化的段落，
输出 partial content JSON（只含变化段落），供 build_personalized.py 合并使用。

用法：
    python3 gen_incremental_content.py \
        --stats-new  /tmp/know_yourself_stats.json \
        --stats-old  /tmp/know_yourself_stats_prev.json \
        --content-prev /tmp/persona_content_prev.json \
        --output     /tmp/persona_content_delta.json

输出：
    delta.json  — 只包含需要更新的 key（未变化的 key 不写入，调用方保留旧值）
    delta.json["_summary"] — 本次更新摘要（供晚间通知使用）
    delta.json["_changed_keys"] — 本次变化的 key 列表
"""

import argparse, json, sys
from pathlib import Path
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# 变化检测：对比新旧 stats，返回哪些维度有实质变化
# ══════════════════════════════════════════════════════════════

THRESHOLD = {
    "topic_pct":      5.0,   # 话题占比变化 ≥5% 才算显著
    "session_count":  3,     # 新增会话 ≥3 才重写 Observation
    "avg_msg_len":  100,     # 平均消息长度变化 ≥100字
    "style_pct":      5.0,   # 互动风格分布变化 ≥5%
    "keyword_new":    2,     # Top10 关键词中有 ≥2 个是新的
}

def detect_changes(old: dict, new: dict) -> dict[str, bool]:
    """返回各维度是否有显著变化的字典。"""
    changes = {}

    # 1. 话题分布变化
    old_topics = {k: v["pct"] for k, v in old.get("topics", {}).get("distribution", {}).items()}
    new_topics = {k: v["pct"] for k, v in new.get("topics", {}).get("distribution", {}).items()}
    topic_drift = max(
        abs(new_topics.get(k, 0) - old_topics.get(k, 0))
        for k in set(old_topics) | set(new_topics)
    ) if old_topics or new_topics else 0
    changes["topics"] = topic_drift >= THRESHOLD["topic_pct"]

    # 2. 会话数增量
    new_sessions  = new.get("session_count", 0) - old.get("session_count", 0)
    changes["sessions"] = new_sessions >= THRESHOLD["session_count"]

    # 3. 平均消息长度变化
    old_len = old.get("language_style", {}).get("avg_message_length", 0)
    new_len = new.get("language_style", {}).get("avg_message_length", 0)
    changes["msg_length"] = abs(new_len - old_len) >= THRESHOLD["avg_msg_len"]

    # 4. 互动风格变化
    old_style = old.get("question_style", {}).get("style_distribution", {})
    new_style = new.get("question_style", {}).get("style_distribution", {})
    style_drift = max(
        abs(new_style.get(k, 0) - old_style.get(k, 0))
        for k in set(old_style) | set(new_style)
    ) if old_style or new_style else 0
    changes["style"] = style_drift >= THRESHOLD["style_pct"]

    # 5. 关键词更新（Top10 中的新词）
    old_kws = {k for k, _ in old.get("top_keywords", [])[:10]}
    new_kws = {k for k, _ in new.get("top_keywords", [])[:10]}
    new_entries = new_kws - old_kws
    changes["keywords"] = len(new_entries) >= THRESHOLD["keyword_new"]

    return changes, {
        "topic_drift": round(topic_drift, 1),
        "new_sessions": new_sessions,
        "msg_len_delta": round(new_len - old_len, 1),
        "style_drift": round(style_drift, 1),
        "new_keywords": list(new_entries),
    }


# ══════════════════════════════════════════════════════════════
# 局部文字生成：只重写有变化的段落（规则驱动，不调 LLM）
# ══════════════════════════════════════════════════════════════

def gen_obs1(new: dict) -> tuple[str, str]:
    """重写 Observation 1（交互结构）。"""
    style = new.get("question_style", {}).get("style_distribution", {})
    exec_pct = style.get("执行型", 0)
    emo_pct  = style.get("情感型", 0)
    ana_pct  = style.get("分析型", 0)
    dec_pct  = style.get("陈述型", 0)
    total_m  = new.get("total_messages", 0)

    dominant = max(style, key=style.get) if style else "执行型"
    label_map = {"执行型": "execution", "情感型": "emotional", "分析型": "analytical",
                 "陈述型": "declarative", "创意型": "creative"}
    dom_en = label_map.get(dominant, dominant)

    en = (
        f"Across {total_m} messages: execution-type {exec_pct}%, "
        f"declarative {dec_pct}%, analytical {ana_pct}%, emotional {emo_pct}%. "
        f"Dominant mode: <span class='ul-hw'>{dom_en}</span>. "
        f"{'The elevated emotional register ('+str(emo_pct)+'%) indicates AI is used as a thinking partner, not just a task engine.' if emo_pct > 15 else ''}"
    )
    zh = (
        f"在 {total_m} 条消息中：执行型 {exec_pct}%、"
        f"陈述型 {dec_pct}%、分析型 {ana_pct}%、情感型 {emo_pct}%。"
        f"主导模式：<span class='ul-hw'>{dominant}</span>。"
        f"{'情感型比例（'+str(emo_pct)+'%）偏高，AI 被用作思维伙伴而非纯粹任务引擎。' if emo_pct > 15 else ''}"
    )
    return en, zh


def gen_obs2(new: dict) -> tuple[str, str]:
    """重写 Observation 2（认知负载）。"""
    lang = new.get("language_style", {})
    avg_len  = lang.get("avg_message_length", 0)
    emoji    = lang.get("emoji_usage_pct", 0)
    total_m  = new.get("total_messages", 0)

    depth = "高语境密度" if avg_len > 800 else "中等语境密度" if avg_len > 400 else "简洁交互"
    depth_en = "context-dense" if avg_len > 800 else "moderate-context" if avg_len > 400 else "concise"

    en = (
        f"Average message length: <span class='ul-hw ul-red'>{avg_len:.0f} characters</span> "
        f"(emoji usage: {emoji}%, n={total_m}). "
        f"Profile: <span class='circled'>{depth_en}, selectively warm"
        f"<svg class='c-svg' viewBox='0 0 260 26'><ellipse cx='130' cy='13' rx='126' ry='12'/></svg></span>. "
        f"Subject pre-builds full problem context before querying — a structural habit, not case-by-case."
    )
    zh = (
        f"平均消息长度 <span class='ul-hw ul-red'>{avg_len:.0f} 字</span>"
        f"（emoji 使用率 {emoji}%，样本 {total_m} 条）。"
        f"特征：<span class='circled'>{depth}、选择性温度"
        f"<svg class='c-svg' viewBox='0 0 220 26'><ellipse cx='110' cy='13' rx='106' ry='12'/></svg></span>。"
        f"受试者在提问前系统性地预构建完整问题空间，是结构性习惯，非偶发行为。"
    )
    return en, zh


def gen_obs3(new: dict) -> tuple[str, str]:
    """重写 Observation 3（峰值决策窗口）。"""
    tp       = new.get("time_pattern", {})
    peak     = tp.get("peak_hours", "12-18")
    label    = tp.get("pattern_label", "白昼工作者")
    hour_dist = tp.get("hour_distribution", {})
    kws      = [k for k, _ in new.get("top_keywords", [])[:5]]

    # 找最高峰小时
    peak_hour = max(hour_dist, key=hour_dist.get, default="17") if hour_dist else "17"
    peak_cnt  = hour_dist.get(peak_hour, 0)

    label_en_map = {"白昼工作者": "Diurnal Operator", "深夜工作者": "Nocturnal Thinker",
                    "全时工作者": "Always-On Operator"}
    label_en = label_en_map.get(label, label)
    kw_str   = " · ".join(kws[:4])

    en = (
        f"Activity concentrates in <span class='circled'><strong>{label_en}</strong>"
        f"<svg class='c-svg' viewBox='0 0 200 26'><ellipse cx='100' cy='13' rx='96' ry='12'/></svg></span> "
        f"pattern, peaking {peak}h (GMT+8). "
        f"The {peak_hour}:00 slot carries the highest density ({peak_cnt} messages). "
        f"Peak-hour queries cluster around <span class='ul-hw'>{kw_str}</span> — architectural thinking, not maintenance."
    )
    zh = (
        f"活跃度集中于<span class='circled'><strong>{label}</strong>"
        f"<svg class='c-svg' viewBox='0 0 130 26'><ellipse cx='65' cy='13' rx='61' ry='12'/></svg></span>"
        f"模式，峰值 {peak} 时（GMT+8）。"
        f"{peak_hour}:00 时段消息密度最高（{peak_cnt} 条）。"
        f"峰值时段查询集中在 <span class='ul-hw'>{kw_str}</span>——架构性思考，非维护性任务。"
    )
    return en, zh


def gen_sec2_intro(new: dict) -> tuple[str, str]:
    """重写核心优势介绍段。"""
    sessions = new.get("session_count", 0)
    total_m  = new.get("total_messages", 0)
    date_r   = new.get("date_range", "")
    en = (
        f"The following capability assessments are derived from {total_m} behavioral observations "
        f"across {sessions} sessions ({date_r}). "
        f"Scoring methodology: keyword density, problem decomposition depth, "
        f"solution architecture complexity, and cross-domain synthesis frequency. "
        f"All scores are evidence-based — not self-reported, not inferred from credentials."
    )
    zh = (
        f"以下能力评估来源于 {sessions} 次会话、{total_m} 条消息的行为观察（{date_r}）。"
        f"评分方法：关键词密度、问题分解深度、解决方案架构复杂度、跨域综合频率。"
        f"所有评分有行为证据支撑，非自评，非学历推断。"
    )
    return en, zh


# ══════════════════════════════════════════════════════════════
# 生成更新摘要（晚间通知用）
# ══════════════════════════════════════════════════════════════

def gen_summary(new: dict, old: dict, changes: dict, metrics: dict) -> str:
    """生成晚间通知用的增量摘要。"""
    lines = []
    ns = metrics["new_sessions"]
    if ns > 0:
        lines.append(f"📊 今日新增 {ns} 次会话，累计 {new.get('session_count', 0)} 次")

    if changes.get("topics"):
        top = max(new.get("topics", {}).get("distribution", {}).items(),
                  key=lambda x: x[1]["pct"], default=("", {}))
        lines.append(f"🔍 话题分布小幅移动（最大偏移 {metrics['topic_drift']}%），{top[0]} 仍主导（{top[1].get('pct', 0):.1f}%）")

    if changes.get("keywords"):
        lines.append(f"🔑 关键词更新：新上榜 → {' · '.join(metrics['new_keywords'][:4])}")

    if changes.get("style"):
        style = new.get("question_style", {}).get("style_distribution", {})
        dom   = max(style, key=style.get) if style else ""
        lines.append(f"💬 交互风格微变（{dom} {style.get(dom, 0)}%）")

    if not lines:
        lines.append("📈 档案在安静积累中，无显著变化")

    lines.append(f"🕐 数据覆盖：{new.get('date_range', '')}")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats-new",    required=True)
    ap.add_argument("--stats-old",    required=True)
    ap.add_argument("--content-prev", required=False, default=None,
                    help="上次生成的 content JSON，用于保留未变化的段落")
    ap.add_argument("--output",       default="/tmp/persona_content_delta.json")
    args = ap.parse_args()

    new  = json.loads(Path(args.stats_new).read_text())
    old  = json.loads(Path(args.stats_old).read_text()) if Path(args.stats_old).exists() else {}
    prev = json.loads(Path(args.content_prev).read_text()) if args.content_prev and Path(args.content_prev).exists() else {}

    changes, metrics = detect_changes(old, new)
    print(f"  [delta] 变化检测: {changes}", file=sys.stderr)
    print(f"  [delta] 指标: {metrics}",     file=sys.stderr)

    delta: dict = {}
    changed_keys: list[str] = []

    # ── 按变化选择性重写段落 ─────────────────────────────────────────────
    if changes.get("sessions") or changes.get("style"):
        en, zh = gen_obs1(new)
        delta["obs1_en"], delta["obs1_zh"] = en, zh
        changed_keys += ["obs1_en", "obs1_zh"]

    if changes.get("msg_length"):
        en, zh = gen_obs2(new)
        delta["obs2_en"], delta["obs2_zh"] = en, zh
        changed_keys += ["obs2_en", "obs2_zh"]

    if changes.get("sessions") or changes.get("keywords"):
        en, zh = gen_obs3(new)
        delta["obs3_en"], delta["obs3_zh"] = en, zh
        changed_keys += ["obs3_en", "obs3_zh"]

    # sec2_intro 只要有新会话就更新（刷新数字）
    if changes.get("sessions"):
        en, zh = gen_sec2_intro(new)
        delta["sec2_intro_en"], delta["sec2_intro_zh"] = en, zh
        changed_keys += ["sec2_intro_en", "sec2_intro_zh"]

    # ── 元信息 ────────────────────────────────────────────────────────────
    delta["_changed_keys"] = changed_keys
    delta["_summary"]      = gen_summary(new, old, changes, metrics)
    delta["_timestamp"]    = datetime.now().isoformat()
    delta["_new_sessions"] = metrics["new_sessions"]

    Path(args.output).write_text(json.dumps(delta, ensure_ascii=False, indent=2))
    print(f"  [delta] 写入 {len(changed_keys)} 个变化段落 → {args.output}", file=sys.stderr)
    print(f"  [delta] 更新摘要:\n{delta['_summary']}", file=sys.stderr)


if __name__ == "__main__":
    main()
