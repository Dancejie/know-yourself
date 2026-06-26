#!/usr/bin/env python3
"""
gen_battle_report.py — 德尔斐战斗系统
支持：
  - PvE：玩家 vs 小粉猪
  - PvP：今日 vs 昨日自我（时间线决斗）
生成文字战报 + PIL 战场图
"""

import json, os, sys, datetime, random, math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))
STATS_FILE = WORKSPACE / "memory/character_stats.json"
QUEST_FILE = WORKSPACE / "memory/daily_quest.json"
SESSIONS_DIR = Path(os.path.expanduser("~/.openclaw/agents/main/sessions"))
OUT_DIR = WORKSPACE / "public"
OUT_DIR.mkdir(exist_ok=True)

TODAY = datetime.date.today().isoformat()
YESTERDAY = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

# ── 颜色主题 ──
DARK_BG    = (15, 15, 25)
PANEL_BG   = (25, 25, 40)
GOLD       = (212, 175, 55)
RED        = (180, 40, 40)
BLUE       = (40, 100, 180)
GREEN      = (40, 160, 80)
PINK       = (255, 150, 180)
WHITE      = (240, 240, 240)
GRAY       = (120, 120, 140)
PURPLE     = (140, 60, 200)

def load_json(path, default=None):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return default or {}

def get_sessions_text(date_str):
    """读取指定日期的所有用户消息"""
    snippets = []
    try:
        files = sorted([f for f in SESSIONS_DIR.iterdir() if f.suffix == ".jsonl"], reverse=True)[:10]
        for fpath in files:
            for line in fpath.read_text(encoding="utf-8", errors="ignore").splitlines():
                try:
                    obj = json.loads(line)
                    ts = str(obj.get("timestamp", ""))
                    msg = obj.get("message", obj)
                    if date_str in ts and msg.get("role") == "user":
                        content = msg.get("content", "")
                        if content:
                            snippets.append(str(content)[:200])
                except:
                    continue
    except:
        pass
    return snippets

def calc_battle_power(stats, snippets, date_str):
    """计算今日战力（今日行动70% + 历史基础30%）"""
    text = " ".join(snippets).lower()
    
    # ── 今日行动五维度（0-100各维度）──
    creativity = 0   # 创造性深度
    cognition  = 0   # 认知突破
    execution  = 0   # 执行密度
    depth      = 0   # 交互深度
    growth     = 0   # 成长显著度

    # 创造性：有新系统/新设计/新框架
    creative_kw = ["设计", "新增", "新功能", "创新", "想法", "系统", "架构", "方案", "战斗", "pvp", "pve"]
    creativity = min(100, sum(10 for k in creative_kw if k in text))

    # 认知突破：修正盲区/重新理解
    cognition_kw = ["发现", "原来", "没想到", "洞察", "理解了", "盲区", "反直觉", "重新", "明白了"]
    cognition = min(100, sum(12 for k in cognition_kw if k in text))

    # 执行密度：具体产出
    exec_kw = ["完成", "生成", "部署", "发布", "写了", "跑了", "测试", "发送", "提交", "更新"]
    execution = min(100, sum(8 for k in exec_kw if k in text))

    # 交互深度：复杂问题/追问
    depth_kw = ["为什么", "怎么", "如何", "原因", "机制", "逻辑", "底层", "本质", "究竟"]
    depth = min(100, sum(10 for k in depth_kw if k in text))
    depth = max(depth, min(60, len(snippets) * 5))  # 消息数量兜底

    # 成长显著度
    exp_log = stats.get("exp_log", [])
    today_log = next((e for e in exp_log if e.get("date") == date_str), None)
    today_exp = today_log.get("total_exp_gained", 0) if today_log else 0
    growth = min(100, today_exp * 2)

    # 今日行动分
    action_score = (creativity * 0.25 + cognition * 0.20 + execution * 0.20 + depth * 0.15 + growth * 0.20)

    # 历史基础分
    level = stats.get("profile", {}).get("level", 1)
    attrs = stats.get("attributes", {})
    avg_attr = sum(a.get("value", 50) for a in attrs.values()) / max(len(attrs), 1)
    base_score = min(100, level * 5 + avg_attr * 0.3)

    total = action_score * 0.7 + base_score * 0.3
    
    return {
        "total": round(total),
        "creativity": round(creativity),
        "cognition": round(cognition),
        "execution_d": round(execution),
        "depth": round(depth),
        "growth": round(growth),
        "action_score": round(action_score),
        "base_score": round(base_score),
        "today_exp": today_exp,
    }

