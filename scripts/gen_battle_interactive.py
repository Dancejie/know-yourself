#!/usr/bin/env python3
"""
gen_battle_interactive.py — 德尔斐战斗系统 HTML 生成器

基于用户的 character_stats.json + daily_quest.json 动态生成个性化战斗界面：
- 根据属性五维自动推荐最匹配的职业（而非写死 mage）
- 技能名称和描述引用用户真实称号/属性
- 怪物 Boss HP 根据未完成任务数动态计算
- 生成的 HTML 保存到 public/ 并可直接用 html-go-live 发布

用法:
  python3 gen_battle_interactive.py [--output path/to/output.html] [--no-publish]
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# ── 路径配置 ────────────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).parent.parent.parent.parent  # ~/.openclaw/workspace
SKILL_DIR = Path(__file__).parent.parent
MEMORY_DIR = WORKSPACE / "memory"
PUBLIC_DIR = WORKSPACE / "public"
TEMPLATE_PATH = SKILL_DIR / "references" / "battle-interactive-template.html"
OUTPUT_PATH = PUBLIC_DIR / "battle_interactive.html"

CHARACTER_STATS_PATH = MEMORY_DIR / "character_stats.json"
DAILY_QUEST_PATH = MEMORY_DIR / "daily_quest.json"

# ── 职业推荐矩阵 ─────────────────────────────────────────────────────────────
# 根据 character_stats 的属性维度推荐最匹配职业
# 权重：对应属性越高，该职业推荐分越高
CLASS_WEIGHTS = {
    "knight": {
        "execution": 0.40,    # 执行纪律 → 骑士
        "architecture": 0.30, # 系统架构 → 骑士防御
        "framework": 0.20,
        "aesthetics": 0.10,
    },
    "mage": {
        "framework": 0.40,    # 框架思维 → 魔法师智慧
        "ai_depth": 0.35,     # AI工程 → 奥术
        "expression": 0.15,
        "aesthetics": 0.10,
    },
    "warrior": {
        "execution": 0.45,    # 执行密度 → 战士
        "architecture": 0.30,
        "finance": 0.15,
        "empathy": 0.10,
    },
    "thief": {
        "aesthetics": 0.35,   # 产品审美 → 盗贼灵活
        "expression": 0.35,   # 文学表达 → 盗贼语言技能
        "empathy": 0.20,
        "finance": 0.10,
    },
    "paladin": {
        "empathy": 0.40,      # 共情力 → 圣骑士神圣
        "execution": 0.25,
        "expression": 0.20,
        "aesthetics": 0.15,
    },
    "warlock": {
        "ai_depth": 0.40,     # AI工程深度 → 术士黑魔法
        "finance": 0.30,      # 金融直觉 → 灵魂汲取
        "framework": 0.20,
        "empathy": 0.10,
    },
}

CLASS_REASONS = {
    "knight": "执行纪律强 · 系统架构扎实 → 系统推荐：骑士",
    "mage": "框架思维 MAX · AI工程深度高 → 系统推荐：魔法师",
    "warrior": "执行密度高 · 架构均衡 → 系统推荐：战士",
    "thief": "产品审美突出 · 文字表达强 → 系统推荐：盗贼",
    "paladin": "共情力领先 · 表达细腻 → 系统推荐：圣骑士",
    "warlock": "AI工程精深 · 金融直觉强 → 系统推荐：术士",
}

# ── 从属性值推导职业 HP/MP ──────────────────────────────────────────────────
def derive_class_stats(class_key: str, attrs: dict) -> tuple[int, int]:
    """
    根据用户真实属性值动态推导职业 HP 和 MP。
    基础值 + 属性加成，每人数值唯一。

    HP 核心驱动：执行纪律(execution) + 系统架构(architecture)  → 稳定性/抗打
    MP 核心驱动：框架思维(framework) + AI工程(ai_depth)         → 思维能量
    """
    def attr_val(key):
        v = attrs.get(key, {})
        return v.get("value", 50) if isinstance(v, dict) else float(v)

    execution   = attr_val("execution")
    architecture = attr_val("architecture")
    framework   = attr_val("framework")
    ai_depth    = attr_val("ai_depth")
    empathy     = attr_val("empathy")
    expression  = attr_val("expression")
    aesthetics  = attr_val("aesthetics")
    finance     = attr_val("finance")

    # 各职业 HP/MP 基础值 + 属性加成公式
    # 属性值范围 0-100，加成范围约 ±150
    class_formulas = {
        "knight": {
            "hp_base": 500,
            "hp_bonus": lambda: int((execution - 50) * 2.5 + (architecture - 50) * 1.5),
            "mp_base": 180,
            "mp_bonus": lambda: int((framework - 50) * 1.0),
        },
        "mage": {
            "hp_base": 300,
            "hp_bonus": lambda: int((framework - 50) * 1.0),
            "mp_base": 420,
            "mp_bonus": lambda: int((ai_depth - 50) * 2.5 + (framework - 50) * 1.5),
        },
        "warrior": {
            "hp_base": 440,
            "hp_bonus": lambda: int((execution - 50) * 3.0),
            "mp_base": 220,
            "mp_bonus": lambda: int((architecture - 50) * 1.5 + (framework - 50) * 0.5),
        },
        "thief": {
            "hp_base": 320,
            "hp_bonus": lambda: int((aesthetics - 50) * 1.5 + (expression - 50) * 1.0),
            "mp_base": 280,
            "mp_bonus": lambda: int((expression - 50) * 2.0 + (aesthetics - 50) * 1.0),
        },
        "paladin": {
            "hp_base": 460,
            "hp_bonus": lambda: int((empathy - 50) * 2.0 + (execution - 50) * 1.0),
            "mp_base": 300,
            "mp_bonus": lambda: int((empathy - 50) * 2.0 + (expression - 50) * 1.0),
        },
        "warlock": {
            "hp_base": 280,
            "hp_bonus": lambda: int((ai_depth - 50) * 1.0),
            "mp_base": 460,
            "mp_bonus": lambda: int((ai_depth - 50) * 2.5 + (finance - 50) * 1.5),
        },
    }

    f = class_formulas.get(class_key, class_formulas["mage"])
    hp = max(150, f["hp_base"] + f["hp_bonus"]())
    mp = max(80,  f["mp_base"] + f["mp_bonus"]())
    return hp, mp


# ── 从今日 exp_log 提取行为关键词 ─────────────────────────────────────────────
def extract_today_actions(character: dict) -> list[str]:
    """
    从最近一日的 exp_log 中提取真实行为描述，
    用于生成个性化技能名和技能描述。
    返回事件 desc 列表（最多取最近8条，过滤掉「今日活跃交互」类泛化描述）。
    """
    from datetime import date
    today = date.today().isoformat()
    exp_log = character.get("exp_log", [])

    # 取最近一天，如果今天没有就取最后一天
    today_log = next((d for d in reversed(exp_log) if d.get("date") == today), None)
    if not today_log:
        today_log = exp_log[-1] if exp_log else {}

    events = today_log.get("events", [])
    # 过滤掉泛化描述
    skip_keywords = ["今日活跃交互", "系统自动巡航", "Cron 体系", "自动巡航"]
    descs = [
        e["desc"] for e in events
        if not any(kw in e.get("desc", "") for kw in skip_keywords)
    ]
    return descs[:8]


# ── 从行为描述推导技能名（规则映射） ──────────────────────────────────────────
def infer_skill_from_action(desc: str, slot_idx: int, class_key: str) -> dict | None:
    """
    根据一条 exp_log 事件描述，尝试生成对应的个性化技能。
    slot_idx 0-2：前三个普通技能槽
    返回技能 dict 或 None（无法识别时）。
    """
    desc_lower = desc.lower()

    # 行为关键词 → 技能模板
    action_skill_map = [
        # AI / PE 工程类
        (["pe", "prompt", "框架", "结构", "分层", "体系"],
         ["🔮 框架穿透术", "🧩 结构化拆解", "📐 体系降维", "🔬 精密框架咒"],
         "魔法", (80, 100), (15, 35), "框架思维具象化，结构性碾压"),

        # Agent / 系统架构类
        (["agent", "子agent", "cron", "自动化", "架构", "部署", "pipeline"],
         ["⚙️ 自动化洪流", "🤖 Agent编排术", "🔁 Cron斩击", "🏗️ 架构震慑"],
         "物理", (85, 105), (20, 40), "系统化执行，批量输出"),

        # 数据 / 分析 / 评测类
        (["数据", "分析", "评测", "准召", "badcase", "统计", "分布"],
         ["📊 数据洞察波", "🎯 精准归因弹", "📈 召回率压制", "🔍 BadCase清算"],
         "魔法", (78, 96), (18, 32), "数据驱动洞察，精准定位问题"),

        # 写作 / 文档 / 表达类
        (["写作", "文档", "redoc", "简历", "散文", "表达", "输出"],
         ["✍️ 文字炼金术", "📝 叙事重构击", "🖊️ 语言穿透", "📜 文学共鸣波"],
         "混合", (75, 92), (12, 28), "文字即武器，叙事即力量"),

        # 投资 / 金融类
        (["止损", "仓位", "投资", "复盘", "建仓", "白银", "期货", "股票"],
         ["💰 止盈纪律斩", "📉 均值回归击", "⚖️ 仓位管理术", "🎲 逆境反弹"],
         "物理", (82, 98), (20, 35), "金融直觉具象化，精准出手"),

        # 执行 / 交付类
        (["完成", "修复", "迭代", "交付", "发布", "上线", "debug"],
         ["🔧 工具链爆破", "🚀 交付冲刺", "⚡ 执行密度压制", "🛠️ 快速迭代击"],
         "物理", (80, 95), (15, 30), "执行力具象化，快速交付"),
    ]

    import random
    for keywords, skill_names, skill_type, power_range, mp_range, base_desc in action_skill_map:
        if any(kw in desc_lower for kw in keywords):
            # 根据 slot_idx 选技能名（避免同一职业重复）
            name = skill_names[slot_idx % len(skill_names)]
            # 从 desc 提取核心词作为技能描述后缀（最多10字）
            short_desc = desc[:18].rstrip("，。、") if len(desc) > 18 else desc
            return {
                "name": name,
                "type": skill_type,
                "power": random.randint(*power_range),
                "mp": random.randint(*mp_range),
                "desc": short_desc,
            }
    return None


# ── 技能个性化生成 ────────────────────────────────────────────────────────────
def generate_skills(class_key: str, character: dict) -> list[dict]:
    """
    根据职业 + 用户今日真实行为 + 称号生成个性化技能。

    槽位分配：
    - 槽 0-2：从今日 exp_log 行为推导（有行为则用，无则用职业默认）
    - 槽 3（史诗位）：称号触发专属技能，无称号则用职业默认史诗技能
    """
    titles = [t.get("name", "") if isinstance(t, dict) else str(t)
              for t in character.get("titles", [])]
    attrs = character.get("attributes", {})
    profile = character.get("profile", {})
    user_class = profile.get("class", "策略工程师")

    # 今日真实行为
    today_actions = extract_today_actions(character)

    # 职业默认技能（兜底，不含史诗槽）
    default_skills = {
        "knight": [
            {"name": "⚔️ 执行裁决", "type": "物理", "power": 85, "mp": 15, "desc": f"以{user_class}之精度，精准裁决"},
            {"name": "🛡️ 纪律防线", "type": "物理", "power": 92, "mp": 25, "desc": "执行纪律具象化，守住交付"},
            {"name": "✨ 系统修复", "type": "辅助", "power": 0,  "mp": 10, "desc": "回复50HP，稳住阵线", "heal": 50},
        ],
        "mage": [
            {"name": "🔮 框架推演", "type": "魔法", "power": 78, "mp": 12, "desc": f"{user_class}框架思维，推演全局"},
            {"name": "❄️ 结构冻结", "type": "魔法", "power": 90, "mp": 28, "desc": "系统结构压制，控制局面"},
            {"name": "🔥 认知燃爆", "type": "魔法", "power": 96, "mp": 35, "desc": "认知突破具象化，焚毁盲区"},
        ],
        "warrior": [
            {"name": "🌪️ 执行风暴", "type": "物理", "power": 82, "mp": 15, "desc": "执行密度具象化，快速清场"},
            {"name": "💪 意志强化", "type": "辅助", "power": 0,  "mp": 10, "desc": "回复35HP，斗志重燃", "heal": 35},
            {"name": "🔨 体系碾压", "type": "物理", "power": 93, "mp": 25, "desc": "架构优势压制，无视防御"},
        ],
        "thief": [
            {"name": "🗡️ 审美刺击", "type": "物理", "power": 74, "mp": 8,  "desc": "产品直觉出奇制胜"},
            {"name": "☠️ 叙事连击", "type": "混合", "power": 87, "mp": 20, "desc": "文字表达具象化，多段输出"},
            {"name": "🎯 洞察暴击", "type": "物理", "power": 0,  "mp": 30, "desc": "精准洞察，双倍伤害", "critMult": 2},
        ],
        "paladin": [
            {"name": "✝️ 共情冲锋",  "type": "神圣", "power": 86, "mp": 18, "desc": "共情力具象化，正义降临"},
            {"name": "⚖️ 价值判决",  "type": "神圣", "power": 95, "mp": 30, "desc": "核心价值观具象化，无法抵挡"},
            {"name": "🌟 情感护盾",  "type": "辅助", "power": 0,  "mp": 15, "desc": "回复60HP，感召守护", "heal": 60},
        ],
        "warlock": [
            {"name": "🖤 AI暗矢",    "type": "魔法", "power": 80, "mp": 10, "desc": "AI工程精准出击"},
            {"name": "💀 数据汲取",  "type": "魔法", "power": 88, "mp": 20, "desc": "吸取数据养料，回复20HP", "heal": 20},
            {"name": "🔗 规则枷锁",  "type": "魔法", "power": 92, "mp": 30, "desc": "规则体系压制，削弱抵抗"},
        ],
    }

    skills = list(default_skills.get(class_key, default_skills["mage"]))  # 前3槽

    # === 用今日真实行为替换前3槽 ===
    replaced = 0
    for i, action_desc in enumerate(today_actions):
        if replaced >= 3:
            break
        skill = infer_skill_from_action(action_desc, replaced, class_key)
        if skill:
            skills[replaced] = skill
            replaced += 1

    # === 槽位3（史诗位）：称号触发专属技能 ===
    # 优先级：隐藏称号 > 史诗称号 > 职业默认史诗
    title_skill_map = {
        "Inspire Your Life":  ("💫 激情绽放·全力以赴", "隐藏·魔法", 108, 42, "隐藏称号解锁：激情层爆发，无上限输出"),
        "精密体系建筑师":      ("🏛️ 架构降维打击",     "史诗·魔法", 100, 38, "精密体系建筑师专属：系统性碾压一切"),
        "规则锻造者":          ("⚖️ 边界锁定·终局",    "史诗·物理",  96, 34, "规则锻造者专属：精准控制，无法突破"),
        "工具建造者":          ("🔧 工具链爆破·批量",  "物理",       92, 26, "工具建造者专属：批量输出，效率碾压"),
        "专注炼金师":          ("🧪 专注提炼术",        "魔法",       88, 22, "专注炼金师专属：深度工作具象化"),
    }

    # 按稀有度排序，隐藏 > 史诗 > 稀有
    rarity_order = {"隐藏": 0, "史诗": 1, "稀有": 2, "rare": 2, "epic": 1}
    user_titles_sorted = sorted(
        [t if isinstance(t, dict) else {"name": t, "rarity": "稀有"}
         for t in character.get("titles", [])],
        key=lambda t: rarity_order.get(t.get("rarity", "稀有"), 3)
    )

    epic_skill = None
    for t in user_titles_sorted:
        tname = t.get("name", "")
        if tname in title_skill_map:
            sk_name, sk_type, sk_power, sk_mp, sk_desc = title_skill_map[tname]
            epic_skill = {
                "name": sk_name, "type": sk_type,
                "power": sk_power, "mp": sk_mp,
                "desc": sk_desc, "isEpic": True,
            }
            break

    # 没有匹配称号则用职业默认史诗技能
    if not epic_skill:
        default_epics = {
            "knight":  {"name": "🏆 荣耀终判",    "type": "史诗", "power": 105, "mp": 42, "desc": "执行极限，荣耀终局"},
            "mage":    {"name": "💥 奥法极爆",    "type": "史诗", "power": 112, "mp": 52, "desc": "框架极限，认知毁天灭地"},
            "warrior": {"name": "🦅 英雄降临",    "type": "史诗", "power": 103, "mp": 42, "desc": "执行极限，从天而降审判"},
            "thief":   {"name": "🌑 绝影刺杀",    "type": "史诗", "power": 0,   "mp": 45, "desc": "审美极限，双倍暴击", "critMult": 2},
            "paladin": {"name": "☀️ 天罚降临",    "type": "史诗", "power": 108, "mp": 47, "desc": "共情极限，神明亲临"},
            "warlock": {"name": "☄️ 毁灭协议",    "type": "史诗", "power": 115, "mp": 58, "desc": "AI极限，虚空毁灭"},
        }
        epic_skill = {**default_epics.get(class_key, default_epics["mage"]), "isEpic": True}

    skills.append(epic_skill)
    return skills


def recommend_class(character: dict) -> tuple[str, str]:
    """
    根据 character_stats 属性推荐最匹配职业。
    返回 (class_key, reason)
    """
    attrs = character.get("attributes", {})

    scores = {}
    for class_key, weights in CLASS_WEIGHTS.items():
        score = 0.0
        for attr_key, weight in weights.items():
            attr_val = attrs.get(attr_key, {})
            if isinstance(attr_val, dict):
                val = attr_val.get("value", 0)
            else:
                val = float(attr_val)
            score += (val / 100.0) * weight
        scores[class_key] = score

    best = max(scores, key=lambda k: scores[k])
    reason = CLASS_REASONS.get(best, f"综合评估 → 系统推荐：{best}")

    # 加入最高属性名
    top_attr = max(attrs.items(),
                   key=lambda kv: kv[1].get("value", 0) if isinstance(kv[1], dict) else 0,
                   default=("", {}))
    top_label = top_attr[1].get("label", "") if isinstance(top_attr[1], dict) else ""
    if top_label:
        reason = f"{top_label} MAX · " + reason.split("·", 1)[-1].strip()

    return best, reason


def count_incomplete_quests(daily_quest: dict) -> int:
    """统计今日+周常未完成任务数"""
    count = 0
    daily = daily_quest.get("daily", {})
    if daily.get("status") != "completed":
        count += 1
    for q in daily_quest.get("weekly", {}).get("quests", []):
        if q.get("status") != "completed":
            count += 1
    return count


def build_character_js(character: dict, daily_quest: dict) -> str:
    """
    生成注入 HTML 的完整个性化 JS 数据块，包括：
    - CHARACTER：姓名/称号/推荐职业
    - PERSONALIZED_CLASS_DATA：从用户属性推导的 HP/MP（每人唯一）
    - PERSONALIZED_SKILLS：从今日行为+称号生成的技能
    - BOSS_HP_BONUS：未完成任务惩罚
    """
    profile  = character.get("profile", {})
    attrs    = character.get("attributes", {})
    titles_raw = character.get("titles", [])
    titles = [t.get("name", "") if isinstance(t, dict) else str(t) for t in titles_raw]

    recommended_class, recommended_reason = recommend_class(character)
    incomplete = count_incomplete_quests(daily_quest)
    boss_hp_bonus = incomplete * 60

    # ── 1. CHARACTER ──────────────────────────────────────────────────────────
    char_js = f"""
