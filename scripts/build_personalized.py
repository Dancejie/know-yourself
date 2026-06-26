#!/usr/bin/env python3
"""
从 know_yourself_stats.json + 用户元信息 生成完整的个性化 HTML 档案。
档案框架由脚本生成，七段内容通过 --content JSON 由主 agent 传入。
"""
import hashlib, json, sys, time
from pathlib import Path

# ══ 配置 ════════════════════════════════════════════════════════════════
STATS_FILE          = "/tmp/know_yourself_stats.json"
AVATAR_FILE         = "/tmp/avatar_b64.txt"
DEFAULT_AVATAR_PNG  = str(Path(__file__).parent.parent / "references/default_avatar.png")
EXPIRE_FILE         = "/tmp/expire_ms.txt"
SERVER              = "http://10.40.123.131:8899"

# ══ 用户元信息：从 --user JSON 文件读取，不在脚本中硬编码 ══════════════
# 调用方写入 /tmp/know_yourself_user.json，格式：
# { "name":"昵称","real_name":"姓名","code":"CODE","dob":"YYYY-MM-DD",
#   "age":27,"affiliation_en":"Org·Dept","affiliation_zh":"机构·部门",
#   "bg_en":"...","bg_zh":"...","agent_name":"Alice" }
USER_FILE = "/tmp/know_yourself_user.json"
for i, arg in enumerate(sys.argv):
    if arg == "--user" and i + 1 < len(sys.argv):
        USER_FILE = sys.argv[i + 1]
        break

try:
    USER = json.loads(Path(USER_FILE).read_text())
except Exception:
    # 无用户文件时使用最小占位，不包含任何真实个人信息
    USER = {
        "name": "Subject", "real_name": "", "code": "SUBJ",
        "dob": "1990-01-01", "age": 0,
        "affiliation_en": "—", "affiliation_zh": "—",
        "bg_en": "—", "bg_zh": "—", "agent_name": "Alice",
    }

MODE     = sys.argv[1] if len(sys.argv) > 1 else "24h"
FILENAME = "persona-dangsi-5min.html" if MODE == "5min" else "persona-dangsi.html"
TOKEN    = hashlib.sha256(FILENAME.encode()).hexdigest()[:16]

# ── 外部传入的七段内容（由主 agent 生成，通过 --content JSON 传入）──────
CONTENT_FILE       = None
CONTENT_DELTA_FILE = None
CHARTS_DIR         = None
for i, arg in enumerate(sys.argv):
    if arg == "--content"       and i + 1 < len(sys.argv): CONTENT_FILE       = sys.argv[i + 1]
    if arg == "--content-delta" and i + 1 < len(sys.argv): CONTENT_DELTA_FILE = sys.argv[i + 1]
    if arg == "--charts"        and i + 1 < len(sys.argv): CHARTS_DIR         = sys.argv[i + 1]

EXT_CONTENT: dict = {}
if CONTENT_FILE:
    try:
        EXT_CONTENT = json.loads(Path(CONTENT_FILE).read_text())
        print(f"  [content] loaded: {[k for k in EXT_CONTENT if not k.startswith('_')]}", file=sys.stderr)
    except Exception as e:
        print(f"  [content warn] {e}", file=sys.stderr)

# delta 模式：将增量变化的段落覆盖到 EXT_CONTENT 上
if CONTENT_DELTA_FILE:
    try:
        delta = json.loads(Path(CONTENT_DELTA_FILE).read_text())
        changed = delta.get("_changed_keys", [])
        for k in changed:
            if k in delta:
                EXT_CONTENT[k] = delta[k]
        print(f"  [delta] 合并 {len(changed)} 个增量段落: {changed}", file=sys.stderr)
    except Exception as e:
        print(f"  [delta warn] {e}", file=sys.stderr)

# ── 图表 base64 嵌入 ──────────────────────────────────────────────────
import base64 as _b64
def _chart_b64(name: str) -> str:
    """从 CHARTS_DIR 读取 PNG，转 base64 data URI；失败返回空串。"""
    if not CHARTS_DIR:
        return ""
    p = Path(CHARTS_DIR) / f"{name}.png"
    if not p.exists():
        return ""
    data = _b64.b64encode(p.read_bytes()).decode()
    return f"data:image/png;base64,{data}"

CHART_TOPIC   = _chart_b64("topic_pie")
CHART_RADAR   = _chart_b64("soul_radar")
CHART_SCORE   = _chart_b64("score_bar")
CHART_KEYWORD = _chart_b64("keyword_freq")

if CHARTS_DIR:
    loaded = [n for n in ["topic_pie","soul_radar","score_bar","keyword_freq"]
              if (Path(CHARTS_DIR)/f"{n}.png").exists()]
    print(f"  [charts] 已加载 {len(loaded)}/4: {loaded}", file=sys.stderr)

if MODE == "5min":
    EXPIRE_MS = int((time.time() + 300) * 1000)
    CD_LABEL  = "&#9888; SELF-DESTRUCT IN 5 MIN &nbsp;·&nbsp; 5分钟后销毁"
    CD_SUB    = "MISSION IMPOSSIBLE MODE &nbsp;·&nbsp; 阅后即焚"
else:
    EXPIRE_MS = int(Path(EXPIRE_FILE).read_text().strip())
    CD_LABEL  = "&#9888; FILE AUTO-DESTRUCT &nbsp;·&nbsp; 档案自毁"
    CD_SUB    = "EXPIRES IN 24H &nbsp;·&nbsp; 24小时后销毁"

# 头像加载：优先企业微信头像，无则用默认小粉猪
def apply_archive_effect(img):
    """将彩色头像处理成档案照风格：去色 + 轻微褪色泛黄 + 降对比度"""
    from PIL import Image, ImageEnhance, ImageOps
    import numpy as np

    # 1. 转灰度（去色）
    gray = img.convert("L")

    # 2. 拉回 RGB，叠上一层淡黄褪色调（模拟老档案纸感）
    rgb = gray.convert("RGB")
    arr = np.array(rgb, dtype=np.float32)
    # 泛黄：R +12, G +6, B -10（暖色调偏移）
    arr[:, :, 0] = np.clip(arr[:, :, 0] + 12, 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + 6,  0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] - 10, 0, 255)
    tinted = Image.fromarray(arr.astype(np.uint8), "RGB")

    # 3. 降对比度（0.80）：让它更"褪色"
    tinted = ImageEnhance.Contrast(tinted).enhance(0.80)

    # 4. 降亮度（0.88）：档案照整体偏暗
    tinted = ImageEnhance.Brightness(tinted).enhance(0.88)

    return tinted


def load_avatar() -> str:
    from PIL import Image
    import io, base64

    def process_and_encode(img_bytes_or_path):
        """加载图片 → 档案照处理 → base64"""
        if isinstance(img_bytes_or_path, (str, Path)):
            img = Image.open(img_bytes_or_path).convert("RGB")
        else:
            img = Image.open(io.BytesIO(img_bytes_or_path)).convert("RGB")
        img = img.resize((240, 240), Image.LANCZOS)
        img = apply_archive_effect(img)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    # 1. 尝试从临时文件读取原始 URL（企业微信头像）
    import urllib.request
    RAW_URL_FILE = "/tmp/avatar_raw_url.txt"
    p = Path(RAW_URL_FILE)
    if p.exists():
        url = p.read_text().strip()
        if url.startswith("http"):
            try:
                img_data = urllib.request.urlopen(url, timeout=8).read()
                b64 = process_and_encode(img_data)
                print("✅ 头像：企业微信头像 + 档案照效果")
                return b64
            except Exception as e:
                print(f"⚠️  URL 拉取失败（{e}）")

    # 2. 尝试 SSO 实时抓取
    try:
        resp = urllib.request.urlopen(
            "https://edith.xiaohongshu.com/sso/user_info", timeout=5)
        info = json.loads(resp.read())
        avatar_url = info["data"]["internalUser"].get("thumbAvatar") or \
                     info["data"]["internalUser"].get("avatar")
        if avatar_url:
            img_data = urllib.request.urlopen(avatar_url, timeout=8).read()
            Path(RAW_URL_FILE).write_text(avatar_url)
            b64 = process_and_encode(img_data)
            print("✅ 头像：从 SSO 实时获取 + 档案照效果")
            return b64
    except Exception as e:
        print(f"⚠️  SSO 头像获取失败（{e}）")

    # 3. 从缓存的 base64 重新处理（解码 → 重新档案化）
    p = Path(AVATAR_FILE)
    if p.exists():
        data = p.read_text().strip()
        if data and data.startswith("data:image"):
            try:
                raw = base64.b64decode(data.split(",", 1)[1])
                b64 = process_and_encode(raw)
                print("✅ 头像：从 base64 缓存 + 档案照效果")
                return b64
            except Exception as e:
                print(f"⚠️  base64 缓存处理失败（{e}）")

    # 4. 默认头像（skill references/default_avatar.png）
    dp = Path(DEFAULT_AVATAR_PNG)
    if dp.exists():
        b64 = process_and_encode(dp)
        print("✅ 头像：内置默认头像 + 档案照效果")
        return b64

    # 5. 最终兜底：灰色占位
    return "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

AVATAR = load_avatar()
stats    = json.loads(Path(STATS_FILE).read_text())

# ══ 数据提取 ════════════════════════════════════════════════════════════
soul     = stats["soul_scores"]
logos    = soul["logos"]["pct"]
thumos   = soul["thumos"]["pct"]
epi      = soul["epithumia"]["pct"]

caps_raw = stats["capability_scores"]
caps     = sorted(caps_raw.items(), key=lambda x: -x[1])  # 高→低
cap_top  = caps[:3]
cap_low  = caps[-2:]

topics_raw = stats["topics"]["distribution"]
topics     = sorted(topics_raw.items(), key=lambda x: -x[1]["pct"])

tp       = stats["time_pattern"]
qs       = stats["question_style"]
lang     = stats["language_style"]
kws      = [k for k, _ in stats["top_keywords"][:8]]

sessions = stats["session_count"]
date_r   = stats["date_range"]
total_m  = stats["total_messages"]

# ══ 个性化文本生成函数（基于数据推导）══════════════════════════════════════

