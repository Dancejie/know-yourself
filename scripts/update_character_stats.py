#!/usr/bin/env python3
"""
update_character_stats.py
根据当日会话增量内容，计算经验值、更新属性、解锁称号。

用法：
    python3 update_character_stats.py \
        --stats /tmp/know_yourself_stats.json \
        --delta /tmp/persona_content_delta.json \
        --char ~/.openclaw/workspace/memory/character_stats.json \
        --date 2026-04-21 \
        [--events-json '{"events": [...]}']  # 由主 agent LLM 生成

输出：更新后的 character_stats.json，同时打印 Redoc 面板 Markdown 片段到 stdout
"""

import argparse, json, sys
from datetime import datetime
from pathlib import Path

# ── 经验表：每级所需经验（简单线性，后期可改） ──────────────────────────────
def exp_to_next_level(level: int) -> int:
    return 100 + (level - 1) * 50  # Lv1→100, Lv2→150, ...

# ── 稀有度显示颜色 ──────────────────────────────────────────────────────────
RARITY_COLOR = {
    "普通":   "#888888",
    "稀有":   "#4a90d9",
    "史诗":   "#9b59b6",
    "传说":   "#e67e22",
    "隐藏":   "#c0392b",
}

def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())

def save_json(path: str, data: dict):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))

def apply_events(char: dict, events: list, date: str) -> tuple[int, list[str]]:
    """应用经验事件，返回总获得经验和解锁称号列表。"""
    total_exp = 0
    unlocked_titles = []

    for ev in events:
        exp = ev.get("exp", 0)
        total_exp += exp

        # 属性加成
        for attr, bonus in ev.get("attr_bonus", {}).items():
            if attr in char["attributes"]:
                char["attributes"][attr]["value"] = min(
                    100, char["attributes"][attr]["value"] + bonus
                )

        # 灵魂三分同步（logos/thumos/epithumia 归一化）
        for soul_key in ["logos", "thumos", "epithumia"]:
            if soul_key in ev.get("attr_bonus", {}):
                total = sum(char["attributes"][k]["value"]
                            for k in ["logos", "thumos", "epithumia"])
                if total != 100:
                    # 简单归一：把差值从最大者上扣除
                    keys = ["logos", "thumos", "epithumia"]
                    diff = total - 100
                    max_key = max(keys, key=lambda k: char["attributes"][k]["value"])
                    char["attributes"][max_key]["value"] -= diff

        # 称号解锁
        title_id = ev.get("title_unlocked")
        if title_id:
            existing_ids = [t["id"] for t in char["titles"]]
            if title_id not in existing_ids:
                # 从 events 里找 title 定义，或从 ev 里取
                new_title = {
                    "id": title_id,
                    "name": ev.get("title_name", title_id),
                    "acquired": date,
                    "desc": ev.get("title_desc", ""),
                    "rarity": ev.get("title_rarity", "普通"),
                }
                char["titles"].append(new_title)
                unlocked_titles.append(new_title["name"])

    # 写入今日 exp_log
    log_entry = {
        "date": date,
        "events": events,
        "total_exp_gained": total_exp,
    }
    existing_dates = [e["date"] for e in char.get("exp_log", [])]
    if date in existing_dates:
        for e in char["exp_log"]:
            if e["date"] == date:
                e["events"].extend(events)
                e["total_exp_gained"] += total_exp
    else:
        char.setdefault("exp_log", []).append(log_entry)

    return total_exp, unlocked_titles

def level_up(char: dict, gained_exp: int) -> list[str]:
    """更新经验值，处理升级，返回升级日志。"""
    log = []
    char["profile"]["exp"] += gained_exp
    char["profile"]["total_exp"] = char["profile"].get("total_exp", 0) + gained_exp

    while True:
        needed = exp_to_next_level(char["profile"]["level"])
        char["profile"]["exp_to_next"] = needed
        if char["profile"]["exp"] >= needed:
            char["profile"]["exp"] -= needed
            char["profile"]["level"] += 1
            log.append(f"🎉 升级！当前等级 Lv.{char['profile']['level']}")
        else:
            break

    return log