// === 德尔斐计划：个性化战斗数据（由 gen_battle_interactive.py 生成）===
// 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
const CHARACTER = {{
  name: {json.dumps(profile.get('name', '冒险者').split('·')[0].strip(), ensure_ascii=False)},
  alias: {json.dumps(profile.get('alias', '桐人'), ensure_ascii=False)},
  level: {profile.get('level', 1)},
  titles: {json.dumps(titles, ensure_ascii=False)},
  recommendedClass: {json.dumps(recommended_class, ensure_ascii=False)},
  recommendedReason: {json.dumps(recommended_reason, ensure_ascii=False)}
}};
const BOSS_HP_BONUS = {boss_hp_bonus};  // 未完成任务 {incomplete} 个 × 60
"""

    # ── 2. PERSONALIZED_CLASS_DATA：从属性推导 HP/MP ──────────────────────────
    class_atktype = {
        "knight": "物理", "mage": "魔法", "warrior": "物理",
        "thief": "混合", "paladin": "神圣", "warlock": "魔法",
    }
    class_intro = {
        "knight":  f"以{profile.get('class','策略工程师')}之执行力，正义必将实现！",
        "mage":    f"以{profile.get('class','策略工程师')}之框架，感受体系的力量！",
        "warrior": f"以{profile.get('class','策略工程师')}之密度，今天我不会退缩！",
        "thief":   f"没人能追上{profile.get('alias','桐人')}的审美直觉...",
        "paladin": f"共情与价值观，就是{profile.get('alias','桐人')}的力量！",
        "warlock": f"AI的深度，将化为{profile.get('alias','桐人')}的武器。",
    }

    class_data_lines = ["const PERSONALIZED_CLASS_DATA = {"]
    for cls in ["knight", "mage", "warrior", "thief", "paladin", "warlock"]:
        hp, mp = derive_class_stats(cls, attrs)
        intro  = class_intro.get(cls, "战斗开始！")
        atk    = class_atktype.get(cls, "物理")
        class_data_lines.append(
            f"  {cls}: {{maxHp:{hp}, maxMp:{mp}, "
            f"atkType:{json.dumps(atk, ensure_ascii=False)}, "
            f"intro:{json.dumps(intro, ensure_ascii=False)}}},"
        )
    class_data_lines.append("};")

    # ── 3. PERSONALIZED_SKILLS：今日行为+称号生成技能 ─────────────────────────
    skills_by_class = {}
    for cls in ["knight", "mage", "warrior", "thief", "paladin", "warlock"]:
        skills_by_class[cls] = generate_skills(cls, character)

    skill_js_lines = ["const PERSONALIZED_SKILLS = {"]
    for cls, skills in skills_by_class.items():
        skill_js_lines.append(f"  {cls}: [")
        for sk in skills:
            parts = [
                f'name:{json.dumps(sk["name"], ensure_ascii=False)}',
                f'type:{json.dumps(sk["type"], ensure_ascii=False)}',
                f'power:{sk["power"]}',
                f'mp:{sk["mp"]}',
                f'desc:{json.dumps(sk["desc"], ensure_ascii=False)}',
            ]
            if sk.get("isEpic"):  parts.append("isEpic:true")
            if sk.get("heal"):    parts.append(f'heal:{sk["heal"]}')
            if sk.get("critMult"):parts.append(f'critMult:{sk["critMult"]}')
            if sk.get("mpRestore"):parts.append(f'mpRestore:{sk["mpRestore"]}')
            skill_js_lines.append(f"    {{{','.join(parts)}}},")
        skill_js_lines.append("  ],")
    skill_js_lines.append("};")

    return char_js + "\n".join(class_data_lines) + "\n" + "\n".join(skill_js_lines)


def patch_html(template_html: str, character: dict, daily_quest: dict) -> str:
    """把个性化数据注入模板 HTML"""
    inject_js = build_character_js(character, daily_quest)

    # 找到模板里 CHARACTER 定义的位置，整块替换
    # 定位标记：从 "const CHARACTER = {" 到 "};" (第一个独立行)
    pattern = r"(// === 德尔斐计划：个性化战斗数据.*?)?const CHARACTER\s*=\s*\{.*?\};\s*\n"
    # 简单方案：在 </script> 前找到 CHARACTER 定义并替换
    # 模板里有：const CHARACTER = { ... };
    char_pattern = re.compile(
        r'const CHARACTER\s*=\s*\{[^}]+\};',
        re.DOTALL
    )

    # 找 PERSONALIZED_SKILLS 或 SKILL_DATA（如存在）也一起替换
    skill_pattern = re.compile(
        r'const PERSONALIZED_SKILLS\s*=\s*\{.*?\n\};',
        re.DOTALL
    )

    # 替换 BOSS_HP_BONUS（如果模板里有）
    boss_pattern = re.compile(r'const BOSS_HP_BONUS\s*=\s*\d+;.*?\n')

    # 先去掉旧的个性化注释块（如果二次生成）
    old_block_pattern = re.compile(
        r'// === 德尔斐计划：个性化战斗数据.*?(?=const SPRITE_CDN)',
        re.DOTALL
    )
    template_html = old_block_pattern.sub('', template_html)

    # 去掉旧的 CHARACTER 定义
    template_html = char_pattern.sub('', template_html)
    template_html = skill_pattern.sub('', template_html)
    template_html = boss_pattern.sub('', template_html)

    # 在 SPRITE_CDN 定义之前注入个性化数据
    inject_marker = "const SPRITE_CDN"
    template_html = template_html.replace(
        inject_marker,
        inject_js + "\n" + inject_marker
    )

    # 在静态数据定义完成后，注入覆盖逻辑
    # 覆盖点：DIFFICULTY_STARS 定义之后（CLASS_DATA/SKILL_DATA/MONSTER_DATA 均已定义）
    override_js = """