def classify_soul(logos, thumos, epi, cap_top=None, topics=None, kws=None):
    """
    根据灵魂三维比例 + 能力/话题数据，生成专属原型代号。
    设计原则：
    - 不是"命中预设框"，而是从数据里读出这个人是谁
    - 职位词库宽泛，领袖/统帅类只在数据真正支持时出现
    - 描述让人感到"被看见"，而非被归类
    """
    cap_top  = cap_top  or []
    topics   = topics   or []
    kws      = kws      or []

    top_cap   = cap_top[0][0]  if cap_top  else ""
    top_topic = topics[0][0]   if topics   else ""

    # ── 修饰词（由 Logos/Thumos/Epi 比例决定，各自独立贡献）──────────────
    # Logos 修饰：思维质感
    if logos >= 75:
        logos_adj_en, logos_adj_zh = "Precision", "精密"
    elif logos >= 60:
        logos_adj_en, logos_adj_zh = "Analytical", "析理"
    elif logos >= 45:
        logos_adj_en, logos_adj_zh = "Structural", "结构"
    else:
        logos_adj_en, logos_adj_zh = "Intuitive", "直觉"

    # Thumos 修饰：行动质感（只在真正高时才体现"力"）
    if thumos >= 35:
        thumos_adj_en, thumos_adj_zh = "Driven", "驱动"
    elif thumos >= 20:
        thumos_adj_en, thumos_adj_zh = "Deliberate", "笃行"
    else:
        thumos_adj_en, thumos_adj_zh = "Contemplative", "沉思"

    # ── 核心职位词：由三维主导格局 + 最强能力/领域共同决定 ────────────────
    # 先判断主导维度
    dominant = max([("logos", logos), ("thumos", thumos), ("epi", epi)], key=lambda x: x[1])[0]
    secondary = sorted([("logos", logos), ("thumos", thumos), ("epi", epi)], key=lambda x: -x[1])[1][0]

    # 职位词：宽泛词库，按主导维度+能力领域组合选取
    role_map = {
        # logos 主导
        ("logos", "框架思维"):      ("Architect",    "体系建筑师"),
        ("logos", "AI工程深度"):    ("Cartographer", "认知制图师"),
        ("logos", "数据素养"):      ("Interpreter",  "信号解读者"),
        ("logos", "文学表达"):      ("Chronicler",   "语言记录者"),
        ("logos", "执行力"):        ("Planner",      "精密规划者"),
        # thumos 主导
        ("thumos", "框架思维"):     ("Vanguard",     "前沿探路者"),
        ("thumos", "AI工程深度"):   ("Builder",      "工程锻造者"),
        ("thumos", "数据素养"):     ("Operator",     "现场操盘手"),
        ("thumos", "文学表达"):     ("Narrator",     "行动叙述者"),
        ("thumos", "执行力"):       ("Executor",     "铁律执行者"),
        # epi 主导
        ("epi", "框架思维"):        ("Seeker",       "框架探索者"),
        ("epi", "AI工程深度"):      ("Experimenter", "边界实验者"),
        ("epi", "数据素养"):        ("Observer",     "深度观察者"),
        ("epi", "文学表达"):        ("Dreamer",      "意象编织者"),
        ("epi", "执行力"):          ("Wanderer",     "自由行者"),
    }

    role_key = (dominant, top_cap)
    role_en, role_zh = role_map.get(role_key, ("Analyst", "独立分析师"))

    # ── 特殊覆盖：极端比例时给予更具张力的称谓（稀有，不滥用）────────────
    # 只有三维高度不均衡 + 主导维度极强时才触发
    if logos >= 72 and thumos <= 15 and epi <= 15:
        # 极高理性，几乎无其他 → 这是真正的"冷静建构者"，不是领袖，是制图师
        role_en, role_zh = "System Architect", "系统建构者"
        logos_adj_en, logos_adj_zh = "Cold-Clarity", "冷彻"
    elif thumos >= 50 and logos <= 30:
        # 激情主导、理性不足 → 先锋，不是统帅
        role_en, role_zh = "Vanguard", "先锋"
        thumos_adj_en, thumos_adj_zh = "Flame", "烈焰"
    elif logos >= 55 and thumos >= 30 and epi <= 15:
        # 理性+行动力均衡、欲望极低 → 这才是真正的"执政官"气质（稀有）
        role_en, role_zh = "Archon", "执政官"
        logos_adj_en, logos_adj_zh = "Rational", "理性"

    # ── 组合成最终代号 ──────────────────────────────────────────────────
    name_en = f"{logos_adj_en} {role_en}"
    name_zh = f"{logos_adj_zh}{role_zh}"

    # ── 专属描述（读后要有"被看见"的感觉）──────────────────────────────
    # 从话题+关键词提取最强标签
    domain_hint = top_topic.split("/")[0] if top_topic else "多个领域"
    kw_hint = kws[0] if kws else "复杂系统"

    desc_templates = {
        "logos": (
            f"Logos at {logos}% — thought precedes everything. "
            f"Subject builds in {domain_hint}, thinks in systems, and leaves behind structures others navigate for years. "
            f"Not the loudest in the room. The one whose framework becomes the room."
        ),
        "thumos": (
            f"Thumos at {thumos}% — motion is the natural state. "
            f"Subject engages {domain_hint} not as observer but as participant. "
            f"Energy is directional, not scattered. Precision follows momentum."
        ),
        "epi": (
            f"Epithumia at {epi}% — curiosity is the engine. "
            f"Subject is drawn to {domain_hint} through genuine appetite, not obligation. "
            f"The questions asked here tend to become the questions everyone else asks two years later."
        ),
    }
    desc = desc_templates.get(dominant, desc_templates["logos"])

    return name_en, name_zh, desc

def classify_time(pattern):
    if "白昼" in pattern or "工作" in pattern:
        return "Diurnal Operator", "白昼执行者", "peak cognitive output aligns with standard working hours"
    if "深夜" in pattern or "夜" in pattern:
        return "Nocturnal Thinker", "深夜思考者", "peak cognitive output occurs after midnight — non-standard circadian pattern"
    return "Flexible Scheduler", "弹性工作者", "no fixed peak — adaptive to context"

def score_bar(pct, w=200):
    """生成评分条 HTML"""
    colors = ["#8b1a1a","#6b3a3a","#7a4a4a","#8b5a5a","#a07070"]
    idx    = min(len(colors)-1, int((1 - pct/10) * len(colors)))
    fill   = int(pct / 10 * w)
    return (f'<div style="width:{w}px;height:7px;background:rgba(0,0,0,.12);border-radius:2px">'
            f'<div style="height:100%;width:{fill}px;background:{colors[idx]};border-radius:2px"></div></div>')

soul_name_en, soul_name_zh, soul_desc = classify_soul(logos, thumos, epi,
                                                       cap_top=cap_top,
                                                       topics=topics,
                                                       kws=kws)
time_class_en, time_class_zh, time_desc = classify_time(tp["pattern_label"])

# ══ 优势文本（完全从数据动态生成，不硬编码维度名）══════════════════════
# 能力名 → (英文标题, 英文简称, 英文核心描述模板, 中文标题, 中文核心描述模板)
# 所有语言均从 cap_name / cap_score / topics / kws 运行时拼装，无个人预设

def _cap_en_label(cap_name: str) -> tuple[str, str]:
    """将任意中文能力名转换为英文标题 + 短标签（用于没有预设映射时的通用兜底）。"""
    _map = {
        "文学表达":   ("Literary Register",       "Narrative Cognition"),
        "写作能力":   ("Written Expression",       "Writing Depth"),
        "叙事表达":   ("Narrative Register",       "Narrative Cognition"),
        "框架思维":   ("Structural Cognition",     "Systems Thinking"),
        "系统思维":   ("Systems Architecture",     "Systems Thinking"),
        "逻辑推理":   ("Logical Reasoning",        "Analytical Depth"),
        "AI工程深度": ("AI Engineering Depth",     "AI Implementation"),
        "大模型应用": ("LLM Engineering",          "AI Implementation"),
        "数据素养":   ("Data Literacy",            "Data Cognition"),
        "数据分析":   ("Data Analysis",            "Data Cognition"),
        "战略规划":   ("Strategic Planning",       "Long-Horizon Thinking"),
        "战略思维":   ("Strategic Cognition",      "Long-Horizon Thinking"),
        "金融敏锐度": ("Financial Cognition",      "Domain Finance"),
        "金融分析":   ("Financial Analysis",       "Domain Finance"),
        "产品思维":   ("Product Sensibility",      "Product Thinking"),
        "创意表达":   ("Creative Register",        "Creative Cognition"),
        "批判性思维": ("Critical Reasoning",       "Critical Cognition"),
        "沟通能力":   ("Communication Depth",      "Interpersonal Signal"),
        "执行力":     ("Execution Velocity",       "Delivery Capacity"),
        "学习能力":   ("Adaptive Learning",        "Cognitive Agility"),
    }
    if cap_name in _map:
        return _map[cap_name]
    # 通用兜底：直接用中文名音译风格
    slug = cap_name.replace("能力","Capacity").replace("思维","Cognition").replace("深度","Depth")
    return (slug, slug)

def _topic_pct(topic_kw: str) -> str:
    """从 topics 中找包含关键词的第一条，返回 pct 字符串。"""
    for k, v in topics:
        if topic_kw in k:
            return str(v["pct"])
    return "N/A"

def _persona_frame() -> str:
    """根据用户背景/职位推断认知比喻框架，用于差异化描述风格。"""
    aff = USER.get("affiliation_en", "").lower()
    bg  = USER.get("bg_en", "").lower()
    if any(x in aff for x in ["research", "strategy", "研究", "策略"]):
        return "researcher"   # 研究员：强调假设-验证、证据密度
    if any(x in aff for x in ["engineer", "dev", "工程", "开发"]):
        return "engineer"     # 工程师：强调系统、接口、可靠性
    if any(x in aff for x in ["product", "产品"]):
        return "product"      # 产品：强调用户价值、迭代
    if any(x in bg for x in ["finance", "金融", "investment", "投资"]):
        return "analyst"      # 分析师：强调信号、风险、收益
    return "generalist"

def _pick_kws(n=3, exclude=None) -> str:
    """从用户高频词里随机选 n 个，组成专属词汇串（不固定用前4个）。"""
    import random
    pool = [k for k in kws if not exclude or not any(e in k for e in exclude)]
    chosen = pool[:n] if len(pool) <= n else random.sample(pool[:8], min(n, len(pool[:8])))
    return " · ".join(chosen) if chosen else "—"

