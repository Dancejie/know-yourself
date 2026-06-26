#!/usr/bin/env python3
"""
gen_daily_quest.py — 每日任务 + 周常任务生成器
早上 Cron 调用，基于昨日交互生成今日专属任务，发 Hi 消息推送
"""

import json
import os
import sys
import datetime
import subprocess

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
STATS_FILE = os.path.join(WORKSPACE, "memory/character_stats.json")
QUEST_FILE = os.path.join(WORKSPACE, "memory/daily_quest.json")
SESSIONS_DIR = os.path.expanduser("~/.openclaw/agents/main/sessions")

TODAY = datetime.date.today().isoformat()
NOW = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=8)))
WEEKDAY = NOW.weekday()  # 0=Monday

# ── 成长目标体系：从 character_stats.json 动态读取，不再硬编码 ──
# GROWTH_GOALS 在 load_growth_goals() 中从文件读取
# 格式：[{ id, name, desc, weekly_target, keywords, exp, rarity, source }]

def load_growth_goals(stats: dict) -> list:
    """
    从 character_stats.json 的 growth_goals 字段读取周常目标。
    若不存在则返回通用兜底目标（首次建档前的过渡期使用）。
    兜底目标不包含任何用户特定内容，只做占位。
    """
    goals = stats.get("growth_goals", [])
    if goals:
        return goals
    # 兜底：通用目标（适用于任何人）
    return [
        {
            "id": "deep_focus",
            "name": "深度专注修炼",
            "desc": "完成一件需要集中注意力超过1小时的事",
            "weekly_target": "本周完成1次有实质输出的深度专注工作",
            "keywords": ["完成", "专注", "输出", "记录", "写", "做到", "总结"],
            "exp": 1000,
            "rarity": "epic",
            "source": "通用兜底（character_stats 中尚无 growth_goals 字段）"
        },
        {
            "id": "reflection_log",
            "name": "反思沉淀",
            "desc": "写下本周最有价值的一条洞察或教训",
            "weekly_target": "本周写下1条有深度的洞察或教训",
            "keywords": ["洞察", "教训", "发现", "总结", "反思", "学到", "复盘"],
            "exp": 1000,
            "rarity": "epic",
            "source": "通用兜底（character_stats 中尚无 growth_goals 字段）"
        }
    ]

def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_yesterday_sessions():
    """读取昨日会话摘要（最近的几个会话文件）"""
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
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
                            if yesterday_str in ts and role == "user" and content:
                                text = content if isinstance(content, str) else str(content)
                                snippets.append(text[:200])
                                if len(snippets) >= 15:
                                    break
                        except:
                            continue
            except:
                continue
    except:
        pass
    return snippets