// ── 德尔斐计划：个性化数据覆盖 ──────────────────────────────────────────────
// 1. 用从用户属性推导的 HP/MP 覆盖 CLASS_DATA（保留其他字段）
if(typeof PERSONALIZED_CLASS_DATA !== 'undefined'){
  Object.keys(PERSONALIZED_CLASS_DATA).forEach(cls => {
    if(CLASS_DATA[cls]){
      const p = PERSONALIZED_CLASS_DATA[cls];
      CLASS_DATA[cls].maxHp  = p.maxHp;
      CLASS_DATA[cls].maxMp  = p.maxMp;
      CLASS_DATA[cls].atkType = p.atkType;
      CLASS_DATA[cls].intro  = p.intro;
    }
  });
}
// 2. 用今日行为+称号生成的技能覆盖 SKILL_DATA
if(typeof PERSONALIZED_SKILLS !== 'undefined'){
  Object.assign(SKILL_DATA, PERSONALIZED_SKILLS);
}
// 3. Boss HP 加成（未完成任务惩罚）
if(typeof BOSS_HP_BONUS !== 'undefined' && BOSS_HP_BONUS > 0){
  Object.keys(MONSTER_DATA).forEach(k => {
    MONSTER_DATA[k].maxHp += BOSS_HP_BONUS;
  });
}
// ──────────────────────────────────────────────────────────────────────────────
"""
    monster_end = "const DIFFICULTY_STARS"
    template_html = template_html.replace(
        monster_end,
        override_js + monster_end
    )

    return template_html


def main():
    import argparse
    parser = argparse.ArgumentParser(description="生成个性化德尔斐战斗 HTML")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="输出 HTML 路径")
    parser.add_argument("--character-stats", default=str(CHARACTER_STATS_PATH))
    parser.add_argument("--daily-quest", default=str(DAILY_QUEST_PATH))
    parser.add_argument("--template", default=str(TEMPLATE_PATH))
    args = parser.parse_args()

    # 读取数据
    print("📖 读取人物档案...")
    if not Path(args.character_stats).exists():
        print(f"❌ 找不到 character_stats.json: {args.character_stats}")
        sys.exit(1)
    with open(args.character_stats, "r", encoding="utf-8") as f:
        character = json.load(f)

    print("📋 读取每日任务...")
    daily_quest = {}
    if Path(args.daily_quest).exists():
        with open(args.daily_quest, "r", encoding="utf-8") as f:
            daily_quest = json.load(f)
    else:
        print("  ⚠️  daily_quest.json 不存在，Boss HP 使用默认值")

    # 读取模板
    print("📄 读取战斗 HTML 模板...")
    if not Path(args.template).exists():
        print(f"❌ 找不到模板文件: {args.template}")
        sys.exit(1)
    with open(args.template, "r", encoding="utf-8") as f:
        template_html = f.read()

    # 生成个性化 HTML
    print("⚙️  生成个性化战斗界面...")
    profile = character.get("profile", {})
    recommended_class, reason = recommend_class(character)
    incomplete = count_incomplete_quests(daily_quest)

    print(f"  👤 角色：{profile.get('alias', '桐人')} Lv.{profile.get('level', 1)} {profile.get('class', '')}")
    print(f"  ✦  推荐职业：{recommended_class}（{reason}）")
    print(f"  ⚠️  未完成任务：{incomplete} 个 → Boss HP +{incomplete * 60}")

    output_html = patch_html(template_html, character, daily_quest)

    # 保存
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_html)

    print(f"\n✅ 战斗 HTML 已生成：{out_path}")
    print(f"   本地预览：http://10.40.123.131:8899/{out_path.name}")
    print(f"\n💡 发布线上命令：")
    print(f"   cd ~/.openclaw/workspace/skills/html-go-live && \\")
    print(f"   python3 scripts/html_go_live.py --file {out_path} --name '德尔斐战斗系统' \\")
    print(f"   --update 172A49CAC6F775415C41A0CE52BD2AC8 --skip-maintainer-prompt")


if __name__ == "__main__":
    main()