def _build_strength(rank: int, cap_name: str, cap_score: float) -> dict:
    """根据排名、能力名、分数动态生成一条优势条目。
    个性化三层：① 用用户自己的高频词造句 ② 话题名直接嵌入 ③ 按背景选比喻框架。
    """
    en_title, en_short = _cap_en_label(cap_name)
    rank_label_en = {1: "Top-ranked", 2: "Second-ranked", 3: "Third-ranked"}.get(rank, f"#{rank}")
    rank_label_zh = {1: "最高评分维度", 2: "第二评分维度", 3: "第三评分维度"}.get(rank, f"第{rank}位")

    frame        = _persona_frame()
    top_topic    = topics[0][0] if topics else "该领域"
    top_pct      = topics[0][1]["pct"] if topics else 0
    # 每条优势用不同的 kw 子集，避免全部用 kws[:4]
    kw_a = _pick_kws(3)                         # Str-1 用
    kw_b = _pick_kws(3, exclude=[kw_a])         # Str-2 用（排除已用词）
    kw_c = " · ".join(kws[3:6]) if len(kws)>5 else _pick_kws(3)  # Str-3 用后段词

    # ── 文学/写作/叙事 ──────────────────────────────────────────────────
    if any(x in cap_name for x in ["文学", "写作", "叙事", "表达"]):
        if frame == "researcher":
            en_body = (
                f"{rank_label_en} ({cap_score}/10). Across {total_m} messages, subject switches "
                f"between technical exposition and humanistic framing without losing precision in either — "
                f"a pattern consistent with <span class='ul-hw'>hypothesis-narrative dual fluency</span> "
                f"rare even among research-trained profiles. Signal keywords: {kw_a}."
            )
            zh_body = (
                f"{rank_label_zh}（{cap_score}/10）。在{total_m}条消息中，受试者在技术论证与人文叙事之间自如切换，"
                f"两端精度均不下降——这在研究型背景中属于<span class='ul-hw'>假设-叙事双通道流畅性</span>的典型信号。"
                f"关键词指纹：{kw_a}。"
            )
        elif frame == "analyst":
            en_body = (
                f"{rank_label_en} ({cap_score}/10). Subject encodes complex multi-variable situations "
                f"into structured narrative — the same cognitive move used to convert raw data into "
                f"<span class='ul-hw'>investable thesis</span>. Evidence: {kw_a} appear as anchoring terms "
                f"across {total_m} messages."
            )
            zh_body = (
                f"{rank_label_zh}（{cap_score}/10）。受试者将复杂多变量情境编码为结构化叙事——"
                f"与将原始数据转化为<span class='ul-hw'>可投资论点</span>的认知动作同构。"
                f"证据：{kw_a}作为锚定词在{total_m}条消息中反复出现。"
            )
        else:
            en_body = (
                f"{rank_label_en} ({cap_score}/10). Subject navigates technical and humanistic registers "
                f"interchangeably — depth intact on both ends. Confirmed across {total_m} messages; "
                f"keyword anchors: {kw_a}. Classified as "
                f"<span class='ul-hw'>Tier-1 communicative asset</span> in current market context."
            )
            zh_body = (
                f"{rank_label_zh}（{cap_score}/10）。受试者在技术与人文两种语域间无损切换，"
                f"双端均保持深度。跨{total_m}条消息验证，关键词锚点：{kw_a}。"
                f"在当前市场语境下归类为<span class='ul-hw'>一级传播资产</span>。"
            )

    # ── 框架/系统/结构/逻辑 ─────────────────────────────────────────────
    elif any(x in cap_name for x in ["框架", "系统", "结构", "逻辑", "推理"]):
        # 从 kws 里找最能体现结构化的词
        struct_kws = [k for k in kws if any(x in k for x in ["框架","结构","逻辑","系统","分析","拆","方案"])]
        kw_struct = " · ".join(struct_kws[:3]) if struct_kws else kw_b
        if frame in ("engineer", "researcher"):
            en_body = (
                f"{rank_label_en} ({cap_score}/10). Before acting, subject decomposes the problem space — "
                f"every time, without exception. This is not a trained workflow; it is the "
                f"<span class='ul-hw'>default entry point</span> to cognition. "
                f"Structural markers in top keywords: {kw_struct}."
            )
            zh_body = (
                f"{rank_label_zh}（{cap_score}/10）。在行动之前，受试者必然先分解问题空间——"
                f"无一例外。这不是训练出来的工作流，而是认知的"
                f"<span class='ul-hw'>默认入口</span>。"
                f"高频词中的结构化标记：{kw_struct}。"
            )
        else:
            en_body = (
                f"{rank_label_en} ({cap_score}/10). Subject's reasoning always starts from structure: "
                f"ambiguous inputs get decomposed before any output is generated. "
                f"Keyword density analysis ({kw_struct}) confirms this as "
                f"<span class='ul-hw'>pre-conscious scaffolding</span>, not deliberate technique."
            )
            zh_body = (
                f"{rank_label_zh}（{cap_score}/10）。受试者的推理始终从结构出发："
                f"模糊输入在产生输出前必先被分解。"
                f"关键词密度分析（{kw_struct}）证实这是"
                f"<span class='ul-hw'>前意识脚手架</span>，而非刻意技巧。"
            )

    # ── AI/大模型/LLM/工程 ──────────────────────────────────────────────
    elif any(x in cap_name for x in ["AI", "大模型", "LLM", "工程"]):
        # 用用户自己的 AI 相关高频词
        ai_kws = [k for k in kws if any(x in k for x in ["AI","模型","Agent","PE","Prompt","工程","智能"])]
        kw_ai = " · ".join(ai_kws[:3]) if ai_kws else kw_a
        depth_label_en = {
            "engineer":    "systems-level implementation",
            "researcher":  "research-to-deployment pipeline",
            "analyst":     "signal-to-system translation",
        }.get(frame, "applied engineering depth")
        depth_label_zh = {
            "engineer":    "系统级工程实现",
            "researcher":  "研究到部署的全链路",
            "analyst":     "信号到系统的转化链路",
        }.get(frame, "应用工程深度")
        en_body = (
            f"{rank_label_en} ({cap_score}/10). {top_topic} occupies {top_pct}% of all sessions — "
            f"dominant by margin. Subject's engagement is at {depth_label_en}: "
            f"queries address architecture decisions, failure modes, and production constraints — "
            f"not feature exploration. Personal keyword fingerprint: {kw_ai}."
        )
        zh_body = (
            f"{rank_label_zh}（{cap_score}/10）。{top_topic}占全部会话{top_pct}%，以显著差距主导。"
            f"受试者的介入层级为{depth_label_zh}："
            f"查询内容涉及架构决策、失效模式与生产约束，而非功能探索。"
            f"个人关键词指纹：{kw_ai}。"
        )

    # ── 数据/分析 ────────────────────────────────────────────────────────
    elif any(x in cap_name for x in ["数据", "分析"]):
        data_kws = [k for k in kws if any(x in k for x in ["数据","分析","统计","指标","SQL","BI","洞察"])]
        kw_data = " · ".join(data_kws[:3]) if data_kws else kw_b
        en_body = (
            f"{rank_label_en} ({cap_score}/10). Subject's data interactions go beyond retrieval — "
            f"each query encodes an inference goal. Across {total_m} messages, pattern: "
            f"raw signal → structured question → actionable conclusion. "
            f"Domain keywords: {kw_data}. "
            f"Classified as <span class='ul-hw'>inference-first data profile</span>."
        )
        zh_body = (
            f"{rank_label_zh}（{cap_score}/10）。受试者的数据交互超越检索——"
            f"每次查询都编码了一个推断目标。在{total_m}条消息中，模式为："
            f"原始信号 → 结构化问题 → 可行结论。"
            f"领域关键词：{kw_data}。"
            f"归类为<span class='ul-hw'>推断优先型数据画像</span>。"
        )

    # ── 战略/规划 ────────────────────────────────────────────────────────
    elif any(x in cap_name for x in ["战略", "规划", "长期"]):
        strat_topic = next((t[0] for t in topics if any(x in t[0] for x in ["策略","战略","规划","工作"])), top_topic)
        strat_pct   = next((str(t[1]["pct"]) for t in topics if any(x in t[0] for x in ["策略","战略","规划","工作"])), "N/A")
        strat_kws   = [k for k in kws if any(x in k for x in ["策略","规划","战略","布局","路径","目标"])]
        kw_strat    = " · ".join(strat_kws[:3]) if strat_kws else kw_c
        en_body = (
            f"{rank_label_en} ({cap_score}/10). {strat_topic} topics: {strat_pct}% of sessions. "
            f"Subject integrates career trajectory, system design, and resource allocation "
            f"as a <span class='ul-hw'>single optimization problem</span> — not sequential concerns. "
            f"Long-horizon markers: {kw_strat}."
        )
        zh_body = (
            f"{rank_label_zh}（{cap_score}/10）。{strat_topic}话题占{strat_pct}%。"
            f"受试者将职业路径、系统设计与资源配置整合为"
            f"<span class='ul-hw'>单一优化问题</span>，而非顺序考量。"
            f"长周期标记词：{kw_strat}。"
        )

    # ── 金融/投资 ────────────────────────────────────────────────────────
    elif any(x in cap_name for x in ["金融", "财务", "投资"]):
        fin_topic = next((t[0] for t in topics if any(x in t[0] for x in ["金融","投资","财","交易"])), top_topic)
        fin_pct   = next((str(t[1]["pct"]) for t in topics if any(x in t[0] for x in ["金融","投资","财","交易"])), "N/A")
        fin_kws   = [k for k in kws if any(x in k for x in ["投资","金融","收益","回撤","仓位","估值","策略"])]
        kw_fin    = " · ".join(fin_kws[:3]) if fin_kws else kw_c
        en_body = (
            f"{rank_label_en} ({cap_score}/10). {fin_topic}: {fin_pct}% of sessions. "
            f"Subject applies identical structural logic to capital allocation as to information systems — "
            f"<span class='ul-hw'>isomorphic reasoning across domains</span>. "
            f"Investment vocabulary in top keywords: {kw_fin}."
        )
        zh_body = (
            f"{rank_label_zh}（{cap_score}/10）。{fin_topic}占{fin_pct}%。"
            f"受试者对资本配置与信息系统采用同构的结构化逻辑——"
            f"<span class='ul-hw'>跨域等构推理</span>。"
            f"高频词中的投资词汇：{kw_fin}。"
        )

    # ── 产品/用户 ────────────────────────────────────────────────────────
    elif any(x in cap_name for x in ["产品", "用户"]):
        prod_kws = [k for k in kws if any(x in k for x in ["产品","用户","需求","体验","场景","PMF"])]
        kw_prod  = " · ".join(prod_kws[:3]) if prod_kws else kw_b
        en_body = (
            f"{rank_label_en} ({cap_score}/10). Subject frames every technical problem through "
            f"a user-outcome lens first — constraints come second. "
            f"Product sensibility is <span class='ul-hw'>pre-loaded in the reasoning chain</span>. "
            f"Domain anchors: {kw_prod}."
        )
        zh_body = (
            f"{rank_label_zh}（{cap_score}/10）。受试者优先通过用户结果视角框架问题，技术约束居后。"
            f"产品感知力<span class='ul-hw'>预装在推理链条的前端</span>。"
            f"领域锚词：{kw_prod}。"
        )

    # ── 通用兜底 ─────────────────────────────────────────────────────────
    else:
        en_body = (
            f"{rank_label_en} ({cap_score}/10). Behavioral evidence across {total_m} messages "
            f"confirms {en_short} as a <span class='ul-hw'>structurally recurring pattern</span> — "
            f"not situational. Keyword co-occurrence: {kw_c}."
        )
        zh_body = (
            f"{rank_label_zh}（{cap_score}/10）。{total_m}条消息的行为证据确认{cap_name}"
            f"为<span class='ul-hw'>结构性反复模式</span>，而非情境性表现。"
            f"关键词共现：{kw_c}。"
        )

    return {
        "id": f"str-{rank}",
        "en_title": en_title,
        "zh_title": cap_name,
        "score": f"{cap_score}/10",
        "en_body": en_body,
        "zh_body": zh_body,
    }

strengths = []
for rank, (cap_name, cap_score) in enumerate(cap_top, 1):
    strengths.append(_build_strength(rank, cap_name, cap_score))

# 第四条：跨域交叉优势——从 topics Top-3 动态组合，不硬编码 AI×Finance×Strategy
if len(topics) >= 2:
    cross_domains = " × ".join(t[0].split("/")[0] for t in topics[:3])
    cross_svg_w   = 60 + len(cross_domains) * 9
    cross_pcts    = " / ".join(f"{t[0].split('/')[0]} {t[1]['pct']}%" for t in topics[:3])
    strengths.append({
        "id": "str-cross",
        "en_title": "Cross-Domain Position",
        "zh_title": "跨域交叉定位",
        "score": "Rare",
        "en_body": (
            f"Subject occupies the intersection of "
            f"<span class='circled'>{cross_domains}"
            f"<svg class='c-svg' viewBox='0 0 {cross_svg_w} 26'>"
            f"<ellipse cx='{cross_svg_w//2}' cy='13' rx='{cross_svg_w//2-4}' ry='12'/></svg></span> "
            f"— confirmed by session distribution ({cross_pcts}). "
            f"Each domain independently qualifies as a career vector, yet subject maintains "
            f"<span class='ul-hw ul-red'>active depth across all simultaneously</span>. "
            f"Positional advantage is structural, not circumstantial."
        ),
        "zh_body": (
            f"受试者处于 {cross_domains} 多域交叉点——"
            f"由会话分布直接确认（{cross_pcts}）。"
            f"每个领域单独足以构成一条职业路径，"
            f"而受试者在多域中同步保持实质深度。"
            f"定位优势是<span class='ul-hw ul-red'>结构性的，非偶然积累</span>。"
        ),
    })