def generate_daily_quest(snippets, stats):
    """根据昨日交互生成今日每日任务（因人而异）"""
    level = stats.get("profile", {}).get("level", 1)
    archetype = stats.get("profile", {}).get("archetype", "")
    
    # 分析昨日主题
    text_all = " ".join(snippets).lower()
    
    # 任务候选池（根据实际交互内容选择最匹配的）
    candidates = []
    
    if any(k in text_all for k in ["简历", "jd", "岗位", "求职", "面试"]):
        candidates.append({
            "title": "战略定位校准",
            "desc": "今天和简历/求职相关的工作已展开。完成目标：在 Redoc 写下你对目标岗位的3条核心判断（为什么适合你，你能带来什么独特价值）。",
            "how": "在 Redoc 新建或编辑一篇文档，写下3条核心判断，发给 Alice 确认即算完成。",
            "benefit": "求职不是展示「我做了什么」，而是传递「我能给你带来什么」。把这三条判断写清楚，面试时你会比别人多一个维度的准备。",
            "completion_keywords": ["redoc", "文档", "写", "核心判断", "价值", "判断"],
            "exp": 200,
            "title_name": "战略自知者",
            "title_rarity": "rare",
            "title_desc": "清楚自己是谁，要去哪里，凭什么去"
        })

    if any(k in text_all for k in ["html", "demo", "部署", "上线", "发布"]):
        candidates.append({
            "title": "产品化思维实践",
            "desc": "今天完成了技术交付。完成目标：为今天交付的产品写一句话定位——用户是谁、解决什么问题、为什么选它。",
            "how": "把那句话发给 Alice，或者发到 Hi/朋友圈，让它接受真实反馈。",
            "benefit": "技术交付完成不等于产品完成。能用一句话说清楚「这是什么、给谁用、为什么好」，才是产品人的核心能力。这个训练越早开始越值钱。",
            "completion_keywords": ["朋友圈", "发出去", "分享", "定位", "一句话", "是什么"],
            "exp": 200,
            "title_name": "产品叙事者",
            "title_rarity": "rare",
            "title_desc": "让技术开口说话的人"
        })

    if any(k in text_all for k in ["agent", "skill", "cron", "prompt", "pe", "tagging"]):
        candidates.append({
            "title": "系统深化日",
            "desc": "今天在 Agent/PE 方向持续推进。完成目标：写下今天做的某个系统中，1条最反直觉的设计决策——为什么这样而不是那样。",
            "how": "发给 Alice 或写进 Redoc 即可，一句话也算。Alice 会在晚间识别到「决策/设计/为什么」等关键词后判定完成。",
            "benefit": "记录反直觉决策是构建工程判断力最快的方式。三个月后你回看这些记录，会发现它们比代码更有价值。",
            "completion_keywords": ["决策", "设计", "反直觉", "为什么", "记录", "redoc"],
            "exp": 200,
            "title_name": "决策记录者",
            "title_rarity": "rare",
            "title_desc": "把每一个选择都变成可传承的智慧"
        })

    if any(k in text_all for k in ["投资", "止损", "仓位", "银锡", "回撤", "白银"]):
        candidates.append({
            "title": "纪律考验日",
            "desc": "今天触及了投资相关内容。完成目标：用一句话写下你当前的持仓判断和止损线。",
            "how": "发给 Alice 一句话：「当前持仓：XX，止损线：XX」即算完成。不需要长篇分析，重点是把判断显式化。",
            "benefit": "投资亏钱往往不是因为判断错，而是因为没有事先写下来——执行时就模糊了。把止损线写成文字，是对自己的一种契约。",
            "completion_keywords": ["止损", "持仓", "记录", "判断", "投资"],
            "exp": 200,
            "title_name": "纪律执行者",
            "title_rarity": "rare",
            "title_desc": "在每一个当下都能做出有原则的决定"
        })

    # 通用兜底任务
    fallback_tasks = [
        {
            "title": "深度输出日",
            "desc": "今天完成一件「需要集中注意力超过30分钟」的事，并用3句话记录：做了什么、遇到什么阻力、最大的收获是什么。",
            "how": "把那3句话发给 Alice，或写进任意文档，Alice 晚间识别「记录/总结/收获」等词后判定完成。",
            "benefit": "深度工作是最稀缺的能力，而反思是让深度工作产生复利的乘数。养成「做完即记录」的习惯，你的成长速度会系统性地快于不记录的人。",
            "completion_keywords": ["记录", "总结", "完成", "收获", "redoc"],
            "exp": 200,
            "title_name": "专注炼金师",
            "title_rarity": "rare",
            "title_desc": "深度工作是最稀缺的能力"
        },
        {
            "title": "洞察提炼日",
            "desc": f"Lv.{level} 的{archetype.split('·')[-1].strip()}，今天提炼一条「让你重新理解某件事」的洞察，写进 Redoc 或备忘录。",
            "how": "一句话洞察发给 Alice 即算完成，格式随意，比如「我发现XX其实是YY，因为ZZ」。",
            "benefit": "洞察是思维升级的最小单位。今天的一句话洞察，可能是三年后某个关键决策的根基。",
            "completion_keywords": ["洞察", "发现", "理解", "redoc", "记录", "其实"],
            "exp": 200,
            "title_name": "洞察提炼者",
            "title_rarity": "rare",
            "title_desc": "从噪音中萃取信号的人"
        }
    ]
    
    if candidates:
        # 选第一个最匹配的
        task = candidates[0]
    else:
        # 按日期轮换兜底任务
        task = fallback_tasks[datetime.date.today().toordinal() % len(fallback_tasks)]
    
    return task

def get_or_init_weekly_quests(quest_data, stats):
    """
    获取或初始化本周周常任务。
    目标从 character_stats.json growth_goals 动态读取，不再硬编码。
    每周一自动刷新，已完成的任务下周重置。
    """
    monday = (datetime.date.today() - datetime.timedelta(days=WEEKDAY)).isoformat()
    weekly = quest_data.get("weekly", {})

    if weekly.get("week_start") != monday:
        growth_goals = load_growth_goals(stats)
        weekly = {
            "week_start": monday,
            "quests": []
        }
        for goal in growth_goals:
            weekly["quests"].append({
                "id": goal["id"],
                "name": goal["name"],
                "desc": goal["weekly_target"],
                "exp": goal["exp"],
                "title_rarity": goal["rarity"],
                "title_name": f"{goal['name']}·周常达成",
                "title_desc": f"本周完成了「{goal['name']}」目标",
                "keywords": goal["keywords"],
                "status": "in_progress",
                "progress_log": [],
                "completed_date": None
            })
        print(f"[weekly] 本周周常已刷新，共 {len(weekly['quests'])} 个目标（来源：character_stats.growth_goals）")

    return weekly

RARITY_LABELS = {
    "hidden": "隐藏", "legendary": "传说",
    "epic": "史诗", "rare": "稀有", "common": "普通"
}