def gen_skills(stats, snippets):
    """根据职业+今日交互生成个性化技能"""
    text = " ".join(snippets).lower()
    titles = [t.get("name", "") for t in stats.get("titles", [])]
    cls = stats.get("profile", {}).get("class", "Agent 策略工程师")

    skills = []

    # 物理系：执行/交付型
    if any(k in text for k in ["cron", "脚本", "部署", "测试", "发布", "gen_"]):
        skills.append({
            "name": "⚙️ 自动化斩",
            "type": "物理",
            "power": random.randint(65, 85),
            "desc": "今日完成了自动化系统部署，对「低效手工」造成碾压",
            "effect": "无视防御"
        })
    if any(k in text for k in ["简历", "文档", "redoc", "写", "分析"]):
        skills.append({
            "name": "📄 叙事重构击",
            "type": "物理",
            "power": random.randint(60, 80),
            "desc": "今日完成高质量文字输出，产生「清晰度冲击」",
            "effect": "降低对手混乱抗性"
        })

    # 魔法系：思维/创意型
    if any(k in text for k in ["设计", "想法", "系统", "机制", "战斗", "pvp", "pve"]):
        skills.append({
            "name": "🔮 体系降维术",
            "type": "魔法",
            "power": random.randint(70, 90),
            "desc": "将复杂问题拆解为可执行框架，造成「结构性震慑」",
            "effect": "对手下回合行动效率 -20%"
        })
    if any(k in text for k in ["pe", "prompt", "打标", "tagging", "agent"]):
        skills.append({
            "name": "✨ PE 框架咒",
            "type": "魔法",
            "power": random.randint(65, 85),
            "desc": "今日触及 Prompt 工程体系，产生「规则锁定」效果",
            "effect": "对手随机爆发概率 -30%"
        })

    # 称号加成技能
    if "精密体系建筑师" in titles:
        skills.append({
            "name": "🏛️ 架构降维打击",
            "type": "魔法·史诗",
            "power": random.randint(80, 100),
            "desc": "「精密体系建筑师」专属技能：用系统架构能力压制对手",
            "effect": "无视对手50%魔法防御"
        })
    if "规则锻造者" in titles:
        skills.append({
            "name": "⚖️ 边界锁定",
            "type": "物理·史诗",
            "power": random.randint(75, 95),
            "desc": "「规则锻造者」专属：从 v3 到 v5.8.3 锻造的规则体系化为盾矛",
            "effect": "减少对手随机暴击概率 40%"
        })

    # 兜底技能
    if not skills:
        skills.append({
            "name": "🧠 理性分析波",
            "type": "魔法",
            "power": random.randint(55, 75),
            "desc": "Logos 75 的理性力量注入攻击",
            "effect": "稳定伤害，无随机波动"
        })

    return skills[:3]  # 最多3个技能

def piglet_today_power(player_power, quest_data):
    """小粉猪今日战力 = 玩家懈怠程度"""
    daily = quest_data.get("daily", {})
    weekly = quest_data.get("weekly", {})
    
    incomplete = 0
    if daily.get("status") == "pending":
        incomplete += 1
    incomplete += sum(1 for q in weekly.get("quests", []) if q.get("status") != "completed")
    
    base = 200 + incomplete * 50
    variation = random.randint(-30, 30)
    hp = max(80, base + variation)
    
    # 越努力今天，小粉猪越弱
    if player_power["today_exp"] > 100:
        hp = int(hp * 0.7)
    elif player_power["today_exp"] > 50:
        hp = int(hp * 0.85)
    
    return hp