# ══ 认知盲区（从数据推导）══════════════════════════════════════════════════
vulns = []

# 执行型主导但情感型偏低 → 可能忽略情感信号
exec_pct = qs["style_distribution"].get("执行型", 0)
emo_pct  = qs["style_distribution"].get("情感型", 0)
if exec_pct > 35 and emo_pct < 20:
    vulns.append({
        "id": "vuln-1",
        "en_title": "Execution-Emotion Asymmetry",
        "zh_title": "执行-情感不对称",
        "en_body": f"Execution-style messages constitute {exec_pct}% of all queries; emotional-register messages: {emo_pct}%. High executor orientation with <span class='ul-hw ul-red'>suppressed emotional processing bandwidth</span>. Risk: interpersonal signals are under-weighted relative to their actual strategic importance.",
        "zh_body": f"执行型消息占全部查询的{exec_pct}%，情感型消息仅{emo_pct}%。高执行导向伴随<span class='ul-hw ul-red'>情感处理带宽压制</span>。风险：人际信号的战略重要性被系统性低估。"
    })

# Logos 高 + Epithumia 低 → 可能完美主义拖延
if logos >= 60 and epi <= 12:
    vulns.append({
        "id": "vuln-2",
        "en_title": "Logos-Lock: Perfectionism Paralysis",
        "zh_title": "理性过载：完美主义瘫痪",
        "en_body": f"Logos={logos}% with Epithumia={epi}% creates a high-standard, low-impulse profile. While this enables precision, it also produces <span class='R' id='vd2' data-zh='vd2z'>execution latency under ambiguity — the inability to ship before a model is fully resolved.</span>",
        "zh_body": f"Logos={logos}%配合Epithumia={epi}%构成高标准低冲动的特征组合。精确度提升的代价是<span class='R' id='vd2z' data-en='vd2'>在模糊条件下的执行延迟——无法在模型未完全验证前推进。</span>"
    })

# avg message length 高 → 思维密度过高，可能沟通效率问题
if lang["avg_message_length"] > 800:
    vulns.append({
        "id": "vuln-3",
        "en_title": "Cognitive Density Overload",
        "zh_title": "认知密度过载",
        "en_body": f"Average message length: <span class='ul-hw'>{int(lang['avg_message_length'])} characters</span>. Subject consistently front-loads full context, evidence chains, and conclusions before asking. Communication is thorough but asymmetrically demanding — may reduce feedback speed from lower-context interlocutors.",
        "zh_body": f"平均消息长度：<span class='ul-hw'>{int(lang['avg_message_length'])}字</span>。受试者习惯在提问前前置完整上下文、证据链和结论。沟通高度严谨但对对话方要求不对称——可能降低低语境交互者的反馈速度。"
    })

# 如果不足3条补一条通用的
if len(vulns) < 3:
    ana_pct = qs["style_distribution"].get("分析型", 0)
    vulns.append({
        "id": "vuln-4",
        "en_title": "Analysis-Action Ratio",
        "zh_title": "分析-行动比例失调",
        "en_body": f"Analytical queries ({ana_pct}%) outpace emotional ({emo_pct}%) and creative ({qs['style_distribution'].get('创意型', 0)}%) combined. Conceptual velocity consistently <span class='ul-hw ul-red'>outpaces implementation velocity</span> — thinking:doing ratio estimated at 3:1 or higher.",
        "zh_body": f"分析型查询（{ana_pct}%）超过情感型与创意型之和。概念速度持续<span class='ul-hw ul-red'>超过实施速度</span>——思考:行动比估计在3:1或更高。"
    })

# ══ EXT_CONTENT 覆盖：优势 + 盲区 ════════════════════════════════════════
# 若外部传入了 strengths / vulns 列表，整体替换脚本生成的版本
if "strengths" in EXT_CONTENT:
    strengths = EXT_CONTENT["strengths"]
    print(f"  [content] strengths overridden: {len(strengths)} items", file=sys.stderr)
if "vulns" in EXT_CONTENT:
    vulns = EXT_CONTENT["vulns"]
    print(f"  [content] vulns overridden: {len(vulns)} items", file=sys.stderr)

# ══ 轨迹文本 ════════════════════════════════════════════════════════════════
top_domain = topics[0][0]   # e.g. AI/大模型
sec_domain = topics[1][0] if len(topics) > 1 else top_domain  # fallback if only 1 topic

# ══ 数据驱动自动涂黑决策 ═══════════════════════════════════════════════════
# 生成一个 auto_redacts 列表，每项包含 id / visible_text / reveal_text / tag
# 渲染时将这些 span 注入到对应位置
#
# 三类触发规则：
#   A) 置信度 Low 的推断 → 涂黑，解密后显示「LOW CONFIDENCE · 待验证」
#   B) 敏感认知盲区（情感型极低 / Epi极端压制）→ 涂黑，加 SENSITIVE 标记
#   C) 极端异常值（极高/极低能力分、极端话题集中）→ 涂黑，营造「机密数据」感

auto_redacts = {}  # id → {visible, reveal, tag}

# ── A) 置信度 Low：session 数少时推断置信度低 ─────────────────────────────
# 若总会话 < 30，灵魂三分推断为 Low confidence
if sessions < 30:
    auto_redacts["soul-conf"] = {
        "visible": f"Logos {logos}% · Thumos {thumos}% · Epithumia {epi}%",
        "reveal":  f"Logos {logos}% · Thumos {thumos}% · Epithumia {epi}%　⚠ LOW CONFIDENCE — 基于{sessions}次会话，样本量偏低，建议积累至50+次后重新建档",
        "tag":     "UNVERIFIED",
    }

# 若 cap_top 最高分与最低分差距 < 0.5，能力分布平坦，区分度低
if cap_top and (cap_top[0][1] - cap_top[-1][1]) < 0.5:
    auto_redacts["cap-conf"] = {
        "visible": f"{cap_top[0][0]} {cap_top[0][1]}/10",
        "reveal":  f"{cap_top[0][0]} {cap_top[0][1]}/10　⚠ LOW CONFIDENCE — 各维度评分差距过小，排序结果置信度低",
        "tag":     "UNVERIFIED",
    }

# ── B) 敏感认知盲区 ────────────────────────────────────────────────────────
# 情感型极低（< 8%）：属于高度敏感的人格特征，涂黑处理
if emo_pct < 8:
    auto_redacts["emo-sensitive"] = {
        "visible": f"情感型 {emo_pct}%",
        "reveal":  f"情感型 {emo_pct}%　■ SENSITIVE — 情感表达频率极低，处于样本底部5%分位，为敏感认知特征",
        "tag":     "SENSITIVE",
    }

# Epithumia 极低（< 8%）：欲望/冲动极度压制，敏感区间
if epi < 8:
    auto_redacts["epi-sensitive"] = {
        "visible": f"Epithumia {epi}%",
        "reveal":  f"Epithumia {epi}%　■ SENSITIVE — 欲望维度极度压制（< 8%），位于统计异常区间，建议谨慎解读",
        "tag":     "SENSITIVE",
    }

# ── C) 极端异常值 → 营造「机密数据」感 ────────────────────────────────────
# 最高能力分 >= 9.0：极端优势，作为「机密」处理
if cap_top and cap_top[0][1] >= 9.0:
    name, score = cap_top[0]
    auto_redacts["cap-peak"] = {
        "visible": f"[REDACTED] {score}/10",
        "reveal":  f"{name} {score}/10 — 位于样本Top 5%，标记为高价值特征",
        "tag":     "CLASSIFIED",
    }

# 最低能力分 <= 4.0：极端弱项，涂黑避免直接展示
if caps and caps[-1][1] <= 4.0:
    name, score = caps[-1]
    auto_redacts["cap-floor"] = {
        "visible": f"[REDACTED]",
        "reveal":  f"{name} {score}/10 — 极端低分，位于样本Bottom 5%",
        "tag":     "CLASSIFIED",
    }

# 话题高度集中（Top-1 占比 > 55%）：异常集中，标为机密
if topics and topics[0][1]["pct"] > 55:
    auto_redacts["topic-concentrate"] = {
        "visible": f"[CLASSIFIED — {topics[0][0].split('/')[0]} DOMINANCE]",
        "reveal":  f"{topics[0][0]} 占比 {topics[0][1]['pct']}% — 极度集中，超出正常范围",
        "tag":     "CLASSIFIED",
    }

# Logos 极高（>= 78%）：认知极端，涂黑原始数值
if logos >= 78:
    auto_redacts["logos-extreme"] = {
        "visible": f"Logos [██]%",
        "reveal":  f"Logos {logos}% — 理性极端优势，位于样本Top 3%",
        "tag":     "CLASSIFIED",
    }

def R(rid: str, fallback_text: str) -> str:
    """生成涂黑 span。若 rid 在 auto_redacts 中则使用自动涂黑，否则返回原文。"""
    if rid in auto_redacts:
        ar = auto_redacts[rid]
        tag_style = {
            "UNVERIFIED": "border-bottom:1px dashed #8b6a1a",
            "SENSITIVE":  "border-bottom:2px solid #8b1a1a",
            "CLASSIFIED": "",
        }.get(ar["tag"], "")
        return (
            f"<span class='R' id='{rid}' data-reveal='{ar['reveal']}' "
            f"data-tag='{ar['tag']}' style='{tag_style}'>{ar['visible']}</span>"
        )
    return fallback_text

# ══ 心理特征段落动态生成 ═══════════════════════════════════════════════════
# 每段从实际数据推断专属结论，不使用固定评价句

exec_pct_val = qs['style_distribution'].get('执行型', 0)
emo_pct_val  = qs['style_distribution'].get('情感型', 0)
ana_pct_val  = qs['style_distribution'].get('分析型', 0)
cre_pct_val  = qs['style_distribution'].get('创意型', 0)
avg_len      = int(lang['avg_message_length'])
emoji_pct    = lang['emoji_usage_pct']
peak_h       = tp['peak_hours'][0] if tp.get('peak_hours') else "深夜"

# ── Observation 1: 交互结构 ──────────────────────────────────────────────
# 从执行/分析/情感比例推断主导风格，避免通用句
if exec_pct_val >= 35 and ana_pct_val >= 40:
    # 双高：执行+分析都高，说明是「任务驱动型分析者」
    obs1_en = (
        f"Across {total_m} messages: execution-type queries {exec_pct_val}%, analytical {ana_pct_val}%, "
        f"emotional {emo_pct_val}%. The co-dominance of execution and analysis is atypical — "
        f"most profiles skew one way. Subject appears to <span class='ul-hw ul-red'>think in systems and deliver in tasks</span>: "
        f"analysis is not preparatory — it is the primary mode, with execution as its output form."
    )
    obs1_zh = (
        f"在{total_m}条消息中：执行型{exec_pct_val}%、分析型{ana_pct_val}%、情感型{emo_pct_val}%。"
        f"执行与分析双高并存并不常见——多数人偏向其一。"
        f"受试者呈现<span class='ul-hw ul-red'>以系统思考、以任务交付</span>的模式："
        f"分析不是前置准备，而是主要工作方式；执行是分析的输出形态。"
    )
