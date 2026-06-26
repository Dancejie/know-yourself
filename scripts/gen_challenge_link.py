#!/usr/bin/env python3
"""
gen_challenge_link.py — 生成 PvP 挑战链接

读取 character_stats.json，把战斗数据打包成 base64 URL 参数，
生成可分享的挑战链接。对方打开链接即可直接接受挑战（无需安装 skill）。

用法:
  python3 gen_challenge_link.py
  python3 gen_challenge_link.py --base-url https://aifin.xiaohongshu.com/...
  python3 gen_challenge_link.py --output /tmp/challenge.txt

触发词：「生成挑战卡片」「挑战链接」「发起挑战」「我要挑战」
"""

import json
import base64
import sys
import argparse
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(__file__).parent.parent.parent.parent
CHARACTER_STATS_PATH = WORKSPACE / "memory" / "character_stats.json"
DAILY_QUEST_PATH = WORKSPACE / "memory" / "daily_quest.json"

# aifin 平台嵌套 iframe，hash 传不进去，改用直链
BATTLE_URL = "http://10.40.123.131:8899/battle_interactive.html"
BATTLE_URL_ONLINE = "https://aifin.xiaohongshu.com/apps/copilot/chart-container?dashboardId=172A49CAC6F775415C41A0CE52BD2AC8"

# 职业键名映射（class_key → 中文名）
CLASS_NAMES = {
    "knight": "骑士", "mage": "魔法师", "warrior": "战士",
    "thief": "盗贼", "paladin": "圣骑士", "warlock": "术士",
}

# 属性 → 职业推荐（与 gen_battle_interactive.py 保持一致）
CLASS_WEIGHTS = {
    "knight":  {"execution":0.40,"architecture":0.30,"framework":0.20,"aesthetics":0.10},
    "mage":    {"framework":0.40,"ai_depth":0.35,"expression":0.15,"aesthetics":0.10},
    "warrior": {"execution":0.45,"architecture":0.30,"finance":0.15,"empathy":0.10},
    "thief":   {"aesthetics":0.35,"expression":0.35,"empathy":0.20,"finance":0.10},
    "paladin": {"empathy":0.40,"execution":0.25,"expression":0.20,"aesthetics":0.15},
    "warlock": {"ai_depth":0.40,"finance":0.30,"framework":0.20,"empathy":0.10},
}

def recommend_class(character: dict) -> str:
    attrs = character.get("attributes", {})
    scores = {}
    for cls, weights in CLASS_WEIGHTS.items():
        score = 0.0
        for attr_key, weight in weights.items():
            attr_val = attrs.get(attr_key, {})
            val = attr_val.get("value", 0) if isinstance(attr_val, dict) else float(attr_val)
            score += (val / 100.0) * weight
        scores[cls] = score
    return max(scores, key=lambda k: scores[k])


def build_skill_list(character: dict, class_key: str) -> list[dict]:
    """生成挑战者的代表技能（4个）"""
    titles = [t.get("name","") if isinstance(t, dict) else str(t)
              for t in character.get("titles", [])]
    profile = character.get("profile", {})

    base_skills = {
        "knight": [
            {"name":"⚔️ 判决之剑","type":"物理","power":85},
            {"name":"🛡️ 圣盾冲锋","type":"物理","power":92},
            {"name":"✨ 神圣护盾","type":"辅助","power":0},
            {"name":"🏆 荣耀打击","type":"史诗","power":102},
        ],
        "mage": [
            {"name":"🔮 奥术飞弹","type":"魔法","power":75},
            {"name":"❄️ 冰霜新星","type":"魔法","power":88},
            {"name":"🔥 燃烧大地","type":"魔法","power":94},
            {"name":"💥 奥法爆发","type":"史诗","power":108},
        ],
        "warrior": [
            {"name":"🌪️ 旋风斩","type":"物理","power":82},
            {"name":"💪 战嚎","type":"辅助","power":0},
            {"name":"🔨 破甲打击","type":"物理","power":91},
            {"name":"🦅 英雄之跃","type":"史诗","power":100},
        ],
        "thief": [
            {"name":"🗡️ 暗影刺击","type":"物理","power":72},
            {"name":"☠️ 毒雾连击","type":"混合","power":86},
            {"name":"🎯 背刺暴击","type":"物理","power":0},
            {"name":"💨 烟雾撤退","type":"辅助","power":0},
        ],
        "paladin": [
            {"name":"✝️ 神圣冲锋","type":"神圣","power":85},
            {"name":"⚖️ 圣光审判","type":"神圣","power":94},
            {"name":"🌟 圣盾祈祷","type":"辅助","power":0},
            {"name":"☀️ 天罚降临","type":"史诗","power":105},
        ],
        "warlock": [
            {"name":"🖤 暗影箭","type":"魔法","power":78},
            {"name":"💀 灵魂汲取","type":"魔法","power":86},
            {"name":"🔗 诅咒枷锁","type":"魔法","power":90},
            {"name":"☄️ 毁灭之击","type":"史诗","power":110},
        ],
    }

    skills = list(base_skills.get(class_key, base_skills["mage"]))

    # 称号触发史诗技能
    title_overrides = {
        "精密体系建筑师": {"name":"🏛️ 架构降维打击","type":"史诗·魔法","power":96},
        "规则锻造者":     {"name":"⚖️ 边界锁定","type":"史诗·物理","power":93},
        "工具建造者":     {"name":"🔧 工具链爆破","type":"物理","power":88},
        "Inspire Your Life": {"name":"💫 激情绽放","type":"隐藏·魔法","power":99},
    }
    for title in titles:
        if title in title_overrides:
            skills[3] = title_overrides[title]
            break

    return skills