def render_redoc_panel(char: dict) -> str:
    """生成 Redoc 人物面板 Markdown 片段。"""
    p = char["profile"]
    attrs = char["attributes"]
    titles = char["titles"]
    level = p["level"]
    exp = p["exp"]
    exp_next = exp_to_next_level(level)
    bar_filled = int((exp / exp_next) * 20)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    # 灵魂三分（从 char['soul'] 读取，独立于 attributes）
    soul_data = char.get("soul", {})
    soul_order = ["logos", "thumos", "epithumia"]
    soul_rows = []
    for k in soul_order:
        if k in soul_data:
            a = soul_data[k]
            val = a["value"]
            bar_s = "█" * int(val/5) + "░" * (20 - int(val/5))
            soul_rows.append(f'| {a["label"]} | **{val}%** | `{bar_s}` | {a["desc"]} |')

    # 综合属性（排除灵魂三分key）
    exclude = {"logos", "thumos", "epithumia"}
    attr_rows = []
    for key, a in attrs.items():
        if key in exclude:
            continue
        val = a["value"]
        bar_s = "█" * int(val/5) + "░" * (20 - int(val/5))
        attr_rows.append(f'| {a["label"]} | **{val}** | `{bar_s}` | {a["desc"]} |')

    # 称号（全部，最新在前，彩色文字 + 稀有度标注）
    title_lines = []
    for t in reversed(titles):
        color = RARITY_COLOR.get(t.get("rarity", "普通"), "#888888")
        rarity = t.get("rarity", "普通")
        name = t["name"]
        acquired = t["acquired"]
        desc = t.get("desc", "")
        title_lines.append(
            f'<span style="color:{color};font-size:15px">**◆ {name}**</span>'
            f'　<span style="color:{color};font-size:11px">[ {rarity} · {acquired} ]</span>\n\n'
            f'<span style="color:#888888;font-size:12px">{desc}</span>\n'
        )

    # 今日获得经验（取最新一条日志）
    today_log = char.get("exp_log", [])[-1] if char.get("exp_log") else None
    today_events_md = "_今日暂无经验记录_"
    if today_log:
        lines = [f'- **+{ev["exp"]} EXP** {ev["desc"]}' for ev in today_log.get("events", [])]
        if lines:
            today_events_md = "\n".join(lines)

    # 转职路线
    next_classes = char.get("class_evolution", {}).get("next_options", [])
    class_lines = "\n".join(
        f'- **{c["class"]}** — {c["condition"]} `{c["progress"]}`'
        for c in next_classes
    )

    soul_table = "\n".join(soul_rows)
    attr_table = "\n".join(attr_rows)
    title_block = "\n".join(title_lines)

    panel = f"""## ○ 人物面板（RPG · 德尔斐计划）

<img src="{RADAR_IMG}" width="860" />

<!-- colWidth: [160,590] -->
| 字段 | 值 |
| --- | --- |
| 职业 | **{p["class"]}** |
| 原型 | {p["archetype"]} |
| 等级 | **Lv.{level}** |
| 经验 | `{exp} / {exp_next}`　{bar} |
| 累计经验 | {p.get("total_exp", exp)} EXP |

**灵魂三分**

<!-- colWidth: [160,60,200,330] -->
| 维度 | 值 | 进度 | 说明 |
| --- | --- | --- | --- |
{soul_table}

**综合属性**

<!-- colWidth: [120,60,200,370] -->
| 属性 | 值 | 进度 | 说明 |
| --- | --- | --- | --- |
{attr_table}

**称号**

{title_block}

**今日成长**

{today_events_md if today_events_md else "_今日暂无经验记录_"}

**转职路线**

{class_lines if class_lines else "_暂无转职选项_"}
"""
    return panel

# character_history.txt 存放在 references/ 下
HISTORY_FILE = Path(__file__).parent.parent / "references" / "character_history.txt"
# 雷达图 CDN 地址（每次重新生成上传后更新此常量）
RADAR_IMG = "https://xhs-doc.xhscdn.com/104004dg31vr0asrc1m047hk2lk"