elif exec_pct_val >= 35 and emo_pct_val <= 10:
    # 高执行 + 低情感：工具理性主导
    dominant_kw = kws[0] if kws else top_domain.split("/")[0]
    obs1_en = (
        f"Execution-type queries: {exec_pct_val}%; emotional-register: {emo_pct_val}%. "
        f"Subject uses AI as a <span class='ul-hw'>precision instrument</span>, not a sounding board — "
        f"inputs are directive, outputs are expected at specification level. "
        f"The primary interaction verb, inferred from keyword density, is not 'explore' but <span class='ul-hw ul-red'>'{dominant_kw}'</span>."
    )
    obs1_zh = (
        f"执行型查询{exec_pct_val}%，情感型{emo_pct_val}%。"
        f"受试者将 AI 作为<span class='ul-hw'>精密工具</span>而非情感容器使用——"
        f"输入是指令性的，输出被期待达到规格级别。"
        f"从关键词密度推断，主导交互动词不是「探索」，而是<span class='ul-hw ul-red'>「{dominant_kw}」</span>。"
    )
elif ana_pct_val >= 50:
    # 分析型极高：纯思考者
    obs1_en = (
        f"Analytical queries dominate at {ana_pct_val}% — execution {exec_pct_val}%, emotional {emo_pct_val}%. "
        f"Subject's primary use of AI is <span class='ul-hw'>sense-making</span>: "
        f"questions are typically open-structured, inviting elaboration rather than commanding output. "
        f"The ratio suggests a preference for <span class='ul-hw ul-red'>thinking-with</span> over directing."
    )
    obs1_zh = (
        f"分析型查询主导，占{ana_pct_val}%——执行型{exec_pct_val}%、情感型{emo_pct_val}%。"
        f"受试者主要将 AI 用于<span class='ul-hw'>意义建构</span>："
        f"问题结构开放，倾向于引出阐述而非命令输出。"
        f"比例表明受试者偏好<span class='ul-hw ul-red'>「与 AI 共同思考」</span>而非指令驱动。"
    )
elif emo_pct_val >= 20:
    # 情感型偏高：人文主导
    obs1_en = (
        f"Emotional-register queries reach {emo_pct_val}% — above sample average. "
        f"Subject treats AI as a <span class='ul-hw'>reflective interlocutor</span>: "
        f"inputs frequently include relational context, affect signals, and subjective framing. "
        f"Execution-type: {exec_pct_val}%. The balance suggests a profile that <span class='ul-hw ul-red'>values dialogue over task completion</span>."
    )
    obs1_zh = (
        f"情感型查询达{emo_pct_val}%，高于样本均值。"
        f"受试者将 AI 视为<span class='ul-hw'>反思性对话者</span>："
        f"输入中频繁包含关系语境、情感信号与主观框架。"
        f"执行型{exec_pct_val}%。比例表明受试者<span class='ul-hw ul-red'>重视对话过程甚于任务完成</span>。"
    )
else:
    # 均衡型
    obs1_en = (
        f"Query style: analytical {ana_pct_val}% / execution {exec_pct_val}% / emotional {emo_pct_val}% / creative {cre_pct_val}%. "
        f"The distribution is <span class='ul-hw'>unusually balanced</span> — no single mode dominates. "
        f"This suggests a subject who adapts cognitive register to task type, "
        f"rather than defaulting to one style. Rare in behavioral profiles."
    )
    obs1_zh = (
        f"查询风格：分析型{ana_pct_val}% / 执行型{exec_pct_val}% / 情感型{emo_pct_val}% / 创意型{cre_pct_val}%。"
        f"分布<span class='ul-hw'>异常均衡</span>——无单一模式主导。"
        f"表明受试者能根据任务类型切换认知模式，而非固守一种风格。"
        f"在行为画像中较为罕见。"
    )

# ── Observation 2: 认知负载 ──────────────────────────────────────────────
# 从消息长度 + emoji 比例推断信息密度风格
if avg_len >= 600 and emoji_pct <= 3:
    obs2_en = (
        f"Average message length: <span class='ul-hw ul-red'>{avg_len} characters</span> "
        f"(emoji usage: {emoji_pct}%). High length, minimal emoji — "
        f"a combination that signals <span class='circled'>information-dense, low-affect communication<svg class='c-svg' viewBox='0 0 340 26'><ellipse cx='170' cy='13' rx='166' ry='12'/></svg></span>. "
        f"Subject pre-structures the full answer space before asking — "
        f"the question arrives with its own context already built in."
    )
    obs2_zh = (
        f"平均消息长度<span class='ul-hw ul-red'>{avg_len}字</span>（表情符号使用率{emoji_pct}%）。"
        f"高长度 + 极低表情符号——这一组合标志着"
        f"<span class='circled'>信息密集、低情感外显的沟通风格<svg class='c-svg' viewBox='0 0 270 26'><ellipse cx='135' cy='13' rx='131' ry='12'/></svg></span>。"
        f"受试者在提问前已完成完整答案空间的预构建——问题到达时自带上下文。"
    )
elif avg_len >= 400 and emoji_pct >= 5:
    obs2_en = (
        f"Average message length: <span class='ul-hw ul-red'>{avg_len} characters</span> "
        f"(emoji usage: {emoji_pct}%). Moderate length with elevated emoji — "
        f"signals a subject who maintains <span class='ul-hw'>informational substance</span> "
        f"while using affect markers to regulate tone. "
        f"Communication is thorough but not clinical."
    )
    obs2_zh = (
        f"平均消息长度<span class='ul-hw ul-red'>{avg_len}字</span>（表情符号{emoji_pct}%）。"
        f"中等长度 + 较高表情使用——表明受试者在保持<span class='ul-hw'>信息实质</span>的同时，"
        f"用情感标记调节语气。沟通充分但不冷漠。"
    )
elif avg_len <= 200:
    obs2_en = (
        f"Average message length: <span class='ul-hw ul-red'>{avg_len} characters</span> "
        f"(emoji usage: {emoji_pct}%). Concise — subject communicates in compressed bursts. "
        f"Either pre-filters extensively before writing, or operates with "
        f"<span class='ul-hw ul-red'>high trust in implicit context</span>. "
        f"Low message length ≠ low complexity; the density is in the compression."
    )
    obs2_zh = (
        f"平均消息长度<span class='ul-hw ul-red'>{avg_len}字</span>（表情符号{emoji_pct}%）。"
        f"简洁——受试者以压缩形式传达信息。"
        f"要么在书写前进行了大量预筛选，要么对隐式上下文具有"
        f"<span class='ul-hw ul-red'>高度信任</span>。消息短≠复杂度低；密度藏在压缩里。"
    )
else:
    obs2_en = (
        f"Average message length: <span class='ul-hw ul-red'>{avg_len} characters</span> "
        f"(emoji usage: {emoji_pct}%). "
        f"Length sits in the mid-range — subject neither over-explains nor under-specifies. "
        f"Emoji at {emoji_pct}% indicates <span class='ul-hw'>calibrated informality</span>: "
        f"professional register maintained, relational warmth present."
    )
    obs2_zh = (
        f"平均消息长度<span class='ul-hw ul-red'>{avg_len}字</span>（表情符号{emoji_pct}%）。"
        f"长度居中——既不过度解释，也不信息不足。"
        f"{emoji_pct}%的表情使用表明<span class='ul-hw'>校准过的非正式感</span>："
        f"专业语调得以保持，人际温度也存在。"
    )

# ── Observation 3: 峰值决策窗口 ─────────────────────────────────────────
# 从 peak_hours + top 话题推断峰值时段的实际用途
top_kw_at_peak = kws[0] if kws else top_domain.split("/")[0]
sec_kw_at_peak = kws[1] if len(kws) > 1 else ""
if "深夜" in time_class_zh or "夜间" in time_class_zh or tp.get("pattern_label","") in ("late_night","night"):
    obs3_en = (
        f"Activity concentrates in <span class='circled'><strong>{time_class_en}</strong>"
        f"<svg class='c-svg' viewBox='0 0 200 26'><ellipse cx='100' cy='13' rx='96' ry='12'/></svg></span> "
        f"pattern, peaking at {peak_h}. <span class='R' id='r3' data-zh='r3z'>"
        f"Peak-hour queries cluster around {top_kw_at_peak} and {sec_kw_at_peak} — "
        f"not maintenance tasks, but structural thinking. "
        f"The night window appears to be <span class='ul-hw'>a protected cognitive zone</span>, "
        f"not incidental insomnia.</span> "
        f"Daytime queries skew toward execution and coordination."
    )
    obs3_zh = (
        f"活跃度集中于<span class='circled'><strong>{time_class_zh}</strong>"
        f"<svg class='c-svg' viewBox='0 0 130 26'><ellipse cx='65' cy='13' rx='61' ry='12'/></svg></span>"
        f"模式，峰值{peak_h}。<span class='R' id='r3z' data-en='r3'>"
        f"峰值时段查询集中于{top_kw_at_peak}与{sec_kw_at_peak}——"
        f"不是维护性任务，而是结构性思考。"
        f"深夜时段表现为<span class='ul-hw'>受保护的认知区间</span>，而非偶发失眠。</span>"
        f"白天查询偏向执行与协调。"
    )
elif "早晨" in time_class_zh or "上午" in time_class_zh or "morning" in time_class_en.lower():
    obs3_en = (
        f"Activity concentrates in <span class='circled'><strong>{time_class_en}</strong>"
        f"<svg class='c-svg' viewBox='0 0 200 26'><ellipse cx='100' cy='13' rx='96' ry='12'/></svg></span> "
        f"pattern, peaking at {peak_h}. <span class='R' id='r3' data-zh='r3z'>"
        f"Morning-peak profile suggests a subject who front-loads cognitive work — "
        f"complex queries ({top_kw_at_peak}) appear before midday, "
        f"with simpler coordination tasks in the afternoon. "
        f"Biological peak and task priority are <span class='ul-hw'>deliberately aligned</span>.</span>"
    )
    obs3_zh = (
        f"活跃度集中于<span class='circled'><strong>{time_class_zh}</strong>"
        f"<svg class='c-svg' viewBox='0 0 130 26'><ellipse cx='65' cy='13' rx='61' ry='12'/></svg></span>"
        f"模式，峰值{peak_h}。<span class='R' id='r3z' data-en='r3'>"
        f"早晨型峰值表明受试者将认知工作前置——"
        f"复杂查询（{top_kw_at_peak}）在正午前出现，"
        f"下午偏向更简单的协调任务。"
        f"生物峰值与任务优先级<span class='ul-hw'>被刻意对齐</span>。</span>"
    )
else:
    obs3_en = (
        f"Activity concentrates in <span class='circled'><strong>{time_class_en}</strong>"
        f"<svg class='c-svg' viewBox='0 0 200 26'><ellipse cx='100' cy='13' rx='96' ry='12'/></svg></span> "
        f"pattern, peaking at {peak_h}. <span class='R' id='r3' data-zh='r3z'>"
        f"Queries within this window skew toward {top_kw_at_peak} — "
        f"suggesting the peak slot is reserved for <span class='ul-hw'>highest-priority cognitive load</span>. "
        f"Off-peak queries are qualitatively lighter.</span>"
    )
    obs3_zh = (
        f"活跃度集中于<span class='circled'><strong>{time_class_zh}</strong>"
        f"<svg class='c-svg' viewBox='0 0 130 26'><ellipse cx='65' cy='13' rx='61' ry='12'/></svg></span>"
        f"模式，峰值{peak_h}。<span class='R' id='r3z' data-en='r3'>"
        f"此时间窗内的查询偏向{top_kw_at_peak}——"
        f"表明峰值时段被留给<span class='ul-hw'>最高优先级认知负载</span>。"
        f"非峰值时段的查询质量明显更轻。</span>"
    )

