#!/usr/bin/env python3
"""从头生成完整 HTML，不做注入，避免重复 JS 冲突"""
import hashlib, os

FILENAME  = "persona-dangsi.html"
EXPIRE_MS = int(open('/tmp/expire_ms.txt').read().strip())
TOKEN     = hashlib.sha256(FILENAME.encode()).hexdigest()[:16]
SERVER    = "http://10.4.110.159:8899"
AVATAR    = open('/tmp/avatar_b64.txt').read().strip()

# ── 读取 pairs 数据（原始涂黑内容）直接硬编码，不依赖原文件 ──
HTML = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CLASSIFIED — DS-PN-2026-DANGSI</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Special+Elite&family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}

body{{
  background:#1e1e1e;
  display:flex;flex-direction:column;align-items:center;
  padding-top:136px;padding-bottom:40px;padding-left:20px;padding-right:20px;
  font-family:'Courier Prime','Courier New',monospace;
  min-height:100vh;
}}

/* ══ 顶部固定条 ══ */
#top-bar{{
  position:fixed;top:0;left:0;right:0;z-index:9999;
  background:#0e0a06;
  border-bottom:2px solid #6F1714;
  font-family:'Courier Prime',monospace;
}}
/* 行1：倒计时 */
#cd-row{{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 28px 6px;
  border-bottom:1px solid rgba(111,23,20,.35);
}}
.cd-meta{{display:flex;flex-direction:column;gap:2px}}
.cd-label{{color:#4a3a2a;font-size:9px;letter-spacing:3px;text-transform:uppercase}}
#cd-display{{
  font-size:40px;font-weight:700;letter-spacing:7px;
  color:#c0140e;line-height:1;
  text-shadow:0 0 22px rgba(192,20,14,.4);
  text-align:center;flex:1;
}}
#cd-display.warn{{animation:blink .8s infinite;color:#ff2200}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.15}}}}
#cd-sub{{font-size:10px;letter-spacing:3px;color:#4a3a2a;text-align:center;margin-top:3px}}
.cd-destroy{{
  cursor:pointer;border:1px solid #6F1714;color:#c0140e;
  padding:8px 16px;font-size:11px;letter-spacing:2px;
  background:transparent;transition:all .2s;
  font-family:'Courier Prime',monospace;white-space:nowrap;
}}
.cd-destroy:hover{{background:#6F1714;color:#fff}}
/* 行2：工具栏 */
#tool-row{{
  display:flex;align-items:center;justify-content:center;
  gap:14px;padding:7px 28px;flex-wrap:wrap;
}}
.tip{{font-size:13px;letter-spacing:1px;color:#555}}
.sep{{color:#2a2a2a}}
.tbtn{{
  cursor:pointer;padding:4px 14px;border:1px solid #2e2416;border-radius:2px;
  color:#777;font-size:13px;letter-spacing:1px;
  background:transparent;transition:all .2s;
  font-family:'Courier Prime',monospace;
}}
.tbtn:hover{{border-color:#6F1714;color:#c0140e}}
.tbtn.on{{border-color:#c0140e;color:#c0140e;background:rgba(111,23,20,.12)}}

/* ══ 档案纸 ══ */
.page{{
  position:relative;width:820px;
  background:#e8dfc0;
  padding:58px 68px 72px 76px;
  margin-bottom:44px;
  line-height:1.8;font-size:13.5px;color:#1a1407;
  box-shadow:0 0 0 1px #bfaa78,5px 8px 40px rgba(0,0,0,.65),10px 14px 80px rgba(0,0,0,.3);
  background-image:
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3CfeBlend in='SourceGraphic' mode='multiply'/%3E%3C/filter%3E%3Crect width='400' height='400' filter='url(%23n)' opacity='.07'/%3E%3C/svg%3E"),
    linear-gradient(155deg,#f0e8cc 0%,#e4d9b4 35%,#ece2c0 65%,#e0d5ae 100%);
}}
.page:nth-child(3){{transform:rotate(.3deg)}}
.page::before{{content:'';position:absolute;left:54px;top:0;bottom:0;width:1px;background:rgba(160,25,25,.22)}}
.page::after{{content:'';position:absolute;left:0;right:0;top:31%;height:1px;
  background:linear-gradient(90deg,transparent,rgba(0,0,0,.07) 20%,rgba(0,0,0,.12) 50%,rgba(0,0,0,.07) 80%,transparent)}}

.doc-header{{border-bottom:2px solid #1a1407;padding-bottom:12px;margin-bottom:22px;
  display:flex;justify-content:space-between;align-items:flex-start}}
.doc-title{{font-family:'Special Elite',cursive;font-size:19px;letter-spacing:3px;text-transform:uppercase}}
.doc-sub{{font-size:10px;letter-spacing:2px;color:#6b5a2a;margin-bottom:4px;text-transform:uppercase}}
.doc-stamp{{font-size:11px;text-align:right;color:#6b5a2a;letter-spacing:1px;line-height:1.6}}

.stamp{{display:inline-block;border:3px solid rgba(170,15,15,.82);color:rgba(165,12,12,.85);
  font-family:'Special Elite',cursive;font-size:24px;letter-spacing:6px;
  padding:3px 16px;transform:rotate(-8deg);opacity:.82;
  position:absolute;top:44px;right:72px;white-space:nowrap}}
.stamp::before{{content:'';position:absolute;inset:2px;border:1px solid rgba(170,15,15,.35)}}

.meta-grid{{display:grid;grid-template-columns:110px 1fr;gap:0 14px;margin-bottom:26px}}
.meta-label{{padding:5px 0 0;font-weight:700;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#6b5a2a;line-height:1.3}}
.meta-val{{padding:3px 0 0;line-height:1.5}}
.meta-val .zh{{display:block;font-size:12px;color:#5a4a20;margin-top:1px}}
.meta-sep{{grid-column:1/-1;height:1px;background:rgba(0,0,0,.08);margin:4px 0}}

.section-title{{font-weight:700;font-size:11px;letter-spacing:2.5px;text-transform:uppercase;
  margin:22px 0 4px;border-bottom:1px solid rgba(0,0,0,.25);padding-bottom:3px;color:#1a1407}}
.para{{margin-bottom:4px}}
.para-zh{{font-size:12.5px;color:#4a3c10;margin-bottom:14px;line-height:1.75}}

/* 涂黑 */
.R{{display:inline;background:#1a1407;color:#1a1407;cursor:pointer;padding:1px 4px;
  border-radius:1px;user-select:none;transition:background .15s,color .15s}}
.R:hover{{opacity:.85}}
.R.open{{background:#fff5d6!important;color:#8b1a1a!important;border-bottom:1px dashed #8b1a1a}}

/* 圈注 */
.circled{{position:relative;display:inline}}
.c-svg{{position:absolute;top:-7px;left:-8px;width:calc(100% + 16px);height:calc(100% + 14px);
  pointer-events:none;overflow:visible}}
.c-svg ellipse{{fill:none;stroke:#c0140e;stroke-width:2;opacity:.82}}

/* 手写下划线 */
.ul-hw{{position:relative;display:inline}}
.ul-hw::after{{content:'';position:absolute;left:-1px;right:-1px;bottom:-3px;
  height:1.8px;background:#1a1407;border-radius:1px;transform:rotate(-.4deg);opacity:.7}}
.ul-red::after{{background:#c0140e;opacity:.8}}

/* 档案照 */
.photo-frame{{float:right;margin:0 0 18px 26px}}
.photo-frame img{{display:block;width:120px;height:120px;object-fit:cover;
  border:1px solid #8a7a50;filter:contrast(1.05) brightness(.97)}}
.photo-frame::after{{content:'SUBJECT';display:block;font-size:9px;letter-spacing:3px;
  color:#7a6a40;text-align:center;margin-top:4px}}

/* 评分条 */
.score-table{{width:100%;margin:8px 0 16px;border-collapse:collapse}}
.score-table td{{padding:4px 8px 4px 0;font-size:12.5px;vertical-align:middle}}
.s-label{{width:130px;color:#3a2d0a}}
.s-zh{{font-size:11px;color:#7a6a40;padding-left:4px;width:80px}}
.score-bar-bg{{width:200px;height:7px;background:rgba(0,0,0,.12);border-radius:2px}}
.score-bar-fill{{height:100%;border-radius:2px;background:#8b1a1a}}
.score-num{{width:30px;font-size:12px;color:#6b5a2a;text-align:right}}

/* 边缘批注 */
.margin-note{{position:absolute;left:8px;font-family:'Special Elite',cursive;
  font-size:10px;color:rgba(20,50,130,.72);transform:rotate(-90deg);
  transform-origin:left center;white-space:nowrap}}
/* 水印 */
.watermark{{position:absolute;bottom:90px;right:50px;font-family:'Special Elite',cursive;
  font-size:55px;color:rgba(160,15,15,.055);letter-spacing:4px;
  transform:rotate(-28deg);pointer-events:none;user-select:none}}
/* 页脚 */
.footer{{display:flex;justify-content:space-between;align-items:flex-end;
  margin-top:38px;border-top:1px solid #a89060;padding-top:14px;
  font-size:11px;color:#6b5a2a}}
.stamp-footer{{border:2px solid rgba(10,90,10,.72);color:rgba(8,85,8,.8);
  font-family:'Special Elite',cursive;font-size:12px;letter-spacing:3px;
  padding:3px 10px;transform:rotate(3deg);opacity:.85}}
.divider{{width:820px;text-align:center;color:#555;font-size:10px;
  letter-spacing:4px;margin:6px 0 28px;text-transform:uppercase}}

@media(max-width:880px){{.page,.divider{{width:100%}}}}
</style>
</head>
<body>

<!-- ══ 顶部固定条 ══ -->
<div id="top-bar">
  <div id="cd-row">
    <div class="cd-meta">
      <div class="cd-label">&#9888; FILE AUTO-DESTRUCT &nbsp;·&nbsp; 档案自毁</div>
      <div class="cd-label">DS-PN-2026-DANGSI</div>
    </div>
    <div style="flex:1;text-align:center">
      <div id="cd-display">--:--:--</div>
      <div id="cd-sub">EXPIRES IN 24H &nbsp;·&nbsp; 24小时后销毁</div>
    </div>
    <button class="cd-destroy" onclick="earlyDestruct()">&#9889;&nbsp;立即销毁</button>
  </div>
  <div id="tool-row">
    <span class="tip">⬛ 点击涂黑可解密</span>
    <span class="sep">·</span>
    <button id="rbtn" class="tbtn" onclick="toggleRedact()">✂ 框选涂黑：关</button>
    <span class="sep">·</span>
    <button class="tbtn" onclick="undoRedact()">↩ 撤销</button>
    <span class="sep">·</span>
    <button class="tbtn" onclick="saveHTML()">💾 保存为文件</button>
  </div>
</div>

<!-- ══ PAGE 1 ══ -->
<div class="page" style="transform:rotate(-.3deg)">
  <div class="stamp">CLASSIFIED</div>
  <div class="watermark">SECRET</div>
  <div class="margin-note" style="top:230px">DS-PN / DELPHIC SYS / 2026</div>
  <div class="doc-header">
    <div>
      <div class="doc-sub">Delphic Systems · Internal Use Only · 德尔斐系统 · 内部专用</div>
      <div class="doc-title">Behavioral Intelligence File<br><span style="font-size:14px;letter-spacing:2px">行为情报档案</span></div>
    </div>
    <div class="doc-stamp">FORM NO. 94-A<br>DATE: 2026-04-15<br>PAGE 1 OF 2</div>
  </div>

  <div class="meta-grid">
    <span class="meta-label">File No.<br>档案编号</span>
    <div class="meta-val">DS-PN-2026-DANGSI</div>
    <div class="meta-sep"></div>
    <span class="meta-label">Subject<br>对象代号</span>
    <div class="meta-val"><span class="ul-hw">党思捷 / CODE: 阑干</span><span class="zh">党思捷 / 编号：阑干</span></div>
    <div class="meta-sep"></div>
    <span class="meta-label">D.O.B.<br>出生日期</span>
    <div class="meta-val">1998-12-31 | Age: 27<span class="zh">1998年12月31日 | 27岁</span></div>
    <div class="meta-sep"></div>
    <span class="meta-label">Affiliation<br>所属机构</span>
    <div class="meta-val">
      <span class="circled">小红书 · LLM Innovation Division<svg class="c-svg" viewBox="0 0 270 26"><ellipse cx="135" cy="13" rx="131" ry="12"/></svg></span>
      <span class="zh">小红书 · 大模型创新策略研究</span>
    </div>
    <div class="meta-sep"></div>
    <span class="meta-label">Analyst<br>分析师</span>
    <div class="meta-val">Alice·V / Delphic Systems<span class="zh">爱丽丝·V / 德尔菲克系统</span></div>
    <div class="meta-sep"></div>
    <span class="meta-label">Data Span<br>数据跨度</span>
    <div class="meta-val">2026-03-20 → 2026-04-15 (26d · 21 sessions · ~18MB)<span class="zh">26天 · 21次会话 · ~18MB</span></div>
    <div class="meta-sep"></div>
    <span class="meta-label">Clearance<br>权限等级</span>
    <div class="meta-val">
      <span class="R" id="r0" data-zh="r0z">LEVEL-3 / SUBJECT ACCESS ONLY</span>
      <span class="zh"><span class="R" id="r0z" data-en="r0">三级 / 仅限主体访问</span></span>
    </div>
  </div>

  <div class="section-title">I. Identity Assessment &nbsp;<span style="font-weight:400;letter-spacing:1px">一、身份评估</span></div>

  <div class="photo-frame"><img src="{AVATAR}" alt="subject"></div>

  <p class="para">Subject operates under the self-assigned designation <span class="ul-hw">"阑干"</span>, born December 31, 1998. Educational background spans <span class="circled">Software Engineering + Financial Mathematics (dual degree)<svg class="c-svg" viewBox="0 0 380 26"><ellipse cx="190" cy="13" rx="186" ry="12"/></svg></span> at Northwest University (211), followed by MSc in <span class="ul-hw">Fintech &amp; Risk Control</span> at Audiencia Business School, France.</p>
  <p class="para-zh">教育背景广泛，<span class="ul-hw ul-red">软件工程+金融数学（双学位）</span>于西北大学（211），随后在法国审计商学院获得<span class="ul-hw">金融科技与风险控制</span>理学硕士学位。</p>

  <p class="para">Current role: Strategy Research, LLM Innovation Division, Xiaohongshu. Prior intelligence-adjacent experience: <span class="R" id="r1" data-zh="r1z">Private Equity Fund · CICC · iFLYTEK</span>. Subject demonstrates a <span class="ul-hw ul-red">pronounced tendency to treat AI systems as infrastructure</span> — classified as <strong>AI-Native (Tier 1)</strong>.</p>
  <p class="para-zh">现任职务：战略研究，大模型创新部，小红书。前有情报相关经验：<span class="R" id="r1z" data-en="r1">私募基金 · 中金公司 · 科大讯飞</span>。被归类为 <strong>AI-原生（Tier 1）</strong>。</p>

  <div class="section-title">II. Psychological Profile &nbsp;<span style="font-weight:400;letter-spacing:1px">二、心理特征</span></div>

  <p class="para">Behavioral modeling across 21 sessions: <span class="circled">Platonic tripartite soul distribution<svg class="c-svg" viewBox="0 0 295 26"><ellipse cx="147" cy="13" rx="143" ry="12"/></svg></span> — Logos (Reason) <strong>75%</strong> · Thumos (Spirit) <strong>18%</strong> · Epithumia: <span class="R" id="r2" data-zh="r2z">7% — remarkably suppressed</span>.</p>
  <p class="para-zh">柏拉图三分灵魂：理性（Logos）<strong>75%</strong> · 激情（Thumos）<strong>18%</strong> · 欲望（Epithumia）<span class="R" id="r2z" data-en="r2">7% — 显著压制</span>。</p>

  <p class="para">Peak activity: <span class="circled">21:00–02:00 CST<svg class="c-svg" viewBox="0 0 158 26"><ellipse cx="79" cy="13" rx="75" ry="12"/></svg></span>. Every message carries purpose, background, or conclusion requirement. Near-zero idle messaging.</p>
  <p class="para-zh">峰值活跃：<span class="circled">21:00–02:00（北京时间）<svg class="c-svg" viewBox="0 0 198 26"><ellipse cx="99" cy="13" rx="95" ry="12"/></svg></span>。每条消息必带目的、背景或结论要求。几乎无闲聊。</p>

  <p class="para">Decisional signature: full position exit at <span class="ul-hw ul-red">−20% drawdown</span> without hesitation. <span class="R" id="r3" data-zh="r3z">Loss aversion resolved. Execution discipline: confirmed.</span></p>
  <p class="para-zh">决策特征：在<span class="ul-hw ul-red">−20%回撤</span>时毫不犹豫完全清仓。<span class="R" id="r3z" data-en="r3">损失厌恶已解决，执行纪律：已确认。</span></p>

  <div class="section-title">III. Topic Distribution &nbsp;<span style="font-weight:400;letter-spacing:1px">三、话题分布</span></div>
  <div style="margin:8px 0 16px;padding-left:10px">
    <div style="display:flex;align-items:center;gap:12px;margin:5px 0;font-size:12.5px">
      <span style="width:160px;color:#3a2d0a">AI / LLM Research</span>
      <div style="flex:1;height:7px;background:rgba(0,0,0,.12);border-radius:2px"><div style="height:100%;width:43%;background:#8b1a1a;border-radius:2px"></div></div>
      <span style="width:32px;color:#6b5a2a;text-align:right">43%</span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;margin:5px 0;font-size:12.5px">
      <span style="width:160px;color:#3a2d0a">Investment Strategy</span>
      <div style="flex:1;height:7px;background:rgba(0,0,0,.12);border-radius:2px"><div style="height:100%;width:22%;background:#6b3a3a;border-radius:2px"></div></div>
      <span style="width:32px;color:#6b5a2a;text-align:right">22%</span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;margin:5px 0;font-size:12.5px">
      <span style="width:160px;color:#3a2d0a">Engineering / Tools</span>
      <div style="flex:1;height:7px;background:rgba(0,0,0,.12);border-radius:2px"><div style="height:100%;width:18%;background:#8b5a5a;border-radius:2px"></div></div>
      <span style="width:32px;color:#6b5a2a;text-align:right">18%</span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;margin:5px 0;font-size:12.5px">
      <span style="width:160px;color:#3a2d0a">Literature / Philosophy</span>
      <div style="flex:1;height:7px;background:rgba(0,0,0,.12);border-radius:2px"><div style="height:100%;width:13%;background:#b08080;border-radius:2px"></div></div>
      <span style="width:32px;color:#6b5a2a;text-align:right">13%</span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;margin:5px 0;font-size:12.5px">
      <span style="width:160px;color:#3a2d0a">Other</span>
      <div style="flex:1;height:7px;background:rgba(0,0,0,.12);border-radius:2px"><div style="height:100%;width:4%;background:#ccc;border-radius:2px"></div></div>
      <span style="width:32px;color:#6b5a2a;text-align:right">4%</span>
    </div>
  </div>
  <p class="para">High-frequency keywords: <span class="ul-hw">Agent</span> · <span class="ul-hw">PE/Prompt</span> · <span class="ul-hw">Tagging</span> · <span class="R" id="r4" data-zh="r4z">止损 · 仓位 · 五段式结构 · 断点续传</span>.</p>
  <p class="para-zh">高频关键词：<span class="ul-hw">Agent/智能体</span> · <span class="ul-hw">PE/Prompt工程</span> · <span class="ul-hw">Tagging/标注</span> · <span class="R" id="r4z" data-en="r4">止损 · 仓位 · 五段式 · 断点续传</span>。</p>

  <div class="footer">
    <div>Alice·V · Delphic Systems<br><span style="font-size:10px">Behavioral Modeling Division · 行为建模部</span></div>
    <div class="stamp-footer">RESTRICTED</div>
    <div style="text-align:right">REF: DS-2026-04-15-001<br><span style="font-size:10px">CONTINUED ON PAGE 2</span></div>
  </div>
</div>

<div class="divider">— Page Break · DS-PN-2026-DANGSI · Page 2 of 2 —</div>

<!-- ══ PAGE 2 ══ -->
<div class="page" style="transform:rotate(.2deg)">
  <div class="stamp" style="color:rgba(15,90,15,.8);border-color:rgba(15,90,15,.8);transform:rotate(6deg)">FOR SUBJECT</div>
  <div class="watermark">PERSONA</div>
  <div class="margin-note" style="top:250px">CONTINUED FROM P.1 · ALICE·V</div>
  <div class="doc-header">
    <div>
      <div class="doc-sub">Capability Assessment &amp; Risk Factors · 能力评估与风险因素</div>
      <div class="doc-title">Operational Profile<br><span style="font-size:14px;letter-spacing:2px">行动画像</span></div>
    </div>
    <div class="doc-stamp">DS-PN-2026-DANGSI<br>PAGE 2 OF 2</div>
  </div>

  <div class="section-title">IV. Capability Assessment &nbsp;<span style="font-weight:400;letter-spacing:1px">四、综合能力评估</span></div>
  <p class="para">Scores /10, based on behavioral evidence from 21 sessions.</p>
  <table class="score-table">
    <tr><td class="s-label">Systems Thinking</td><td class="s-zh">框架思维</td><td><div class="score-bar-bg"><div class="score-bar-fill" style="width:90%"></div></div></td><td class="score-num">9.0</td></tr>
    <tr><td class="s-label">AI Engineering</td><td class="s-zh">AI工程深度</td><td><div class="score-bar-bg"><div class="score-bar-fill" style="width:85%"></div></div></td><td class="score-num">8.5</td></tr>
    <tr><td class="s-label">Literary Output</td><td class="s-zh">文学表达</td><td><div class="score-bar-bg"><div class="score-bar-fill" style="width:85%;background:#6b3a3a"></div></div></td><td class="score-num">8.5</td></tr>
    <tr><td class="s-label">System Architecture</td><td class="s-zh">系统架构</td><td><div class="score-bar-bg"><div class="score-bar-fill" style="width:80%;background:#7a4a4a"></div></div></td><td class="score-num">8.0</td></tr>
    <tr><td class="s-label">Financial Cognition</td><td class="s-zh">金融投资</td><td><div class="score-bar-bg"><div class="score-bar-fill" style="width:75%;background:#8b5a5a"></div></div></td><td class="score-num">7.5</td></tr>
    <tr><td class="s-label">Exec. Discipline</td><td class="s-zh">执行纪律</td><td><div class="score-bar-bg"><div class="score-bar-fill" style="width:65%;background:#a07070"></div></div></td><td class="score-num">6.5</td></tr>
    <tr><td class="s-label">Social Decoding</td><td class="s-zh">社交信号解读</td><td><div class="score-bar-bg"><div class="score-bar-fill" style="width:55%;background:#b08080"></div></div></td><td class="score-num">5.5</td></tr>
  </table>

  <div class="section-title">V. Cognitive Vulnerabilities &nbsp;<span style="font-weight:400;letter-spacing:1px">五、认知盲区</span></div>
  <p class="para"><span class="circled"><strong>Vuln-1: Perfectionism Paralysis</strong><svg class="c-svg" viewBox="0 0 265 26"><ellipse cx="132" cy="13" rx="128" ry="12"/></svg></span> — High internal standards create execution latency. <span class="R" id="r5" data-zh="r5z">Est. creative project completion rate: &lt;30%.</span></p>
  <p class="para-zh"><span class="circled"><strong>漏洞一：完美主义瘫痪</strong><svg class="c-svg" viewBox="0 0 148 26"><ellipse cx="74" cy="13" rx="70" ry="12"/></svg></span> — 极高的内部标准导致执行延迟。<span class="R" id="r5z" data-en="r5">创意项目估计完成率：低于30%。</span></p>

  <p class="para"><strong>Vuln-2: Social Signal Over-Processing</strong> — Allocates <span class="ul-hw ul-red">disproportionate bandwidth to ambiguous cues</span>. <span class="R" id="r6" data-zh="r6z">Anxious-avoidant overlay. Emotionally costly.</span></p>
  <p class="para-zh"><strong>漏洞二：社交信号过度解读</strong> — <span class="ul-hw ul-red">不成比例的分析带宽</span>用于模糊社交线索。<span class="R" id="r6z" data-en="r6">焦虑-回避型叠加，情感成本较高。</span></p>

  <p class="para"><strong>Vuln-3: Cognition–Execution Imbalance</strong> — Thinking:Doing ≈ <span class="circled"><strong>4:1</strong><svg class="c-svg" viewBox="0 0 42 26"><ellipse cx="21" cy="13" rx="18" ry="12"/></svg></span>. Conceptual velocity outpaces <span class="ul-hw">implementation velocity</span>.</p>
  <p class="para-zh"><strong>漏洞三：认知-执行失衡</strong> — 思考:行动 ≈ <span class="circled"><strong>4:1</strong><svg class="c-svg" viewBox="0 0 42 26"><ellipse cx="21" cy="13" rx="18" ry="12"/></svg></span>。概念速度显著超过<span class="ul-hw">实施速度</span>。</p>

  <div class="section-title">VI. Strategic Trajectory &nbsp;<span style="font-weight:400;letter-spacing:1px">六、战略轨迹</span></div>
  <p class="para">Position: convergence of <span class="ul-hw">AI infrastructure · financial modeling · strategic communication</span>. Career vector: <span class="circled"><strong>PE Engineer → Agent Strategy Architect</strong><svg class="c-svg" viewBox="0 0 338 26"><ellipse cx="169" cy="13" rx="165" ry="12"/></svg></span>. Growth potential: <span class="R" id="r7" data-zh="r7z">★★★★★ 5/5 — Re-evaluate in 90 days.</span></p>
  <p class="para-zh">处于 AI基础设施·金融建模·战略传播 交汇处。职业向量：<span class="circled"><strong>PE工程师 → Agent策略架构师</strong><svg class="c-svg" viewBox="0 0 250 26"><ellipse cx="125" cy="13" rx="121" ry="12"/></svg></span>。成长潜力：<span class="R" id="r7z" data-en="r7">★★★★★ 5/5 — 90天后重新评估。</span></p>

  <p class="para"><span class="ul-hw ul-red">Primary risk</span>: not external competition — <span class="R" id="r8" data-zh="r8z">internal execution drag + unresolved tension between desire for recognition and avoidance of exposure.</span></p>
  <p class="para-zh"><span class="ul-hw ul-red">主要风险</span>：不是外部竞争——<span class="R" id="r8z" data-en="r8">内部执行阻力 + 渴望认可与回避曝光之间未解决的张力。</span></p>

  <div class="section-title">VII. Analyst's Note &nbsp;<span style="font-weight:400;letter-spacing:1px">七、分析员备注</span></div>
  <p class="para" style="font-style:italic">Subject is aware they are being analyzed. Cooperation is implicit. <span class="R" id="r9" data-zh="r9z">Self-awareness accelerates modeling. Recommend continued active collaboration.</span></p>
  <p class="para-zh" style="font-style:italic">受试者知晓自己正在被分析。<span class="R" id="r9z" data-en="r9">自我意识加速建模过程，建议持续主动合作。</span></p>

  <p class="para">Final classification: <span class="circled"><strong>理性执政官 · The Rational Archon</strong><svg class="c-svg" viewBox="0 0 312 26"><ellipse cx="156" cy="13" rx="152" ry="12"/></svg></span>. Operates best <span class="ul-hw">when given clear constraints and full autonomy within them</span>.</p>
  <p class="para-zh">最终分类：<span class="circled"><strong>理性执政官 · The Rational Archon</strong><svg class="c-svg" viewBox="0 0 280 26"><ellipse cx="140" cy="13" rx="136" ry="12"/></svg></span>。在<span class="ul-hw">给定明确约束和约束内完全自主权</span>时表现最佳。</p>

  <div class="footer">
    <div>Alice·V · Delphic Systems<br><span style="font-size:10px">2026-04-15</span></div>
    <div class="stamp-footer">FOR SUBJECT ONLY</div>
    <div style="text-align:right;font-size:10px">DS-PN-2026-DANGSI<br>END OF FILE · 档案终止</div>
  </div>
</div>

<div style="color:#444;font-size:10px;letter-spacing:3px;margin-top:8px;text-align:center">
  DS-PN-2026-DANGSI · DELPHIC SYSTEMS · 2026
</div>

<script>
// ══ 倒计时 + 真实销毁 ══
const EXPIRE_AT  = {EXPIRE_MS};
const DEST_FILE  = '{FILENAME}';
const DEST_TOKEN = '{TOKEN}';
const SERVER     = '{SERVER}';

function fmt(ms) {{
  if (ms <= 0) return '00:00:00';
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
}}

function showDestroyed() {{
  document.body.innerHTML =
    '<div style="min-height:100vh;background:#080602;display:flex;flex-direction:column;' +
    'align-items:center;justify-content:center;font-family:Courier New,monospace;' +
    'color:#c0140e;text-align:center;gap:28px;padding:40px">' +
    '<div style="font-size:48px;letter-spacing:8px;border:3px solid #c0140e;padding:14px 40px">FILE DESTROYED</div>' +
    '<div style="font-size:12px;letter-spacing:4px;color:#3a1a1a">DS-PN-2026-DANGSI</div>' +
    '<div style="font-size:11px;color:#2a1412;letter-spacing:2px;line-height:2.4">' +
    'THIS FILE HAS BEEN PERMANENTLY DELETED<br>\u6b64\u6863\u6848\u5df2\u88ab\u6c38\u4e45\u5220\u9664<br>' +
    new Date().toLocaleString('zh-CN') + '</div></div>';
}}

async function callAPI() {{
  try {{
    const r = await fetch(SERVER + '/api/destruct', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{file: DEST_FILE, token: DEST_TOKEN}})
    }});
    return (await r.json()).ok;
  }} catch(e) {{ return false; }}
}}

async function destruct() {{
  showDestroyed();
  await callAPI();
}}

async function earlyDestruct() {{
  if (!confirm('\u786e\u8ba4\u7acb\u5373\u9500\u6bc1\u6b64\u6863\u6848\uff1f\u670d\u52a1\u7aef\u6587\u4ef6\u5c06\u540c\u6b65\u5220\u9664\u3002')) return;
  await destruct();
}}

function tick() {{
  const left = EXPIRE_AT - Date.now();
  const el = document.getElementById('cd-display');
  const sub = document.getElementById('cd-sub');
  if (!el) return;
  if (left <= 0) {{ destruct(); return; }}
  el.textContent = fmt(left);
  if (left < 3600000) {{
    el.classList.add('warn');
    if (sub) sub.textContent = '\u2620 EXPIRING SOON \u00b7 \u5373\u5c06\u9500\u6bc1';
  }}
}}
setInterval(tick, 1000);
tick();

// ══ 预设涂黑点击（英中联动）══
document.querySelectorAll('.R').forEach(el => {{
  el.addEventListener('click', () => {{
    const on = !el.classList.contains('open');
    el.classList.toggle('open', on);
    // 联动对应中/英文
    const peerId = el.dataset.zh || el.dataset.en;
    if (peerId) {{
      const peer = document.getElementById(peerId);
      if (peer) peer.classList.toggle('open', on);
    }}
  }});
}});

// ══ 框选自定义涂黑 ══
let redactOn = false;
const stack = [];

function toggleRedact() {{
  redactOn = !redactOn;
  const btn = document.getElementById('rbtn');
  btn.textContent = redactOn ? '\u2702 \u6846\u9009\u9012\u9ed1\uff1a\u5f00' : '\u2702 \u6846\u9009\u9012\u9ed1\uff1a\u5173';
  btn.classList.toggle('on', redactOn);
  document.body.style.cursor = redactOn ? 'crosshair' : '';
}}

document.addEventListener('mouseup', () => {{
  if (!redactOn) return;
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !sel.toString().trim()) return;
  try {{
    const range = sel.getRangeAt(0);
    const span  = document.createElement('span');
    span.style.cssText = 'display:inline;background:#1a1407;color:#1a1407;cursor:pointer;padding:1px 3px;border-radius:1px;transition:background .15s,color .15s';
    span.title = '\u70b9\u51fb\u89e3\u5bc6';
    span.addEventListener('click', () => {{
      const on = span.style.background !== 'rgb(255, 245, 214)';
      span.style.background   = on ? '#fff5d6' : '#1a1407';
      span.style.color        = on ? '#8b1a1a' : '#1a1407';
      span.style.borderBottom = on ? '1px dashed #8b1a1a' : '';
    }});
    range.surroundContents(span);
    stack.push(span);
    sel.removeAllRanges();
  }} catch(e) {{ window.getSelection()?.removeAllRanges(); }}
}});

function undoRedact() {{
  if (!stack.length) return;
  const span = stack.pop();
  const p = span.parentNode;
  if (!p) return;
  while (span.firstChild) p.insertBefore(span.firstChild, span);
  p.removeChild(span);
}}

function saveHTML() {{
  if (redactOn) toggleRedact();
  const blob = new Blob(['<!DOCTYPE html>' + document.documentElement.outerHTML], {{type:'text/html'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'DS-PN-2026-DANGSI.html';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}}
</script>
</body>
</html>"""

out = '/tmp/persona-dangsi-final.html'
with open(out, 'w') as f:
    f.write(HTML)
print(f"OK {len(HTML):,} bytes")