def append_history(char: dict, date: str):
    """把当日经验记录和新增称号沉淀到 references/character_history.txt"""
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    hist_file = HISTORY_FILE

    lines = [f"\n{'='*60}", f"日期：{date}", f"等级：Lv.{char['profile']['level']}  累计EXP：{char['profile'].get('total_exp',0)}"]

    # 当日经验事件
    today_log = next((e for e in char.get("exp_log", []) if e.get("date") == date), None)
    if today_log:
        lines.append(f"\n【今日经验（+{today_log['total_exp_gained']} EXP）】")
        for ev in today_log.get("events", []):
            bonus = ""
            if ev.get("attr_bonus"):
                bonus = " | 属性+" + "/".join(f"{k}:{v}" for k,v in ev["attr_bonus"].items())
            title_note = f" | 解锁称号：{ev['title_unlocked']}" if ev.get("title_unlocked") else ""
            lines.append(f"  +{ev['exp']} EXP  {ev['desc']}{bonus}{title_note}")

    # 当日新增称号
    new_titles = [t for t in char.get("titles", []) if t.get("acquired") == date]
    if new_titles:
        lines.append("\n【新增称号】")
        for t in new_titles:
            lines.append(f"  [{t['rarity']}] {t['name']}  —  {t.get('desc','')}")

    with open(hist_file, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  [history] 已追加到 {hist_file}", file=sys.stderr)


def extract_panel_block(doc_md: str) -> str:
    """从 Redoc read-doc 输出中提取人物面板章节（标题到下一个 --- 之间）。"""
    marker = "## ○ 人物面板（RPG · 德尔斐计划）"
    start = doc_md.find(marker)
    if start == -1:
        return ""
    # 找面板结束：下一个以 --- 单独成行的分隔符
    rest = doc_md[start:]
    import re
    m = re.search(r'\n---\s*\n', rest)
    if m:
        return rest[:m.start()]
    return rest  # 没有找到分隔符则取到末尾


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--char", required=True, help="character_stats.json 路径")
    parser.add_argument("--events-json", default=None, help="当日经验事件 JSON 字符串")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--print-panel", action="store_true", help="打印 Redoc 面板")
    parser.add_argument("--save-history", action="store_true", help="沉淀当日记录到 references/character_history.txt")
    parser.add_argument("--update-redoc", default=None, help="自动读取旧面板并整体替换，传入 shortcutId")
    args = parser.parse_args()

    char = load_json(args.char)

    if args.events_json:
        events_data = json.loads(args.events_json)
        events = events_data.get("events", [])
        gained_exp, unlocked = apply_events(char, events, args.date)
        level_logs = level_up(char, gained_exp)

        char["_updated"] = datetime.now().isoformat(timespec="seconds") + "+08:00"
        save_json(args.char, char)

        print(f"✓ 今日获得 {gained_exp} EXP", file=sys.stderr)
        for log in level_logs:
            print(log, file=sys.stderr)
        if unlocked:
            print(f"🏆 解锁称号：{', '.join(unlocked)}", file=sys.stderr)

    if args.save_history:
        append_history(char, args.date)

    if args.print_panel:
        print(render_redoc_panel(char))

    if args.update_redoc:
        import subprocess, tempfile, os
        shortcut_id = args.update_redoc
        run_sh = str(Path(__file__).parent.parent.parent / "redoc-enhanced" / "run.sh")

        # 1. 读取当前文档（source 格式，保留 img 标签原文）
        result = subprocess.run([run_sh, "read-doc", shortcut_id, "--format", "source"],
                                capture_output=True, text=True)
        old_doc = result.stdout

        # 2. 提取旧面板块
        old_panel = extract_panel_block(old_doc)
        if not old_panel:
            print("  [redoc] 未找到面板章节，跳过更新", file=sys.stderr)
        else:
            # 3. 生成新面板块
            new_panel = render_redoc_panel(char)

            # 4. 用 edit-doc --old-source / --new-source 整体替换（保留 img 标签）
            proc = subprocess.run(
                [run_sh, "edit-doc", shortcut_id,
                 "--old-source", old_panel.strip(),
                 "--new-source", new_panel.strip()],
                capture_output=True, text=True
            )
            if proc.returncode == 0:
                print(f"  [redoc] 面板已整体替换 ✓", file=sys.stderr)
                # Redoc 会自动补 height 属性，立刻移除（height 会导致图片下方大量空白）
                subprocess.run(
                    [run_sh, "edit-doc", shortcut_id,
                     "--old-source", f'<img src="{RADAR_IMG}" width="860" height=',
                     "--new-source", f'<img src="{RADAR_IMG}" width="860" '],
                    capture_output=True, text=True
                )
                # 更精确：用 read-source 查找实际 height 值后替换
                src2 = subprocess.run([run_sh, "read-doc", shortcut_id, "--format", "source"],
                                      capture_output=True, text=True).stdout
                import re as _re
                from PIL import Image as _Image
                try:
                    _img = _Image.open(Path(__file__).parent.parent.parent / "public" / "rpg_radar.png")
                    _iw, _ih = _img.size
                    correct_h = int(860 * _ih / _iw)
                except Exception:
                    correct_h = 557  # 默认值
                m = _re.search(r'<img src="' + _re.escape(RADAR_IMG) + r'"[^/]*/>', src2)
                if m:
                    old_img = m.group(0)
                    new_img = f'<img src="{RADAR_IMG}" width="860" height="{correct_h}" />'
                    if old_img != new_img:
                        subprocess.run(
                            [run_sh, "edit-doc", shortcut_id,
                             "--old-source", old_img,
                             "--new-source", new_img],
                            capture_output=True, text=True
                        )
                        print(f"  [redoc] 已修正 height={correct_h} (比例正确) ✓", file=sys.stderr)
            else:
                print(f"  [redoc] 替换失败: {proc.stderr[:200]}", file=sys.stderr)

if __name__ == "__main__":
    main()
