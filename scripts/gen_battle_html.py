#!/usr/bin/env python3
"""
gen_battle_html.py — 生成战场 HTML 并用 Chrome headless 截图
"""

import json, os, sys, datetime, random
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))
STATS_FILE = WORKSPACE / "memory/character_stats.json"
QUEST_FILE = WORKSPACE / "memory/daily_quest.json"
SESSIONS_DIR = Path(os.path.expanduser("~/.openclaw/agents/main/sessions"))
OUT_DIR = WORKSPACE / "public"
OUT_DIR.mkdir(exist_ok=True)

TODAY = datetime.date.today().isoformat()
YESTERDAY = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

def load_json(path, default=None):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return default or {}

def get_sessions_text(date_str):
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

def calc_power(stats, snippets, date_str):
    text = " ".join(snippets).lower()
    creativity = min(100, sum(10 for k in ["设计","新增","想法","系统","架构","方案","战斗","pvp","pve","html","创新"] if k in text))
    cognition  = min(100, sum(12 for k in ["发现","原来","洞察","理解了","盲区","反直觉","重新","明白"] if k in text))
    execution  = min(100, sum(8  for k in ["完成","生成","部署","发布","写了","跑了","测试","发送","提交","更新"] if k in text))
    depth      = max(min(60, len(snippets)*5), min(100, sum(10 for k in ["为什么","怎么","如何","逻辑","底层","本质"] if k in text)))
    exp_log    = stats.get("exp_log", [])
    today_log  = next((e for e in exp_log if e.get("date") == date_str), None)
    today_exp  = today_log.get("total_exp_gained", 0) if today_log else 0
    growth     = min(100, today_exp * 2)
    action     = creativity*0.25 + cognition*0.20 + execution*0.20 + depth*0.15 + growth*0.20
    level      = stats.get("profile", {}).get("level", 1)
    attrs      = stats.get("attributes", {})
    avg_attr   = sum(a.get("value",50) for a in attrs.values()) / max(len(attrs),1)
    base       = min(100, level*5 + avg_attr*0.3)
    total      = action*0.7 + base*0.3
    return {"total": round(total), "creativity": round(creativity), "cognition": round(cognition),
            "execution_d": round(execution), "depth": round(depth), "growth": round(growth),
            "today_exp": today_exp}

def gen_skills(stats, snippets):
    text = " ".join(snippets).lower()
    titles = [t.get("name","") for t in stats.get("titles",[])]
    skills = []
    if any(k in text for k in ["cron","脚本","部署","测试","发布","gen_","html","battle"]):
        skills.append({"name":"⚙️ 自动化斩","type":"物理","power":random.randint(65,85),"effect":"无视防御"})
    if any(k in text for k in ["简历","文档","redoc","写","分析","设计"]):
        skills.append({"name":"📄 叙事重构击","type":"物理","power":random.randint(60,80),"effect":"清晰度冲击"})
    if any(k in text for k in ["设计","想法","系统","机制","战斗","pvp","pve","战场"]):
        skills.append({"name":"🔮 体系降维术","type":"魔法","power":random.randint(70,90),"effect":"结构性震慑"})
    if any(k in text for k in ["pe","prompt","打标","agent"]):
        skills.append({"name":"✨ PE 框架咒","type":"魔法","power":random.randint(65,85),"effect":"规则锁定"})
    if "精密体系建筑师" in titles:
        skills.append({"name":"🏛️ 架构降维打击","type":"魔法·史诗","power":random.randint(80,100),"effect":"无视50%魔防"})
    if "规则锻造者" in titles:
        skills.append({"name":"⚖️ 边界锁定","type":"物理·史诗","power":random.randint(75,95),"effect":"减少对手暴击40%"})
    if not skills:
        skills.append({"name":"🧠 理性分析波","type":"魔法","power":random.randint(55,75),"effect":"稳定伤害"})
    return skills[:3]

def piglet_hp(quest_data, power):
    daily = quest_data.get("daily", {})
    weekly = quest_data.get("weekly", {})
    incomplete = (1 if daily.get("status") == "pending" else 0)
    incomplete += sum(1 for q in weekly.get("quests",[]) if q.get("status") != "completed")
    hp = max(80, 200 + incomplete*50 + random.randint(-30,30))
    if power["today_exp"] > 100: hp = int(hp * 0.7)
    elif power["today_exp"] > 50: hp = int(hp * 0.85)
    return hp