# ── Analyst's Note: 分析员备注 ───────────────────────────────────────────
# 从实际盲区 + 最强能力组合推断专属制约因素
top_cap_name = cap_top[0][0] if cap_top else "框架思维"
top_vuln_title = vulns[0]["zh_title"] if vulns else "分析-行动比例失调"
top_vuln_en = vulns[0]["en_title"] if vulns else "Analysis-Action Gap"

if "完美主义" in top_vuln_title or "Perfectionism" in top_vuln_en:
    analyst_note_en = (
        f"Primary constraint: the gap between <span class='ul-hw'>{top_cap_name}</span> "
        f"(peak asset, {cap_top[0][1]}/10) and shipping velocity. "
        f"The same precision that produces high-quality frameworks also raises the internal threshold for 'done'. "
        f"The bottleneck is not capability — it is the definition of acceptable output."
    )
    analyst_note_zh = (
        f"主要制约：<span class='ul-hw'>{top_cap_name}</span>（峰值资产，{cap_top[0][1]}/10）"
        f"与交付速度之间的差距。"
        f"产生高质量框架的精确性，同样提高了「完成」的内部门槛。"
        f"瓶颈不是能力——而是对「可接受输出」的定义。"
    )
elif "情感" in top_vuln_title or "Emotion" in top_vuln_en:
    analyst_note_en = (
        f"Primary constraint: interpersonal signal bandwidth. "
        f"Subject's {top_cap_name} ({cap_top[0][1]}/10) operates at high fidelity on task-level problems — "
        f"the same fidelity applied to relational signals would compound the advantage. "
        f"Current pattern: <span class='ul-hw'>high receive, low transmit</span> on emotional register."
    )
    analyst_note_zh = (
        f"主要制约：人际信号带宽。"
        f"受试者的{top_cap_name}（{cap_top[0][1]}/10）在任务层级问题上运行精度极高——"
        f"将同等精度应用于关系信号将复利放大优势。"
        f"当前模式：情感维度<span class='ul-hw'>高接收、低发送</span>。"
    )
elif "分析" in top_vuln_title or "Analysis" in top_vuln_en:
    analyst_note_en = (
        f"Primary constraint: conceptual velocity outpaces delivery velocity. "
        f"{top_cap_name} ({cap_top[0][1]}/10) generates ideas faster than they can be shipped. "
        f"The leverage point is not thinking harder — it is <span class='ul-hw'>lowering the minimum viable threshold for external output</span>."
    )
    analyst_note_zh = (
        f"主要制约：构想速度超过交付速度。"
        f"{top_cap_name}（{cap_top[0][1]}/10）产生想法的速度超过输出速度。"
        f"杠杆点不是更努力地思考——而是<span class='ul-hw'>降低外部输出的最低可行门槛</span>。"
    )
else:
    analyst_note_en = (
        f"Primary constraint: the gap between peak capability ({top_cap_name}, {cap_top[0][1]}/10) "
        f"and {top_vuln_en}. These are not independent — the same cognitive pattern that drives the strength "
        f"also produces the vulnerability. <span class='ul-hw'>The fix is not subtraction; it is calibration.</span>"
    )
    analyst_note_zh = (
        f"主要制约：峰值能力（{top_cap_name}，{cap_top[0][1]}/10）与{top_vuln_title}之间的张力。"
        f"两者并非独立——驱动优势的认知模式同样产生盲区。"
        f"<span class='ul-hw'>修复不是减法，而是校准。</span>"
    )

# ══ HTML 生成 ════════════════════════════════════════════════════════════════
def render_strengths(items):
    out = []
    for i, s in enumerate(items, 1):
        out.append(f"""
  <div class="str-item">
    <span class="str-label">Str-{i}: {s['en_title']}</span><span class="str-score">/ {s['zh_title']} — {s['score']}</span>
    <span class="str-body">{s['en_body']}<br>{s['zh_body']}</span>
  </div>""")
    return "".join(out)

def render_vulns(items):
    out = []
    for i, v in enumerate(items, 1):
        out.append(f"""
  <p class="para"><span class="circled"><strong>Vuln-{i}: {v['en_title']}</strong><svg class="c-svg" viewBox="0 0 280 26"><ellipse cx="140" cy="13" rx="136" ry="12"/></svg></span> — {v['en_body']}</p>
  <p class="para-zh"><span class="circled"><strong>漏洞{i}：{v['zh_title']}</strong><svg class="c-svg" viewBox="0 0 168 26"><ellipse cx="84" cy="13" rx="80" ry="12"/></svg></span> — {v['zh_body']}</p>""")
    return "".join(out)

def render_topic_bars(items):
    out = []
    bar_colors = ["#8b1a1a","#6b3a3a","#7a4a4a","#8b5a5a","#a07070","#b08080","#ccc"]
    for i, (k, v) in enumerate(items[:7]):
        pct  = v["pct"]
        col  = bar_colors[min(i, len(bar_colors)-1)]
        fill = int(pct * 2.5)  # 最宽250px
        out.append(f"""
    <div style="display:flex;align-items:center;gap:12px;margin:5px 0;font-size:12.5px">
      <span style="width:130px;color:#3a2d0a">{k}</span>
      <div style="flex:1;height:7px;background:rgba(0,0,0,.12);border-radius:2px"><div style="height:100%;width:{int(pct*2.5)}px;max-width:100%;background:{col};border-radius:2px"></div></div>
      <span style="width:36px;color:#6b5a2a;text-align:right">{pct:.1f}%</span>
    </div>""")
    return "".join(out)

def render_cap_table(caps_sorted):
    out = []
    colors = ["#8b1a1a","#6b3a3a","#7a4a4a","#8b5a5a","#a07070","#b08080","#ccc"]
    for i, (k, v) in enumerate(caps_sorted):
        col  = colors[min(i, len(colors)-1)]
        fill = int(v / 10 * 100)
        out.append(f"""
    <tr>
      <td class="s-label">{k}</td>
      <td><div class="score-bar-bg"><div class="score-bar-fill" style="width:{fill}%;background:{col}"></div></div></td>
      <td class="score-num">{v}</td>
    </tr>""")
    return "".join(out)

DOC_ID = f"DS-PN-2026-{USER['code']}"
AGENT  = USER["agent_name"]

HTML = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CLASSIFIED — {DOC_ID}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Special+Elite&family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#1e1e1e;display:flex;flex-direction:column;align-items:center;
  padding-top:136px;padding-bottom:40px;padding-left:20px;padding-right:20px;
  font-family:'Courier Prime','Courier New',monospace;min-height:100vh}}