def gen_pve_report(stats, quest_data, snippets):
    """生成 PvE 战报文字"""
    power = calc_battle_power(stats, snippets, TODAY)
    skills = gen_skills(stats, snippets)
    piglet_hp = piglet_today_power(power, quest_data)
    
    profile = stats.get("profile", {})
    level = profile.get("level", 1)
    name = profile.get("alias", profile.get("name", "明公"))
    
    # 玩家总伤害
    total_dmg = 0
    rounds = []
    remaining_hp = piglet_hp
    
    for i, skill in enumerate(skills, 1):
        base_dmg = skill["power"] * (power["total"] / 100) * random.uniform(0.85, 1.15)
        
        # 特殊加成
        if quest_data.get("daily", {}).get("status") == "completed":
            base_dmg *= 1.3  # 完成每日任务 +30%
        
        dmg = round(base_dmg)
        total_dmg += dmg
        remaining_hp = max(0, remaining_hp - dmg)
        
        # 小粉猪反击
        piglet_skills = [
            ("「差不多就行」", "你的创造性深度暂时 -10%"),
            ("「明日再说」", "下回合伤害减半"),
            ("「舒适区护盾」", "获得防御层"),
        ]
        pig_skill, pig_effect = random.choice(piglet_skills)
        
        rounds.append({
            "round": i,
            "skill": skill,
            "dmg": dmg,
            "remaining_hp": remaining_hp,
            "pig_skill": pig_skill,
            "pig_effect": pig_effect,
            "hp_after": remaining_hp
        })
        
        if remaining_hp <= 0:
            break
    
    won = remaining_hp <= 0
    
    # 战报文字
    incomplete_count = sum(1 for q in quest_data.get("weekly", {}).get("quests", [])
                           if q.get("status") != "completed")
    if quest_data.get("daily", {}).get("status") == "pending":
        incomplete_count += 1
    
    lines = []
    lines.append(f"🐷 PvE 战报 — {TODAY}")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"")
    lines.append(f"小粉猪今日战力：{piglet_hp} HP")
    if incomplete_count > 0:
        lines.append(f"（你有 {incomplete_count} 个未完成任务，它今天很精神 🐷）")
    else:
        lines.append(f"（你今日任务全完成，小粉猪蔫了一半 🐷💨）")
    lines.append(f"")
    lines.append(f"你的今日战力：{power['total']}")
    lines.append(f"  创造力 {power['creativity']}  认知突破 {power['cognition']}")
    lines.append(f"  执行密度 {power['execution_d']}  交互深度 {power['depth']}")
    lines.append(f"  成长显著 {power['growth']}")
    lines.append(f"")
    
    for r in rounds:
        sk = r["skill"]
        lines.append(f"【回合 {r['round']}】")
        lines.append(f"你使用 {sk['name']}（{sk['type']}·威力{sk['power']}）")
        lines.append(f"  → {sk['desc']}")
        lines.append(f"  → 造成 {r['dmg']} 点伤害！小粉猪剩余 HP：{r['hp_after']}")
        if r["hp_after"] > 0:
            lines.append(f"小粉猪反击 {r['pig_skill']} — {r['pig_effect']}")
        lines.append(f"")
    
    if won:
        # 找今日最具决定性行动
        best_skill = max(rounds, key=lambda x: x["dmg"])["skill"]["name"]
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🏆 胜利！以 {total_dmg} 总伤害击败小粉猪！")
        lines.append(f"「{best_skill}」是今日制胜关键。")
        lines.append(f"")
        lines.append(f"小粉猪临死前说：「我...明天...还会回来的...」🐷💨")
        lines.append(f"")
        lines.append(f"🎁 奖励：+30 EXP  ·  称号线索：「小粉猪克星」")
    else:
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💀 小粉猪今天赢了。但它也只敢赢你一天。")
        lines.append(f"明日复仇加成 +15%。今天，先好好休息。")
        lines.append(f"")
        lines.append(f"🎁 安慰奖：+10 EXP「虽败犹荣」")
    
    return "\n".join(lines), power, skills, piglet_hp, rounds, won