def gen_battle_html(mode, stats, quest_data, snippets_today, snippets_yesterday):
    profile = stats.get("profile", {})
    level = profile.get("level", 1)
    name = profile.get("alias", "明公")
    cls = profile.get("class", "Agent 策略工程师")
    titles = stats.get("titles", [])
    title_str = " / ".join(f"【{t['name']}】" for t in titles[-2:]) if titles else ""

    p_today = calc_power(stats, snippets_today, TODAY)
    skills = gen_skills(stats, snippets_today)

    if mode == "pve":
        pig_hp_max = piglet_hp(quest_data, p_today)
        # simulate rounds
        rounds = []
        remaining = pig_hp_max
        for sk in skills:
            dmg = round(sk["power"] * (p_today["total"]/100) * random.uniform(0.85,1.15))
            if quest_data.get("daily",{}).get("status") == "completed":
                dmg = int(dmg * 1.3)
            remaining = max(0, remaining - dmg)
            pig_counters = ["「差不多就行」","「明日再说」","「舒适区护盾」"]
            rounds.append({"skill": sk, "dmg": dmg, "remaining": remaining,
                           "counter": random.choice(pig_counters)})
            if remaining <= 0:
                break
        won = remaining <= 0

        # 生成 rounds HTML
        rounds_html = ""
        for i, r in enumerate(rounds, 1):
            sk = r["skill"]
            type_color = "#9b59b6" if "魔法" in sk["type"] else "#e74c3c"
            pig_hp_bar = int(100 * r["remaining"] / pig_hp_max) if pig_hp_max > 0 else 0
            counter_html = f'<div class="counter">🐷 反击 {r["counter"]}</div>' if r["remaining"] > 0 else ""
            rounds_html += f"""
            <div class="round">
              <div class="round-header">回合 {i}</div>
              <div class="skill-line">
                <span class="skill-badge" style="background:{type_color}">{sk['type']}</span>
                <span class="skill-name">{sk['name']}</span>
                <span class="skill-power">威力 {sk['power']}</span>
              </div>
              <div class="dmg-line">造成 <span class="dmg">{r['dmg']}</span> 点伤害 &nbsp;·&nbsp; 小粉猪剩余 <span class="hp-num">{r['remaining']}</span> HP</div>
              <div class="pig-bar-wrap"><div class="pig-bar" style="width:{pig_hp_bar}%"></div></div>
              {counter_html}
            </div>"""

        result_class = "win" if won else "lose"
        result_text = "🏆 VICTORY！小粉猪已击败！+30 EXP" if won else "💀 DEFEAT — 小粉猪今天赢了。明日复仇 +15%"
        pig_face = "😵" if won else "😤"
        incomplete_count = (1 if quest_data.get("daily",{}).get("status")=="pending" else 0)
        incomplete_count += sum(1 for q in quest_data.get("weekly",{}).get("quests",[]) if q.get("status")!="completed")

        html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:900px; background:#0a0a14; color:#e8e8f0; font-family:'Noto Sans SC',sans-serif; padding:24px; }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#16213e); border:1px solid #2a2a4a; border-radius:12px; padding:20px 28px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; }}
  .header-title {{ font-size:22px; font-weight:900; color:#d4af37; letter-spacing:2px; }}
  .header-date {{ font-size:13px; color:#6b6b8a; }}
  .battle-arena {{ display:grid; grid-template-columns:1fr 80px 1fr; gap:0; }}
  .fighter {{ background:#12122a; border:1px solid #2a2a4a; border-radius:12px; padding:20px; }}
  .fighter-name {{ font-size:18px; font-weight:700; margin-bottom:4px; }}
  .fighter-sub {{ font-size:12px; color:#6b6b8a; margin-bottom:12px; }}
  .power-big {{ font-size:36px; font-weight:900; margin:8px 0; }}
  .power-label {{ font-size:11px; color:#6b6b8a; margin-bottom:12px; }}
  .dim-row {{ display:flex; align-items:center; gap:8px; margin:5px 0; }}
  .dim-label {{ font-size:12px; color:#8888aa; width:60px; flex-shrink:0; }}
  .dim-bar-bg {{ flex:1; height:10px; background:#1e1e3a; border-radius:5px; overflow:hidden; }}
  .dim-bar {{ height:100%; border-radius:5px; transition:width .3s; }}
  .dim-val {{ font-size:11px; color:#aaa; width:28px; text-align:right; }}
  .vs-col {{ display:flex; align-items:center; justify-content:center; }}
  .vs-text {{ font-size:32px; font-weight:900; color:#d4af37; text-shadow:0 0 20px #d4af3788; }}
  .pig-panel {{ text-align:center; }}
  .pig-emoji {{ font-size:72px; line-height:1; margin:8px 0; }}
  .pig-name {{ font-size:14px; font-weight:700; color:#ff9ec0; margin-bottom:4px; }}
  .pig-sub {{ font-size:11px; color:#6b6b8a; margin-bottom:10px; }}
  .hp-bar-bg {{ background:#2a0a0a; border-radius:6px; height:14px; overflow:hidden; margin:8px 0; }}
  .hp-bar {{ background:linear-gradient(90deg,#c0392b,#e74c3c); height:100%; border-radius:6px; }}
  .hp-text {{ font-size:12px; color:#e74c3c; }}
  .rounds-section {{ margin-top:16px; }}
  .section-title {{ font-size:13px; color:#d4af37; font-weight:700; margin-bottom:10px; letter-spacing:1px; text-transform:uppercase; }}
  .round {{ background:#0e0e22; border:1px solid #1e1e3a; border-radius:8px; padding:12px 16px; margin-bottom:8px; }}
  .round-header {{ font-size:11px; color:#6b6b8a; margin-bottom:6px; }}
  .skill-line {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; }}
  .skill-badge {{ font-size:10px; padding:2px 7px; border-radius:10px; color:#fff; font-weight:700; }}
  .skill-name {{ font-size:15px; font-weight:700; }}
  .skill-power {{ font-size:11px; color:#8888aa; margin-left:auto; }}
  .dmg-line {{ font-size:13px; color:#ccc; margin-bottom:6px; }}
  .dmg {{ font-size:18px; font-weight:900; color:#e74c3c; }}
  .hp-num {{ font-size:15px; font-weight:700; color:#f39c12; }}
  .pig-bar-wrap {{ background:#1a0a0a; height:8px; border-radius:4px; overflow:hidden; margin:4px 0; }}
  .pig-bar {{ background:linear-gradient(90deg,#c0392b,#e74c3c); height:100%; }}
  .counter {{ font-size:12px; color:#ff9ec0; margin-top:6px; padding:4px 10px; background:#1a0a14; border-radius:6px; display:inline-block; }}
  .result-banner {{ margin-top:16px; border-radius:10px; padding:16px 24px; text-align:center; font-size:18px; font-weight:900; letter-spacing:1px; }}
  .win {{ background:linear-gradient(135deg,#0a2a0a,#1a4a1a); border:1px solid #2ecc71; color:#2ecc71; }}
  .lose {{ background:linear-gradient(135deg,#2a0a0a,#4a1a1a); border:1px solid #e74c3c; color:#e74c3c; }}
  .titles {{ margin-top:10px; font-size:11px; color:#d4af37; }}
</style>
</head>
<body>
<div class="header">
  <div class="header-title">⚔ 德尔斐 PvE 战报</div>
  <div class="header-date">{TODAY} &nbsp;|&nbsp; Lv.{level} {cls}</div>
</div>

<div class="battle-arena">
  <div class="fighter">
    <div class="fighter-name" style="color:#d4af37">{name}</div>
    <div class="fighter-sub">{cls}</div>
    <div class="power-big" style="color:#2ecc71">{p_today['total']}</div>
    <div class="power-label">今日战力</div>
    {''.join(f'<div class="dim-row"><span class="dim-label">{l}</span><div class="dim-bar-bg"><div class="dim-bar" style="width:{v}%;background:#3498db"></div></div><span class="dim-val">{v}</span></div>' for l,v in [("创造力",p_today["creativity"]),("认知突破",p_today["cognition"]),("执行密度",p_today["execution_d"]),("交互深度",p_today["depth"]),("成长显著",p_today["growth"])])}
    <div class="titles">{title_str}</div>
  </div>

  <div class="vs-col"><div class="vs-text">VS</div></div>

  <div class="fighter pig-panel">
    <div class="pig-name">小粉猪 Piglet.exe</div>
    <div class="pig-sub">「差不多就行」具象体</div>
    <div class="pig-emoji">{pig_face}</div>
    <div class="pig-sub">{'你有 '+str(incomplete_count)+' 个未完成任务，它今天很精神' if incomplete_count>0 else '你任务全完成，它蔫了一半'}</div>
    <div class="hp-bar-bg"><div class="hp-bar" style="width:{int(100*remaining/pig_hp_max) if pig_hp_max>0 else 0}%"></div></div>
    <div class="hp-text">HP {remaining} / {pig_hp_max}</div>
    <br>
    <div style="font-size:12px;color:#8888aa">技能：「拖延漩涡」「差不多就行」<br>「明日再说」「舒适区护盾」</div>
  </div>
</div>

<div class="rounds-section">
  <div class="section-title">战斗过程</div>
  {rounds_html}
</div>

<div class="result-banner {result_class}">{result_text}</div>
</body>
</html>"""
        return html, won

    else:  # pvp
        p_yesterday = calc_power(stats, snippets_yesterday, YESTERDAY)
        won = p_today["total"] >= p_yesterday["total"]
        diff = p_today["total"] - p_yesterday["total"]

        def make_bars(p, color):
            return ''.join(f'<div class="dim-row"><span class="dim-label">{l}</span><div class="dim-bar-bg"><div class="dim-bar" style="width:{v}%;background:{color}"></div></div><span class="dim-val">{v}</span></div>'
                           for l, v in [("创造力",p["creativity"]),("认知突破",p["cognition"]),("执行密度",p["execution_d"]),("交互深度",p["depth"]),("成长显著",p["growth"])])

        skills_html = "".join(f'<div class="skill-item"><span class="skill-badge" style="background:{"#9b59b6" if "魔法" in sk["type"] else "#e74c3c"}">{sk["type"]}</span> {sk["name"]} <span style="color:#888;font-size:11px">威力{sk["power"]}</span></div>' for sk in skills)

        result_class = "win" if won else "lose"
        result_text = f"🏆 今日胜出！战力提升 +{abs(diff)} · 时间线进化中 +25 EXP" if won else f"💀 昨日自我胜出，差距 -{abs(diff)} · 明天赢回来 +15 EXP「反省之力」"

        html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:900px; background:#0a0a14; color:#e8e8f0; font-family:'Noto Sans SC',sans-serif; padding:24px; }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#16213e); border:1px solid #2a2a4a; border-radius:12px; padding:20px 28px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; }}
  .header-title {{ font-size:22px; font-weight:900; color:#d4af37; letter-spacing:2px; }}
  .header-sub {{ font-size:13px; color:#6b6b8a; }}
  .arena {{ display:grid; grid-template-columns:1fr 60px 1fr; gap:0; }}
  .fighter {{ background:#12122a; border:1px solid #2a2a4a; border-radius:12px; padding:20px; }}
  .fighter.today {{ border-color:#2ecc71; }}
  .fighter.yesterday {{ border-color:#e74c3c; }}
  .badge {{ display:inline-block; font-size:10px; padding:2px 8px; border-radius:10px; font-weight:700; margin-bottom:8px; }}
  .power-big {{ font-size:42px; font-weight:900; margin:8px 0 4px; }}
  .power-label {{ font-size:11px; color:#6b6b8a; margin-bottom:14px; }}
  .dim-row {{ display:flex; align-items:center; gap:8px; margin:5px 0; }}
  .dim-label {{ font-size:12px; color:#8888aa; width:60px; flex-shrink:0; }}
  .dim-bar-bg {{ flex:1; height:10px; background:#1e1e3a; border-radius:5px; overflow:hidden; }}
  .dim-bar {{ height:100%; border-radius:5px; }}
  .dim-val {{ font-size:11px; color:#aaa; width:28px; text-align:right; }}
  .vs-col {{ display:flex; align-items:center; justify-content:center; }}
  .vs-text {{ font-size:28px; font-weight:900; color:#d4af37; text-shadow:0 0 20px #d4af3788; }}
  .skills-section {{ margin-top:16px; background:#0e0e22; border:1px solid #1e1e3a; border-radius:10px; padding:14px 18px; }}
  .section-title {{ font-size:12px; color:#d4af37; font-weight:700; margin-bottom:10px; letter-spacing:1px; }}
  .skill-item {{ font-size:13px; padding:5px 0; border-bottom:1px solid #1a1a2e; }}
  .skill-item:last-child {{ border:none; }}
  .skill-badge {{ font-size:10px; padding:1px 6px; border-radius:8px; color:#fff; font-weight:700; margin-right:4px; }}
  .result-banner {{ margin-top:16px; border-radius:10px; padding:16px 24px; text-align:center; font-size:17px; font-weight:900; letter-spacing:1px; }}
  .win {{ background:linear-gradient(135deg,#0a2a0a,#1a4a1a); border:1px solid #2ecc71; color:#2ecc71; }}
  .lose {{ background:linear-gradient(135deg,#2a0a0a,#4a1a1a); border:1px solid #e74c3c; color:#e74c3c; }}
</style>
</head>
<body>
<div class="header">
  <div class="header-title">⚔ 时间线决斗</div>
  <div class="header-sub">今日 {name} vs 昨日 {name} &nbsp;|&nbsp; {TODAY}</div>
</div>

<div class="arena">
  <div class="fighter today">
    <span class="badge" style="background:#1a4a1a;color:#2ecc71">今日</span>
    <div style="font-size:16px;font-weight:700;color:#d4af37">{name}</div>
    <div style="font-size:11px;color:#6b6b8a;margin-bottom:8px">Lv.{level} · {cls}</div>
    <div class="power-big" style="color:#2ecc71">{p_today['total']}</div>
    <div class="power-label">今日战力</div>
    {make_bars(p_today, "#2ecc71")}
  </div>

  <div class="vs-col"><div class="vs-text">VS</div></div>

  <div class="fighter yesterday">
    <span class="badge" style="background:#4a1a1a;color:#e74c3c">昨日</span>
    <div style="font-size:16px;font-weight:700;color:#d4af37">{name}</div>
    <div style="font-size:11px;color:#6b6b8a;margin-bottom:8px">Lv.{level} · {cls}</div>
    <div class="power-big" style="color:#e74c3c">{p_yesterday['total']}</div>
    <div class="power-label">昨日战力</div>
    {make_bars(p_yesterday, "#e74c3c")}
  </div>
</div>

<div class="skills-section">
  <div class="section-title">今日技能</div>
  {skills_html}
</div>

<div class="result-banner {result_class}">{result_text}</div>
</body>
</html>"""
        return html, won

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "pve"
    stats = load_json(STATS_FILE)
    quest_data = load_json(QUEST_FILE, {})
    snippets_today = get_sessions_text(TODAY)
    snippets_yesterday = get_sessions_text(YESTERDAY)

    html, won = gen_battle_html(mode, stats, quest_data, snippets_today, snippets_yesterday)

    html_path = OUT_DIR / f"battle_{mode}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"[html] 写入 {html_path}")

    # Chrome headless 截图
    png_path = OUT_DIR / f"battle_{mode}.png"
    import subprocess
    result = subprocess.run([
        "google-chrome", "--headless=new", "--no-sandbox",
        "--disable-gpu", "--disable-dev-shm-usage",
        f"--screenshot={png_path}",
        "--window-size=900,700",
        "--hide-scrollbars",
        f"file://{html_path}"
    ], capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        print(f"[png] 截图成功：{png_path}")
        with open("/tmp/battle_image_path.txt", "w") as f:
            f.write(str(png_path))
    else:
        print(f"[warn] Chrome 截图失败：{result.stderr[:200]}")

if __name__ == "__main__":
    main()
