#!/usr/bin/env python3
"""
settle_daily_quest.py — 晚间任务结算器
晚间 Cron 调用，判定今日/周常任务是否完成，注入经验事件，更新称号
"""

import json
import os
import datetime
import re

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
STATS_FILE = os.path.join(WORKSPACE, "memory/character_stats.json")
QUEST_FILE = os.path.join(WORKSPACE, "memory/daily_quest.json")
SESSIONS_DIR = os.path.expanduser("~/.openclaw/agents/main/sessions")

TODAY = datetime.date.today().isoformat()
NOW_STR = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=8))).isoformat()

RARITY_COLORS = {
    "hidden":    "#c0392b",
    "legendary": "#f39c12",
    "epic":      "#9b59b6",
    "rare":      "#4a90d9",
    "common":    "#7f8c8d"
}

RARITY_LABELS = {
    "hidden": "隐藏", "legendary": "传说",
    "epic": "史诗", "rare": "稀有", "common": "普通"
}

def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_today_sessions():
    """读取今日所有用户消息"""
    today_str = datetime.date.today().isoformat()
    snippets = []
    try:
        all_files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith(".jsonl")]
        files = sorted(all_files, reverse=True)[:10]
        for fname in files:
            fpath = os.path.join(SESSIONS_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            obj = json.loads(line.strip())
                            ts = str(obj.get("timestamp", ""))
                            msg = obj.get("message", obj)
                            role = msg.get("role", "")
                            content = msg.get("content", "")
                            if today_str in ts and role == "user" and content:
                                text = content if isinstance(content, str) else str(content)
                                snippets.append(text[:300])
                        except:
                            continue
            except:
                continue
    except:
        pass
    return snippets

def check_completion(snippets, keywords):
    """简单关键词匹配判定任务完成"""
    text_all = " ".join(snippets).lower()
    matched = [k for k in keywords if k.lower() in text_all]
    return len(matched) >= max(1, len(keywords) // 3), matched

def add_title(stats, title_name, rarity, desc, source="daily_quest"):
    """向 stats 添加称号（去重）"""
    titles = stats.get("titles", [])
    existing_names = [t.get("name") for t in titles]
    if title_name not in existing_names:
        color = RARITY_COLORS.get(rarity, "#7f8c8d")
        titles.append({
            "name": title_name,
            "rarity": rarity,
            "color": color,
            "desc": desc,
            "unlocked_at": TODAY,
            "source": source
        })
        stats["titles"] = titles
        return True
    return False

def add_exp_event(stats, desc, exp, attr_bonus=None):
    """向今日经验记录中添加事件"""
    exp_log = stats.get("exp_log", [])
    
    # 找今日记录
    today_entry = None
    for entry in exp_log:
        if entry.get("date") == TODAY:
            today_entry = entry
            break
    
    if today_entry is None:
        today_entry = {
            "date": TODAY,
            "events": [],
            "total_exp_gained": 0
        }
        exp_log.append(today_entry)
    
    today_entry["events"].append({
        "desc": desc,
        "exp": exp,
        "attr_bonus": attr_bonus or {}
    })
    today_entry["total_exp_gained"] = today_entry.get("total_exp_gained", 0) + exp
    
    # 更新总经验和等级
    profile = stats.get("profile", {})
    current_exp = profile.get("exp", 0) + exp
    total_exp = profile.get("total_exp", 0) + exp
    exp_to_next = profile.get("exp_to_next", 500)
    level = profile.get("level", 1)
    
    leveled_up = False
    while current_exp >= exp_to_next:
        current_exp -= exp_to_next
        level += 1
        exp_to_next = int(exp_to_next * 1.3)
        leveled_up = True
    
    profile["exp"] = current_exp
    profile["total_exp"] = total_exp
    profile["exp_to_next"] = exp_to_next
    profile["level"] = level
    stats["profile"] = profile
    stats["exp_log"] = exp_log
    
    # 属性加成
    if attr_bonus:
        attrs = stats.get("attributes", {})
        for k, v in attr_bonus.items():
            if k in attrs:
                attrs[k]["value"] = min(100, attrs[k].get("value", 0) + v)
        stats["attributes"] = attrs
    
    return leveled_up

def format_settlement_message(results, stats):
    """格式化晚间结算消息"""
    profile = stats.get("profile", {})
    level = profile.get("level", 1)
    exp = profile.get("exp", 0)
    exp_to_next = profile.get("exp_to_next", 500)
    
    lines = []
    lines.append(f"🌙 德尔斐计划 · 晚间结算")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📅 {TODAY}  |  Lv.{level}  |  EXP {exp}/{exp_to_next}")
    lines.append("")
    
    total_exp = sum(r.get("exp", 0) for r in results)
    lines.append(f"【今日获得经验】+{total_exp} EXP")
    for r in results:
        icon = "✅" if r.get("completed") else "📌"
        lines.append(f"  {icon} {r.get('desc', '')}  +{r.get('exp', 0)}")
    
    new_titles = [r for r in results if r.get("title_unlocked")]
    if new_titles:
        lines.append("")
        lines.append("【🏆 称号解锁】")
        for r in new_titles:
            rarity_label = RARITY_LABELS.get(r.get("rarity", "rare"), "稀有")
            lines.append(f"  ◆ 「{r['title_name']}」({rarity_label})")
            lines.append(f"    {r.get('title_desc', '')}")
    
    if any(r.get("leveled_up") for r in results):
        lines.append("")
        lines.append(f"🎉 ！升级至 Lv.{level}！")
    
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    
    return "\n".join(lines)

def main():
    stats = load_json(STATS_FILE)
    quest_data = load_json(QUEST_FILE, {})
    
    if not quest_data:
        print("[skip] 无任务数据，跳过结算")
        return
    
    snippets = get_today_sessions()
    print(f"[info] 读取到 {len(snippets)} 条今日交互")
    
    results = []
    
    # ── 1. 日常小经验（自动发放）──
    if snippets:
        base_exp = min(25 * len(snippets) // 3, 75)  # 最多 75 小包
        leveled = add_exp_event(stats, f"今日活跃交互（{len(snippets)}条）", base_exp, {"execution": 1})
        results.append({
            "desc": f"日常活跃经验",
            "exp": base_exp,
            "completed": True,
            "leveled_up": leveled
        })
    
    # ── 2. 每日任务判定 ──
    daily = quest_data.get("daily", {})
    if daily.get("date") == TODAY and daily.get("status") == "pending":
        keywords = daily.get("completion_keywords", [])
        completed, matched = check_completion(snippets, keywords)
        
        if completed:
            print(f"[daily] 任务完成！匹配关键词：{matched}")
            daily["status"] = "completed"
            daily["completed_at"] = NOW_STR
            
            # 发放经验
            leveled = add_exp_event(
                stats,
                f"完成每日任务「{daily['title']}」",
                daily.get("exp", 200),
                {"framework": 1, "execution": 2}
            )
            
            # 解锁称号
            title_added = add_title(
                stats,
                daily.get("title_name", "任务达成者"),
                daily.get("title_rarity", "rare"),
                daily.get("title_desc", "完成了今日专属任务"),
                source="daily_quest"
            )
            
            results.append({
                "desc": f"每日任务「{daily['title']}」",
                "exp": daily.get("exp", 200),
                "completed": True,
                "title_unlocked": title_added,
                "title_name": daily.get("title_name"),
                "title_desc": daily.get("title_desc"),
                "rarity": daily.get("title_rarity", "rare"),
                "leveled_up": leveled
            })
        else:
            print(f"[daily] 任务未完成（关键词未命中）")
            results.append({
                "desc": f"每日任务「{daily['title']}」（未完成）",
                "exp": 0,
                "completed": False
            })
        
        quest_data["daily"] = daily
    
    # ── 3. 周常任务进度检测 ──
    weekly = quest_data.get("weekly", {})
    for wq in weekly.get("quests", []):
        if wq.get("status") == "completed":
            continue
        
        keywords = wq.get("keywords", [])
        has_progress, matched = check_completion(snippets, keywords)
        
        if has_progress:
            # 记录进展
            progress_note = f"{TODAY}: 涉及关键词 {matched[:3]}"
            wq.setdefault("progress_log", []).append(progress_note)
            print(f"[weekly] {wq['name']} 有进展：{matched[:3]}")
            
            # 判定是否完成（需要 progress_log >= 2 天，或关键词命中较多）
            if len(wq.get("progress_log", [])) >= 2 or len(matched) >= len(keywords) // 2:
                wq["status"] = "completed"
                wq["completed_date"] = TODAY
                print(f"[weekly] 周常任务完成：{wq['name']}")
                
                leveled = add_exp_event(
                    stats,
                    f"完成周常任务「{wq['name']}」",
                    wq.get("exp", 1000),
                    {"framework": 2, "execution": 3, "ai_depth": 2}
                )
                
                title_added = add_title(
                    stats,
                    wq.get("title_name", "周常达成者"),
                    wq.get("title_rarity", "epic"),
                    wq.get("title_desc", "完成了本周的成长目标"),
                    source="weekly_quest"
                )
                
                results.append({
                    "desc": f"周常任务「{wq['name']}」",
                    "exp": wq.get("exp", 1000),
                    "completed": True,
                    "title_unlocked": title_added,
                    "title_name": wq.get("title_name"),
                    "title_desc": wq.get("title_desc"),
                    "rarity": wq.get("title_rarity", "epic"),
                    "leveled_up": leveled
                })
    
    quest_data["weekly"] = weekly
    
    # ── 保存 ──
    stats["_updated"] = NOW_STR
    save_json(STATS_FILE, stats)
    save_json(QUEST_FILE, quest_data)
    
    # ── 输出结算消息 ──
    msg = format_settlement_message(results, stats)
    msg_file = "/tmp/daily_quest_settle_msg.txt"
    with open(msg_file, "w", encoding="utf-8") as f:
        f.write(msg)
    print(msg)
    print(f"[done] 结算完成，消息写入 {msg_file}")

if __name__ == "__main__":
    main()