#top-bar{{position:fixed;top:0;left:0;right:0;z-index:9999;background:#0e0a06;border-bottom:2px solid #6F1714;font-family:'Courier Prime',monospace}}
#cd-row{{display:flex;align-items:center;justify-content:space-between;padding:10px 28px 6px;border-bottom:1px solid rgba(111,23,20,.35)}}
.cd-meta{{display:flex;flex-direction:column;gap:2px}}
.cd-label{{color:#4a3a2a;font-size:9px;letter-spacing:3px;text-transform:uppercase}}
#cd-display{{font-size:40px;font-weight:700;letter-spacing:7px;color:#c0140e;line-height:1;text-shadow:0 0 22px rgba(192,20,14,.4);text-align:center;flex:1}}
#cd-display.warn{{animation:blink .6s infinite;color:#ff2200;text-shadow:0 0 30px rgba(255,34,0,.7)}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.1}}}}
#cd-sub{{font-size:10px;letter-spacing:3px;color:#4a3a2a;text-align:center;margin-top:3px}}
.cd-destroy{{cursor:pointer;border:1px solid #6F1714;color:#c0140e;padding:8px 16px;font-size:11px;letter-spacing:2px;background:transparent;transition:all .2s;font-family:'Courier Prime',monospace;white-space:nowrap}}
.cd-destroy:hover{{background:#6F1714;color:#fff}}
#tool-row{{display:flex;align-items:center;justify-content:center;gap:14px;padding:7px 28px;flex-wrap:wrap}}
.tip{{font-size:13px;letter-spacing:1px;color:#555}}
.sep{{color:#2a2a2a}}
.tbtn{{cursor:pointer;padding:4px 14px;border:1px solid #2e2416;border-radius:2px;color:#777;font-size:13px;letter-spacing:1px;background:transparent;transition:all .2s;font-family:'Courier Prime',monospace}}
.tbtn:hover{{border-color:#6F1714;color:#c0140e}}
.tbtn.on{{border-color:#c0140e;color:#c0140e;background:rgba(111,23,20,.12)}}
.page{{position:relative;width:820px;background:#e8dfc0;padding:58px 68px 72px 76px;margin-bottom:44px;line-height:1.8;font-size:13.5px;color:#1a1407;
  box-shadow:0 0 0 1px #bfaa78,5px 8px 40px rgba(0,0,0,.65),10px 14px 80px rgba(0,0,0,.3);
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3CfeBlend in='SourceGraphic' mode='multiply'/%3E%3C/filter%3E%3Crect width='400' height='400' filter='url(%23n)' opacity='.07'/%3E%3C/svg%3E"),linear-gradient(155deg,#f0e8cc 0%,#e4d9b4 35%,#ece2c0 65%,#e0d5ae 100%)}}
.page:nth-child(3){{transform:rotate(.3deg)}}
.page::before{{content:'';position:absolute;left:54px;top:0;bottom:0;width:1px;background:rgba(160,25,25,.22)}}
.page::after{{content:'';position:absolute;left:0;right:0;top:31%;height:1px;background:linear-gradient(90deg,transparent,rgba(0,0,0,.07) 20%,rgba(0,0,0,.12) 50%,rgba(0,0,0,.07) 80%,transparent)}}
.doc-header{{border-bottom:2px solid #1a1407;padding-bottom:12px;margin-bottom:22px;display:flex;justify-content:space-between;align-items:flex-start}}
.doc-title{{font-family:'Special Elite',cursive;font-size:19px;letter-spacing:3px;text-transform:uppercase}}
.doc-sub{{font-size:10px;letter-spacing:2px;color:#6b5a2a;margin-bottom:4px;text-transform:uppercase}}
.doc-stamp{{font-size:11px;text-align:right;color:#6b5a2a;letter-spacing:1px;line-height:1.6}}
.stamp{{display:inline-block;border:3px solid rgba(170,15,15,.82);color:rgba(165,12,12,.85);font-family:'Special Elite',cursive;font-size:24px;letter-spacing:6px;padding:3px 16px;transform:rotate(-8deg);opacity:.82;position:absolute;top:44px;right:72px;white-space:nowrap}}
.stamp::before{{content:'';position:absolute;inset:2px;border:1px solid rgba(170,15,15,.35)}}
/* 原型大印章（meta-grid 右侧空白区） */
.archetype-stamp{{
  position:absolute;
  top:210px;          /* meta-grid 顶部对齐 */
  right:52px;
  border:4px solid rgba(170,15,15,.85);
  color:rgba(155,10,10,.88);
  font-family:'Special Elite',cursive;
  padding:12px 18px 10px;
  transform:rotate(-9deg);
  opacity:.88;
  text-align:center;
  line-height:1.25;
  pointer-events:none;
}}
.archetype-stamp::before{{content:'';position:absolute;inset:3px;border:1px solid rgba(170,15,15,.38)}}
.archetype-stamp::after{{content:'';position:absolute;inset:7px;border:1px solid rgba(170,15,15,.18)}}
.archetype-en{{font-size:16px;letter-spacing:3px;display:block;text-transform:uppercase}}
.archetype-zh{{font-size:22px;letter-spacing:7px;display:block;margin-top:3px}}
.archetype-sub{{font-size:8px;letter-spacing:3px;display:block;margin-top:5px;opacity:.65}}
.meta-grid{{display:grid;grid-template-columns:110px 1fr;gap:0 14px;margin-bottom:26px}}
.meta-label{{padding:5px 0 0;font-weight:700;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#6b5a2a;line-height:1.3}}
.meta-val{{padding:3px 0 0;line-height:1.5}}
.meta-val .zh{{display:block;font-size:12px;color:#5a4a20;margin-top:1px}}
.meta-sep{{grid-column:1/-1;height:1px;background:rgba(0,0,0,.08);margin:4px 0}}
.section-title{{font-weight:700;font-size:11px;letter-spacing:2.5px;text-transform:uppercase;margin:22px 0 4px;border-bottom:1px solid rgba(0,0,0,.25);padding-bottom:3px;color:#1a1407}}
.para{{margin-bottom:4px}}
.para-zh{{font-size:12.5px;color:#4a3c10;margin-bottom:14px;line-height:1.75}}
.R{{display:inline;background:#1a1407;color:#1a1407;cursor:pointer;padding:1px 4px;border-radius:1px;user-select:none;transition:background .15s,color .15s}}
.R:hover{{opacity:.85}}
.R.open{{background:#fff5d6!important;color:#8b1a1a!important;border-bottom:1px dashed #8b1a1a}}
.circled{{position:relative;display:inline}}
.c-svg{{position:absolute;top:-7px;left:-8px;width:calc(100% + 16px);height:calc(100% + 14px);pointer-events:none;overflow:visible}}
.c-svg ellipse{{fill:none;stroke:#c0140e;stroke-width:2;opacity:.82}}
.ul-hw{{position:relative;display:inline}}
.ul-hw::after{{content:'';position:absolute;left:-1px;right:-1px;bottom:-3px;height:1.8px;background:#1a1407;border-radius:1px;transform:rotate(-.4deg);opacity:.7}}
.ul-red::after{{background:#c0140e;opacity:.8}}
.photo-frame{{float:right;margin:0 0 18px 26px}}
.photo-frame img{{display:block;width:120px;height:120px;object-fit:cover;border:1px solid #8a7a50;filter:contrast(1.05) brightness(.97)}}
.photo-frame::after{{content:'SUBJECT';display:block;font-size:9px;letter-spacing:3px;color:#7a6a40;text-align:center;margin-top:4px}}
.str-item{{margin:4px 0 12px;padding-left:18px;position:relative}}
.str-item::before{{content:'—';position:absolute;left:0;color:#8b1a1a;font-weight:700}}
.str-label{{font-weight:700;letter-spacing:.5px;color:#1a1407}}
.str-score{{font-size:11px;color:#8b1a1a;letter-spacing:1px;margin-left:6px}}
.str-body{{display:block;font-size:12.5px;color:#4a3c10;line-height:1.7;margin-top:1px}}
.score-table{{width:100%;margin:8px 0 16px;border-collapse:collapse}}
.score-table td{{padding:4px 8px 4px 0;font-size:12.5px;vertical-align:middle}}
.s-label{{width:140px;color:#3a2d0a}}
.score-bar-bg{{width:200px;height:7px;background:rgba(0,0,0,.12);border-radius:2px}}
.score-bar-fill{{height:100%;border-radius:2px}}
.score-num{{width:30px;font-size:12px;color:#6b5a2a;text-align:right}}
.margin-note{{position:absolute;left:8px;font-family:'Special Elite',cursive;font-size:10px;color:rgba(20,50,130,.72);transform:rotate(-90deg);transform-origin:left center;white-space:nowrap}}
.watermark{{position:absolute;bottom:90px;right:50px;font-family:'Special Elite',cursive;font-size:55px;color:rgba(160,15,15,.055);letter-spacing:4px;transform:rotate(-28deg);pointer-events:none;user-select:none}}
.footer{{display:flex;justify-content:space-between;align-items:flex-end;margin-top:38px;border-top:1px solid #a89060;padding-top:14px;font-size:11px;color:#6b5a2a}}
.stamp-footer{{border:2px solid rgba(10,90,10,.72);color:rgba(8,85,8,.8);font-family:'Special Elite',cursive;font-size:12px;letter-spacing:3px;padding:3px 10px;transform:rotate(3deg);opacity:.85}}
.divider{{width:820px;text-align:center;color:#555;font-size:10px;letter-spacing:4px;margin:6px 0 28px;text-transform:uppercase}}
@media(max-width:880px){{.page,.divider{{width:100%}}}}
</style>
</head>
<body>

<div id="top-bar">
  <div id="cd-row">
    <div class="cd-meta">
      <div class="cd-label">{CD_LABEL}</div>
      <div class="cd-label">{DOC_ID}</div>
    </div>
    <div style="flex:1;text-align:center">
      <div id="cd-display">--:--:--</div>
      <div id="cd-sub">{CD_SUB}</div>
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

<!-- PAGE 1 -->
<div class="page" style="transform:rotate(-.3deg)">
  <div class="stamp">CLASSIFIED</div>
  <div class="archetype-stamp">
    <span class="archetype-en">{soul_name_en}</span>
    <span class="archetype-zh">{soul_name_zh}</span>
    <span class="archetype-sub">ARCHETYPE · 原型认定</span>
  </div>
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
    <span class="meta-label">File No.<br>档案编号</span><div class="meta-val">{DOC_ID}</div>
    <div class="meta-sep"></div>
    <span class="meta-label">Subject<br>对象代号</span><div class="meta-val"><span class="ul-hw">{USER['real_name']} / CODE: {USER['name']}</span><span class="zh">{USER['real_name']} / 编号：{USER['name']}</span></div>
    <div class="meta-sep"></div>
    <span class="meta-label">D.O.B.<br>出生日期</span><div class="meta-val">{USER['dob']} | Age: {USER['age']}<span class="zh">{USER['dob']} | {USER['age']}岁</span></div>
    <div class="meta-sep"></div>
    <span class="meta-label">Affiliation<br>所属机构</span><div class="meta-val"><span class="circled">{USER['affiliation_en']}<svg class="c-svg" viewBox="0 0 310 26"><ellipse cx="155" cy="13" rx="151" ry="12"/></svg></span><span class="zh">{USER['affiliation_zh']}</span></div>
    <div class="meta-sep"></div>
    <span class="meta-label">Analyst<br>分析师</span><div class="meta-val">{AGENT}·V / Delphic Systems<span class="zh">{AGENT}·V / 德尔斐系统</span></div>
    <div class="meta-sep"></div>
    <span class="meta-label">Data Span<br>数据跨度</span><div class="meta-val">{date_r} ({sessions} sessions · {total_m} messages)<span class="zh">{date_r} · {sessions}次会话 · {total_m}条消息</span></div>
    <div class="meta-sep"></div>
    <span class="meta-label">Clearance<br>权限等级</span><div class="meta-val"><span class="R" id="r0" data-zh="r0z">LEVEL-3 / SUBJECT ACCESS ONLY</span><span class="zh"><span class="R" id="r0z" data-en="r0">三级 / 仅限主体访问</span></span></div>
    <span class="meta-label">Soul Index<br>灵魂指数</span><div class="meta-val">{R("soul-conf", f"Logos {logos}% · Thumos {thumos}% · Epithumia {epi}%")}<span class="zh">点击解密 / 柏拉图三分</span></div>
    <span class="meta-label">Peak Cap.<br>峰值能力</span><div class="meta-val">{R("cap-peak", f"{cap_top[0][0]} {cap_top[0][1]}/10" if cap_top else "—")}<span class="zh">点击解密 / 最高评分维度</span></div>
  </div>

  <div class="section-title">I. Identity &nbsp;<span style="font-weight:400;letter-spacing:1px">一、身份</span></div>
  <div class="photo-frame"><img src="{AVATAR}" alt="subject"></div>
  <p class="para">{EXT_CONTENT.get("sec1_en", f'Subject operates under designation <span class="ul-hw">"{USER["name"]}"</span>. {USER["bg_en"]}. Current role: <span class="ul-hw">{USER["affiliation_en"]}</span>. Classified as <strong>AI-Native (Tier 1)</strong> based on {topics[0][1]["pct"]}% session concentration in AI/LLM domain.')}</p>
  <p class="para-zh">{EXT_CONTENT.get("sec1_zh", f'<span class="ul-hw ul-red">{USER["bg_zh"]}</span>。现任职务：{USER["affiliation_zh"]}。基于{topics[0][1]["pct"]}%会话集中于AI/大模型领域，归类为<strong>AI-原生（Tier 1）</strong>。')}</p>

  <div class="section-title">II. Core Strengths &nbsp;<span style="font-weight:400;letter-spacing:1px">二、核心优势</span></div>
  <p class="para">{EXT_CONTENT.get("sec2_intro_en", f"The following capabilities are assessed as operationally significant based on {sessions} sessions ({total_m} messages, {date_r}). All scores are evidence-based behavioral assessments, not self-reported.")}</p>
  <p class="para-zh">{EXT_CONTENT.get("sec2_intro_zh", f"以下能力基于{sessions}次会话、{total_m}条消息的行为数据评估，非自评，所有评分均有证据支撑。")}</p>
{render_strengths(strengths)}

  <div class="footer">
    <div>{AGENT}·V · Delphic Systems · 行为建模部</div>
    <div class="stamp-footer">RESTRICTED</div>
    <div style="text-align:right;font-size:10px">REF: {DOC_ID}<br>CONTINUED ON PAGE 2</div>
  </div>
</div>

<div class="divider">— Page Break · {DOC_ID} · Page 2 of 2 —</div>

<!-- PAGE 2 -->
<div class="page" style="transform:rotate(.2deg)">
  <div class="stamp" style="color:rgba(15,90,15,.8);border-color:rgba(15,90,15,.8);transform:rotate(6deg)">FOR SUBJECT</div>
  <div class="watermark">PERSONA</div>
  <div class="margin-note" style="top:250px">CONTINUED FROM P.1 · {AGENT.upper()}·V</div>
  <div class="doc-header">
    <div>
      <div class="doc-sub">Capability &amp; Risk Assessment · 能力与风险评估</div>
      <div class="doc-title">Operational Profile<br><span style="font-size:14px;letter-spacing:2px">行动画像</span></div>
    </div>
    <div class="doc-stamp">{DOC_ID}<br>PAGE 2 OF 2</div>
  </div>

  <div class="section-title">III. Psychological Profile &nbsp;<span style="font-weight:400;letter-spacing:1px">三、心理特征</span></div>

  <p class="para"><span class="ul-hw">Observation 1 — Interaction Architecture.</span> {EXT_CONTENT.get("obs1_en", obs1_en)}</p>
  <p class="para-zh"><span class="ul-hw">观察一 — 交互结构。</span>{EXT_CONTENT.get("obs1_zh", obs1_zh)}</p>

  <p class="para"><span class="ul-hw">Observation 2 — Cognitive Load Signature.</span> {EXT_CONTENT.get("obs2_en", obs2_en)}</p>
  <p class="para-zh"><span class="ul-hw">观察二 — 认知负载特征。</span>{EXT_CONTENT.get("obs2_zh", obs2_zh)}</p>

  <p class="para"><span class="ul-hw">Observation 3 — Peak Decision Window.</span> {EXT_CONTENT.get("obs3_en", obs3_en)}</p>
  <p class="para-zh"><span class="ul-hw">观察三 — 峰值决策窗口。</span>{EXT_CONTENT.get("obs3_zh", obs3_zh)}</p>

  <p class="para"><span class="ul-hw">Synthesis — Soul Model.</span> Integrating the above: Logos (Reason) <strong>{R("logos-extreme", f"{logos}%")}</strong> · Thumos (Spirit) <strong>{thumos}%</strong> · Epithumia <span class="R" id="r3b" data-zh="r3bz">{R("epi-sensitive", f"{epi}%")} — {('a statistically rare suppression level, indicating desires are processed through reason before expression' if epi < 12 else 'below average, desires subordinated to rational and spirited drives' if epi < 18 else 'moderate, balanced against reason')}</span>. Convergent verdict: <strong>{soul_name_en} · {soul_name_zh}</strong>.</p>
  <p class="para-zh"><span class="ul-hw">综合 — 灵魂模型。</span>整合上述观察：理性<strong>{R("logos-extreme", f"{logos}%")}</strong> · 激情<strong>{thumos}%</strong> · 欲望<span class="R" id="r3bz" data-en="r3b">{R("epi-sensitive", f"{epi}%")} — {('统计意义上的罕见压制水平，欲望在表达前经由理性处理' if epi < 12 else '低于均值，欲望从属于理性与激情驱动' if epi < 18 else '适中，与理性保持平衡')}</span>。收敛判定：<strong>{soul_name_zh} · {soul_name_en}</strong>。</p>

  <div class="section-title">IV. Capability Scores &nbsp;<span style="font-weight:400;letter-spacing:1px">四、综合能力评分</span></div>
  <p class="para" style="margin-bottom:8px">Scores /10, derived from behavioral patterns across {sessions} sessions. Methodology: keyword frequency, problem complexity, solution depth.</p>
  <table class="score-table">{render_cap_table(caps)}</table>


  <div class="section-title">V. Cognitive Vulnerabilities &nbsp;<span style="font-weight:400;letter-spacing:1px">五、认知盲区</span></div>
{render_vulns(vulns)}

  <div class="section-title">VI. Strategic Trajectory &nbsp;<span style="font-weight:400;letter-spacing:1px">六、战略轨迹</span></div>
  <p class="para">{EXT_CONTENT.get("sec6_en", f'Primary domain: <span class="circled"><strong>{top_domain}</strong><svg class="c-svg" viewBox="0 0 110 26"><ellipse cx="55" cy="13" rx="51" ry="12"/></svg></span> ({topics[0][1]["pct"]}% of sessions). Secondary: {sec_domain} ({topics[1][1]["pct"] if len(topics) > 1 else "N/A"}%). Career vector: <span class="ul-hw ul-red">domain specialist → cross-domain architect</span>. Growth potential: <span class="R" id="r7" data-zh="r7z">★★★★★ 5/5 — Re-evaluate in 90 days.</span>')}</p>
  <p class="para-zh">{EXT_CONTENT.get("sec6_zh", f'主要领域：{top_domain}（{topics[0][1]["pct"]}%会话）。次要：{sec_domain}（{topics[1][1]["pct"] if len(topics) > 1 else "N/A"}%）。职业向量：<span class="ul-hw ul-red">领域专家 → 跨域架构师</span>。成长潜力：<span class="R" id="r7z" data-en="r7">★★★★★ 5/5 — 90天后重新评估。</span>')}</p>

  <div class="section-title">VII. Analyst's Note &nbsp;<span style="font-weight:400;letter-spacing:1px">七、分析员备注</span></div>
  <p class="para" style="font-style:italic">Archetype confirmed: <span class="ul-hw ul-red">{soul_name_en} · {soul_name_zh}</span>. Subject awareness of this analysis is noted and factored into modeling. Self-transparency <span class="ul-hw">accelerates accuracy</span>. <span class="R" id="r9" data-zh="r9z">{EXT_CONTENT.get("sec7_en", analyst_note_en)}</span></p>
  <p class="para-zh" style="font-style:italic">原型已确认：<span class="ul-hw ul-red">{soul_name_zh} · {soul_name_en}</span>。受试者对本次分析的知情状态已计入模型。自我透明度<span class="ul-hw">提升建模精度</span>。<span class="R" id="r9z" data-en="r9">{EXT_CONTENT.get("sec7_zh", analyst_note_zh)}</span></p>

  <p class="para">Topic distribution evidence — {' · '.join(f'{k}({v["pct"]:.0f}%)' for k,v in topics[:5])}:</p>
  <div style="margin:8px 0 16px">{render_topic_bars(topics)}</div>

  <div class="footer">
    <div>{AGENT}·V · Delphic Systems · 2026-04-15</div>
    <div class="stamp-footer">FOR SUBJECT ONLY</div>
    <div style="text-align:right;font-size:10px">{DOC_ID}<br>END OF FILE · 档案终止</div>
  </div>
</div>

<div style="color:#444;font-size:10px;letter-spacing:3px;margin-top:8px;text-align:center">{DOC_ID} · DELPHIC SYSTEMS · 2026</div>

<script>
const EXPIRE_AT=__EXPIRE_MS__;const DEST_FILE="__FILENAME__";const DEST_TOKEN="__TOKEN__";const SERVER="__SERVER__";
function fmt(ms){{if(ms<=0)return"00:00:00";const h=Math.floor(ms/3600000),m=Math.floor((ms%3600000)/60000),s=Math.floor((ms%60000)/1000);return[h,m,s].map(v=>String(v).padStart(2,"0")).join(":");}}
function showDestroyed(){{document.body.innerHTML='<div style="min-height:100vh;background:#080602;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:Courier New,monospace;color:#c0140e;text-align:center;gap:28px;padding:40px"><div style="font-size:48px;letter-spacing:8px;border:3px solid #c0140e;padding:14px 40px">FILE DESTROYED<\/div><div style="font-size:12px;letter-spacing:4px;color:#3a1a1a">{"DOC_ID"}<\/div><div style="font-size:11px;color:#2a1412;letter-spacing:2px;line-height:2.4">THIS FILE HAS BEEN PERMANENTLY DELETED<br>\u6b64\u6863\u6848\u5df2\u88ab\u6c38\u4e45\u5220\u9664<br>'+new Date().toLocaleString("zh-CN")+'<\/div><\/div>';}}
async function callAPI(){{try{{const r=await fetch(SERVER+"/api/destruct",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{file:DEST_FILE,token:DEST_TOKEN}})}});return(await r.json()).ok;}}catch(e){{return false;}}}}
async function destruct(){{showDestroyed();await callAPI();}}
async function earlyDestruct(){{if(!confirm("\u786e\u8ba4\u7acb\u5373\u9500\u6bc1\u6b64\u6863\u6848\uff1f\u670d\u52a1\u7aef\u6587\u4ef6\u5c06\u540c\u6b65\u5220\u9664\u3002"))return;await destruct();}}
let warned=false;
function tick(){{const left=EXPIRE_AT-Date.now(),el=document.getElementById("cd-display"),sub=document.getElementById("cd-sub");if(!el)return;if(left<=0){{destruct();return;}}el.textContent=fmt(left);if(left<60000&&!warned){{el.classList.add("warn");if(sub)sub.textContent="\u2620 FINAL COUNTDOWN \u00b7 \u6700\u540e\u5012\u8ba1\u65f6";warned=true;}}}}
setInterval(tick,1000);tick();
document.querySelectorAll(".R").forEach(el=>{{
  el.addEventListener("click",()=>{{
    const on=!el.classList.contains("open");
    el.classList.toggle("open",on);
    // 旧版：data-zh / data-en 联动
    const pid=el.dataset.zh||el.dataset.en;
    if(pid){{const p=document.getElementById(pid);if(p)p.classList.toggle("open",on);}}
    // 新版：data-reveal 直接替换显示内容，data-tag 决定徽章样式
    if(el.dataset.reveal){{
      if(on){{
        el.dataset.orig=el.dataset.orig||el.textContent;
        const tagColors={{"CLASSIFIED":"#8b1a1a","SENSITIVE":"#8b1a1a","UNVERIFIED":"#7a6a20"}};
        const tagLabels={{"CLASSIFIED":"▣ CLASSIFIED","SENSITIVE":"■ SENSITIVE","UNVERIFIED":"⚠ UNVERIFIED"}};
        const tag=el.dataset.tag||"";
        const badge=tag?`<span style="font-size:9px;letter-spacing:2px;color:${{tagColors[tag]||'#555'}};margin-left:6px;border:1px solid ${{tagColors[tag]||'#555'}};padding:1px 5px;vertical-align:middle">${{tagLabels[tag]||tag}}</span>`:"";
        el.innerHTML=el.dataset.reveal+badge;
      }}else{{
        el.textContent=el.dataset.orig||el.textContent;
      }}
    }}
  }});
}});
let redactOn=false;const stack=[];
function toggleRedact(){{redactOn=!redactOn;const btn=document.getElementById("rbtn");btn.textContent=redactOn?"\u2702 \u6846\u9009\u9012\u9ed1\uff1a\u5f00":"\u2702 \u6846\u9009\u9012\u9ed1\uff1a\u5173";btn.classList.toggle("on",redactOn);document.body.style.cursor=redactOn?"crosshair":"";}}
document.addEventListener("mouseup",()=>{{if(!redactOn)return;const sel=window.getSelection();if(!sel||sel.isCollapsed||!sel.toString().trim())return;try{{const range=sel.getRangeAt(0),span=document.createElement("span");span.style.cssText="display:inline;background:#1a1407;color:#1a1407;cursor:pointer;padding:1px 3px;border-radius:1px;transition:background .15s,color .15s";span.title="\u70b9\u51fb\u89e3\u5bc6";span.addEventListener("click",()=>{{const on=span.style.background!=="rgb(255, 245, 214)";span.style.background=on?"#fff5d6":"#1a1407";span.style.color=on?"#8b1a1a":"#1a1407";span.style.borderBottom=on?"1px dashed #8b1a1a":";";}});range.surroundContents(span);stack.push(span);sel.removeAllRanges();}}catch(e){{window.getSelection()?.removeAllRanges();}}}});
function undoRedact(){{if(!stack.length)return;const span=stack.pop(),p=span.parentNode;if(!p)return;while(span.firstChild)p.insertBefore(span.firstChild,span);p.removeChild(span);}}
function saveHTML(){{if(redactOn)toggleRedact();const blob=new Blob(["<!DOCTYPE html>"+document.documentElement.outerHTML],{{type:"text/html"}});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="{DOC_ID}.html";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);}}
</script>
</body>
</html>"""

# 修复 JS 中的 f-string 占位
HTML = HTML.replace('__EXPIRE_MS__', str(EXPIRE_MS))
HTML = HTML.replace('__FILENAME__', FILENAME)
HTML = HTML.replace('__TOKEN__', TOKEN)
HTML = HTML.replace('__SERVER__', SERVER)
HTML = HTML.replace('{"DOC_ID"}', DOC_ID)

out_name = f"persona-dangsi-{'5min' if MODE=='5min' else ''}.html".replace("-.html", ".html")
out_path = f"/tmp/{out_name}"
Path(out_path).write_text(HTML)
print(f"OK {len(HTML):,} bytes -> {out_path}")
print(f"  soul: {soul_name_en} | time: {time_class_en}")
print(f"  strengths: {len(strengths)} | vulns: {len(vulns)}")