def generate_challenge_data(character: dict) -> dict:
    """把 character_stats 压缩成挑战数据包"""
    profile = character.get("profile", {})
    titles_raw = character.get("titles", [])
    titles = [t.get("name","") if isinstance(t, dict) else str(t) for t in titles_raw]

    class_key = recommend_class(character)
    skills = build_skill_list(character, class_key)

    return {
        "v": 1,                                    # 版本号
        "name": profile.get("name", "").split("·")[0].strip(),
        "alias": profile.get("alias", "冒险者"),
        "level": profile.get("level", 1),
        "classKey": class_key,
        "className": CLASS_NAMES.get(class_key, class_key),
        "titles": titles[:4],                       # 最多4个称号
        "skills": skills,
        "ts": int(datetime.now().timestamp()),      # 生成时间戳（防重放）
    }


def generate_url(challenge_data: dict, base_url: str = BATTLE_URL) -> str:
    json_str = json.dumps(challenge_data, ensure_ascii=False, separators=(",",":"))
    b64 = base64.b64encode(json_str.encode("utf-8")).decode("ascii")
    # 用 hash（#pvp=base64）而非 query string
    # aifin 平台会过滤 query 额外参数，但不处理 hash，客户端可读取
    return f"{base_url}#pvp={b64}"


def main():
    parser = argparse.ArgumentParser(description="生成德尔斐 PvP 挑战链接")
    parser.add_argument("--character-stats", default=str(CHARACTER_STATS_PATH))
    parser.add_argument("--base-url", default=BATTLE_URL)
    parser.add_argument("--output", default=None, help="输出到文件（默认打印到终端）")
    args = parser.parse_args()

    stats_path = Path(args.character_stats)
    if not stats_path.exists():
        print(f"❌ 找不到 character_stats.json: {stats_path}", file=sys.stderr)
        sys.exit(1)

    with open(stats_path, encoding="utf-8") as f:
        character = json.load(f)

    profile = character.get("profile", {})
    challenge_data = generate_challenge_data(character)
    url = generate_url(challenge_data, args.base_url)

    class_key = challenge_data["classKey"]
    class_name = challenge_data["className"]
    titles_str = " / ".join(challenge_data["titles"][:2]) or "（无称号）"
    skill_names = " · ".join(s["name"] for s in challenge_data["skills"])

    output_lines = [
        "",
        "⚔️  德尔斐挑战卡片已生成！",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  挑战者：{challenge_data['alias']}（{profile.get('name','')}）",
        f"  职业：{class_name}  Lv.{challenge_data['level']}",
        f"  称号：{titles_str}",
        f"  技能：{skill_names}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "🔗 挑战链接（发到 Hi 群 / 朋友圈）：",
        url,
        "",
        "📋 Hi 群发送模板：",
        f"我在「德尔斐计划」中是 Lv.{challenge_data['level']} {class_name}，称号「{challenge_data['titles'][0] if challenge_data['titles'] else '无'}」",
        f"敢来挑战我吗？👇",
        url,
        "",
    ]

    result = "\n".join(output_lines)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"✅ 已保存到 {args.output}")
    else:
        print(result)

    # 写入临时文件供 agent 读取
    tmp_path = Path("/tmp/challenge_link.txt")
    tmp_path.write_text(result + f"\nURL_ONLY:{url}", encoding="utf-8")


if __name__ == "__main__":
    main()