def gen_pvp_report(stats, snippets_today, snippets_yesterday):
    """生成 PvP 时间线决斗战报（今日 vs 昨日）"""
    power_today = calc_battle_power(stats, snippets_today, TODAY)
    power_yesterday = calc_battle_power(stats, snippets_yesterday, YESTERDAY)
    
    profile = stats.get("profile", {})
    name = profile.get("alias", "明公")
    
    diff = power_today["total"] - power_yesterday["total"]
    won = diff >= 0
    
    skills_today = gen_skills(stats, snippets_today)
    
    lines = []
    lines.append(f"⚔️ PvP 时间线决斗 — {TODAY}")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"今日 {name}  vs  昨日 {name}")
    lines.append(f"")
    lines.append(f"【今日战力】 {power_today['total']}")
    lines.append(f"  创造力 {power_today['creativity']}  认知突破 {power_today['cognition']}")
    lines.append(f"  执行密度 {power_today['execution_d']}  交互深度 {power_today['depth']}")
    lines.append(f"")
    lines.append(f"【昨日战力】 {power_yesterday['total']}")
    lines.append(f"  创造力 {power_yesterday['creativity']}  认知突破 {power_yesterday['cognition']}")
    lines.append(f"  执行密度 {power_yesterday['execution_d']}  交互深度 {power_yesterday['depth']}")
    lines.append(f"")
    lines.append(f"【技能释放】")
    for sk in skills_today:
        lines.append(f"  {sk['name']} — {sk['desc']}")
    lines.append(f"")
    
    if won:
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🏆 今日胜出！战力提升 +{abs(diff)} 点")
        if diff > 20:
            lines.append(f"今天的你，比昨天的你强了一大截。")
        else:
            lines.append(f"微弱优势胜出，明天继续。")
        lines.append(f"🎁 +25 EXP「时间线进化」")
    else:
        lines.append(f"━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💀 昨日自我胜出，战力差 -{abs(diff)} 点")
        lines.append(f"昨天的你设定了更高的基准。今天输了，明天赢回来。")
        lines.append(f"🎁 +15 EXP「反省之力」")
    
    return "\n".join(lines), power_today, power_yesterday, skills_today, won, diff