WEEKLY_GOAL_BENEFITS = {
    "investment_discipline": {
        "how": "今天触碰投资相关思考、写下持仓判断或执行一次止损/建仓操作，Alice 会在晚间自动识别并标记进度。",
        "benefit": "投资纪律是复利积累的基石。每次有意识的记录和执行，都在强化你的决策肌肉——这比任何单次收益都更值钱。"
    },
    "writing_output": {
        "how": "今天完成任何有实质内容的写作——Redoc 文档、复盘、简历优化、分析备忘——Alice 晚间自动识别。",
        "benefit": "写作是思维的外化。把你脑子里的框架落成文字，不仅留存了智识资产，也在倒逼你澄清模糊的认知。"
    }
}

def format_morning_message(daily_task, weekly, stats):
    """格式化早安推送消息"""
    profile = stats.get("profile", {})
    level = profile.get("level", 1)
    exp = profile.get("exp", 0)
    exp_to_next = profile.get("exp_to_next", 500)
    
    monday = weekly.get("week_start", "")
    sunday = (datetime.date.fromisoformat(monday) + datetime.timedelta(days=6)).isoformat() if monday else ""
    
    rarity_label = RARITY_LABELS.get(daily_task.get("title_rarity", "rare"), "稀有")
    
    lines = []
    lines.append(f"⚔️ 德尔斐计划 · 每日简报")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🗓 {TODAY}  |  Lv.{level}  |  EXP {exp}/{exp_to_next}")
    lines.append(f"")
    
    # 每日任务
    lines.append(f"【📋 今日任务】{daily_task['title']}")
    lines.append(f"")
    lines.append(f"📌 任务内容")
    lines.append(f"{daily_task['desc']}")
    lines.append(f"")
    lines.append(f"✅ 完成方式")
    lines.append(f"{daily_task.get('how', '在今天的交互或行动中自然触发，Alice 晚间自动判定。')}")
    lines.append(f"")
    lines.append(f"💡 为什么值得做")
    lines.append(f"{daily_task.get('benefit', '每一次有意识的行动都在积累你的成长势能。')}")
    lines.append(f"")
    lines.append(f"🎁 奖励：+{daily_task['exp']} EXP  |  解锁称号「{daily_task['title_name']}」({rarity_label})")
    lines.append(f"")
    
    # 周常任务
    lines.append(f"【🏆 周常任务】{monday} ~ {sunday}")
    lines.append(f"")
    
    for i, wq in enumerate(weekly.get("quests", []), 1):
        status_icon = "✅" if wq["status"] == "completed" else "⬜"
        progress_count = len(wq.get("progress_log", []))
        progress_str = f"（进度：{progress_count}/2天）" if wq["status"] != "completed" else ""
        
        lines.append(f"{status_icon} W{i}. {wq['name']}  +{wq['exp']} EXP {progress_str}")
        lines.append(f"   📌 目标：{wq['desc']}")
        
        # 完成方式和收益
        goal_info = WEEKLY_GOAL_BENEFITS.get(wq.get("id", ""), {})
        if goal_info:
            lines.append(f"   ✅ 怎么完成：{goal_info['how']}")
            lines.append(f"   💡 为什么值得：{goal_info['benefit']}")
        
        if wq["status"] == "completed":
            lines.append(f"   🎉 已完成（{wq.get('completed_date', '')}）· 称号「{wq.get('title_name','')}」已解锁")
        elif wq.get("progress_log"):
            lines.append(f"   📈 最新进展：{wq['progress_log'][-1]}")
        
        lines.append(f"")
    
    lines.append(f"━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"晚间 19:30 自动结算 · 完成即解锁称号")
    
    return "\n".join(lines)

def send_hi_message(text):
    """通过 OpenClaw message 工具发 Hi 消息（写入临时文件让主 agent 发送）"""
    msg_file = "/tmp/daily_quest_morning_msg.txt"
    with open(msg_file, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[morning-msg] 消息已写入 {msg_file}")
    print(text)

def main():
    # 加载现有数据
    stats = load_json(STATS_FILE)
    quest_data = load_json(QUEST_FILE, {
        "version": "1.0",
        "daily": {},
        "weekly": {}
    })
    
    # 检查今天是否已生成
    if quest_data.get("daily", {}).get("date") == TODAY:
        print(f"[skip] 今日任务已生成：{quest_data['daily'].get('title', '')}")
        # 仍然发送进度提醒
    else:
        # 读昨日会话
        snippets = get_yesterday_sessions()
        print(f"[info] 读取到 {len(snippets)} 条昨日交互片段")
        
        # 生成今日任务
        daily_task = generate_daily_quest(snippets, stats)
        print(f"[daily] 生成任务：{daily_task['title']}")
        
        # 保存今日任务
        quest_data["daily"] = {
            "date": TODAY,
            "status": "pending",  # pending / completed
            **daily_task
        }
    
    # 周常任务（从 character_stats.growth_goals 动态读取）
    weekly = get_or_init_weekly_quests(quest_data, stats)
    quest_data["weekly"] = weekly
    
    # 保存
    save_json(QUEST_FILE, quest_data)
    
    # 格式化消息
    msg = format_morning_message(quest_data["daily"], weekly, stats)
    send_hi_message(msg)
    
    print("[done] daily_quest.json 已更新")

if __name__ == "__main__":
    main()