def draw_battle_image_pve(power, piglet_hp, skills, rounds, won, out_path):
    """生成 PvE 战场图（PIL）"""
    W, H = 900, 560
    img = Image.new("RGB", (W, H), DARK_BG)
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体
    try:
        font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        font_lg = ImageFont.truetype(font_path, 28)
        font_md = ImageFont.truetype(font_path, 20)
        font_sm = ImageFont.truetype(font_path, 16)
        font_xs = ImageFont.truetype(font_path, 14)
    except:
        font_lg = font_md = font_sm = font_xs = ImageFont.load_default()
    
    def rect(x, y, w, h, color, radius=10):
        draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=color)

    def text(x, y, t, color=WHITE, font=None):
        draw.text((x, y), t, fill=color, font=font or font_md)

    # 背景面板
    rect(0, 0, W, H, DARK_BG)
    rect(10, 10, W-20, 60, PANEL_BG)
    rect(10, 80, W//2-20, H-100, PANEL_BG)
    rect(W//2+10, 80, W//2-20, H-100, PANEL_BG)

    # 标题
    text(W//2 - 120, 22, f"⚔  德尔斐 PvE 战报  {TODAY}", GOLD, font_lg)

    # ── 左侧：玩家 ──
    text(30, 95, "【精密体系建筑师】Lv.13", GOLD, font_md)
    text(30, 125, "阑干 · 桐人", WHITE, font_md)
    text(30, 155, f"今日战力  {power['total']}", GREEN, font_lg)
    
    # 战力条
    bar_x, bar_y, bar_w, bar_h = 30, 200, 380, 18
    rect(bar_x, bar_y, bar_w, bar_h, (40, 40, 60))
    filled = int(bar_w * min(power['total'], 100) / 100)
    rect(bar_x, bar_y, filled, bar_h, GREEN)
    text(bar_x + bar_w + 8, bar_y, f"{power['total']}/100", GRAY, font_sm)

    # 五维雷达文字版
    dims = [
        ("创造力", power["creativity"]),
        ("认知突破", power["cognition"]),
        ("执行密度", power["execution_d"]),
        ("交互深度", power["depth"]),
        ("成长显著", power["growth"]),
    ]
    for i, (label, val) in enumerate(dims):
        y = 230 + i * 30
        text(30, y, f"{label}", GRAY, font_sm)
        bx, by, bw, bh = 110, y+2, 200, 14
        rect(bx, by, bw, bh, (40, 40, 60))
        rect(bx, by, int(bw * val / 100), bh, BLUE)
        text(bx + bw + 6, by, f"{val}", WHITE, font_sm)

    # 技能列表
    text(30, 390, "今日技能", GOLD, font_md)
    for i, sk in enumerate(skills[:3]):
        y = 420 + i * 36
        color = PURPLE if "魔法" in sk["type"] else RED
        rect(30, y, 380, 28, (30, 30, 50), radius=6)
        text(38, y+4, f"{sk['name']}  威力{sk['power']}", color, font_sm)

    # ── 右侧：小粉猪 ──
    text(W//2+30, 95, "【Boss】小粉猪  Piglet.exe", PINK, font_md)
    text(W//2+30, 125, "「差不多就行」具象体", GRAY, font_sm)
    
    pig_remaining = max(0, piglet_hp - sum(r["dmg"] for r in rounds))
    text(W//2+30, 160, f"HP  {pig_remaining} / {piglet_hp}", RED if pig_remaining > 0 else GREEN, font_lg)
    
    # HP 条
    bar_x2 = W//2+30
    rect(bar_x2, 200, 380, 18, (60, 20, 20))
    if piglet_hp > 0:
        hp_pct = pig_remaining / piglet_hp
        rect(bar_x2, 200, int(380 * hp_pct), 18, RED)
    
    # 小粉猪（像素风，用矩形拼）
    px, py = W//2 + 150, 240
    # 身体
    rect(px-55, py,    110, 90, PINK, radius=20)
    # 头
    rect(px-45, py-55, 90,  60, PINK, radius=15)
    # 耳朵
    rect(px-58, py-70, 25,  30, PINK, radius=8)
    rect(px+33, py-70, 25,  30, PINK, radius=8)
    # 眼睛
    if won:  # 失败的小粉猪
        draw.ellipse([px-25, py-42, px-10, py-27], fill=(80, 20, 20))
        draw.ellipse([px+10, py-42, px+25, py-27], fill=(80, 20, 20))
        # X眼
        draw.line([px-25, py-42, px-10, py-27], fill=DARK_BG, width=2)
        draw.line([px-10, py-42, px-25, py-27], fill=DARK_BG, width=2)
        draw.line([px+10, py-42, px+25, py-27], fill=DARK_BG, width=2)
        draw.line([px+25, py-42, px+10, py-27], fill=DARK_BG, width=2)
    else:
        draw.ellipse([px-25, py-42, px-10, py-27], fill=(80, 20, 80))
        draw.ellipse([px+10, py-42, px+25, py-27], fill=(80, 20, 80))
    # 鼻子
    draw.ellipse([px-15, py-20, px+15, py-5], fill=(220, 100, 130))
    draw.ellipse([px-10, py-17, px-3,  py-9], fill=DARK_BG)
    draw.ellipse([px+3,  py-17, px+10, py-9], fill=DARK_BG)
    # 嘴
    if won:
        draw.arc([px-15, py-8, px+15, py+5], 0, 180, fill=(80, 20, 20), width=2)
    else:
        draw.arc([px-15, py-5, px+15, py+8], 180, 360, fill=(80, 20, 20), width=2)
    # 腿
    rect(px-40, py+85, 30, 30, PINK, radius=8)
    rect(px+10, py+85, 30, 30, PINK, radius=8)
    # 尾巴（螺旋）
    draw.arc([px+50, py+20, px+80, py+50], 0, 270, fill=PINK, width=4)
    
    # 战报摘要（右下）
    text(W//2+30, 380, "战斗摘要", GOLD, font_md)
    for i, r in enumerate(rounds[:3]):
        y = 410 + i * 34
        rect(W//2+30, y, 380, 26, (30, 30, 50), radius=5)
        text(W//2+38, y+4, f"回合{r['round']}  {r['skill']['name']}  -{r['dmg']}HP", WHITE, font_sm)
    
    # 结果横幅
    result_y = H - 55
    result_color = GREEN if won else RED
    result_text = "🏆  VICTORY！小粉猪已击败！" if won else "💀  DEFEAT  小粉猪今天赢了"
    rect(10, result_y, W-20, 40, result_color)
    text(W//2 - 160, result_y + 8, result_text, DARK_BG if won else WHITE, font_lg)
    
    img.save(str(out_path))
    print(f"[image] 战场图已生成：{out_path}")

def draw_battle_image_pvp(power_today, power_yesterday, skills, won, diff, out_path):
    """生成 PvP 时间线决斗图"""
    W, H = 900, 500
    img = Image.new("RGB", (W, H), DARK_BG)
    draw = ImageDraw.Draw(img)

    try:
        font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        font_lg = ImageFont.truetype(font_path, 28)
        font_md = ImageFont.truetype(font_path, 20)
        font_sm = ImageFont.truetype(font_path, 16)
    except:
        font_lg = font_md = font_sm = ImageFont.load_default()

    def rect(x, y, w, h, color, radius=8):
        draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=color)
    def text(x, y, t, color=WHITE, font=None):
        draw.text((x, y), t, fill=color, font=font or font_md)

    # 标题
    rect(10, 10, W-20, 55, PANEL_BG)
    text(W//2 - 160, 18, f"⚔  时间线决斗  {TODAY} vs {YESTERDAY}", GOLD, font_lg)

    # 中间 vs
    rect(W//2-30, 80, 60, H-110, (30, 30, 50))
    text(W//2-20, H//2-20, "VS", GOLD, font_lg)

    # 左：今日
    rect(10, 75, W//2-55, H-105, PANEL_BG)
    today_color = GREEN if won else GRAY
    text(30, 90, "今日", today_color, font_md)
    text(30, 120, f"战力 {power_today['total']}", today_color, font_lg)
    dims = [("创造力", power_today["creativity"]), ("认知突破", power_today["cognition"]),
            ("执行密度", power_today["execution_d"]), ("交互深度", power_today["depth"]),
            ("成长显著", power_today["growth"])]
    for i, (label, val) in enumerate(dims):
        y = 165 + i * 30
        text(30, y, f"{label}", GRAY, font_sm)
        rect(100, y+2, 180, 14, (40,40,60))
        rect(100, y+2, int(180*val/100), 14, today_color)
        text(288, y+2, f"{val}", WHITE, font_sm)

    text(30, 325, "今日技能", GOLD, font_md)
    for i, sk in enumerate(skills[:3]):
        y = 355 + i * 34
        rect(30, y, W//2-75, 26, (30,30,50), radius=5)
        c = PURPLE if "魔法" in sk["type"] else RED
        text(38, y+4, f"{sk['name']}", c, font_sm)

    # 右：昨日
    rect(W//2+45, 75, W//2-55, H-105, PANEL_BG)
    yest_color = RED if won else GREEN
    text(W//2+65, 90, "昨日", yest_color, font_md)
    text(W//2+65, 120, f"战力 {power_yesterday['total']}", yest_color, font_lg)
    dims2 = [("创造力", power_yesterday["creativity"]), ("认知突破", power_yesterday["cognition"]),
             ("执行密度", power_yesterday["execution_d"]), ("交互深度", power_yesterday["depth"]),
             ("成长显著", power_yesterday["growth"])]
    for i, (label, val) in enumerate(dims2):
        y = 165 + i * 30
        text(W//2+65, y, f"{label}", GRAY, font_sm)
        rect(W//2+145, y+2, 180, 14, (40,40,60))
        rect(W//2+145, y+2, int(180*val/100), 14, yest_color)
        text(W//2+333, y+2, f"{val}", WHITE, font_sm)

    text(W//2+65, 325, "昨日无记录" if not power_yesterday["total"] else "昨日表现", GOLD, font_md)

    # 结果
    result_y = H - 52
    result_color = GREEN if won else RED
    if won:
        result_str = f"🏆  今日胜出！战力 +{abs(diff)}  成长进化中"
    else:
        result_str = f"💀  昨日自我胜出  差距 -{abs(diff)}  明天赢回来"
    rect(10, result_y, W-20, 38, result_color)
    text(W//2-180, result_y+8, result_str, DARK_BG if won else WHITE, font_lg)

    img.save(str(out_path))
    print(f"[image] PvP 战场图已生成：{out_path}")

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "pve"
    
    stats = load_json(STATS_FILE)
    quest_data = load_json(QUEST_FILE, {})
    snippets_today = get_sessions_text(TODAY)
    snippets_yesterday = get_sessions_text(YESTERDAY)
    
    print(f"[info] 今日交互：{len(snippets_today)} 条，昨日：{len(snippets_yesterday)} 条")
    
    if mode == "pvp":
        report, p_today, p_yesterday, skills, won, diff = gen_pvp_report(stats, snippets_today, snippets_yesterday)
        print(report)
        
        if PIL_OK:
            out_path = OUT_DIR / "battle_pvp.png"
            draw_battle_image_pvp(p_today, p_yesterday, skills, won, diff, out_path)
            with open("/tmp/battle_image_path.txt", "w") as f:
                f.write(str(out_path))
        
        with open("/tmp/battle_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
    
    else:  # pve
        report, power, skills, piglet_hp, rounds, won = gen_pve_report(stats, quest_data, snippets_today)
        print(report)
        
        if PIL_OK:
            out_path = OUT_DIR / "battle_pve.png"
            draw_battle_image_pve(power, piglet_hp, skills, rounds, won, out_path)
            with open("/tmp/battle_image_path.txt", "w") as f:
                f.write(str(out_path))
        
        with open("/tmp/battle_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
    
    print("[done] 战报生成完毕")

if __name__ == "__main__":
    main()
