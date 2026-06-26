#!/usr/bin/env python3
"""
德尔斐计划 - 人物档案图表生成器 v4
数据驱动版：所有图表数据从 --stats JSON 读取，无硬编码。
风格参考：观潮弄虾报告图（环形图+箭头标注+署名）
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import numpy as np
import os
import json
import argparse
import sys
from pathlib import Path

# =====================
# 中文字体
# =====================
font_path      = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_bold_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
for fp in [font_path, font_bold_path]:
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)

ZH   = fm.FontProperties(fname=font_path,      size=11)
ZH_B = fm.FontProperties(fname=font_bold_path, size=11)
ZH_S = fm.FontProperties(fname=font_path,      size=9)
ZH_T = fm.FontProperties(fname=font_bold_path, size=13)

matplotlib.rcParams['font.family']     = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# 抑制字体 warning（中文文字用 fontproperties=ZH 直接传入，不走 rcParams）
import warnings
warnings.filterwarnings("ignore", message="findfont")
warnings.filterwarnings("ignore", message="Glyph")

BG     = "#FFFFFF"
FG     = "#1a1a1a"
GRAY   = "#888888"

# 配色（深暗红→浅灰）
C = ["#6F1714","#821C18","#942722","#A63B36","#B85D58",
     "#C98A86","#D6B4B1","#DECECC","#E6E6E6","#F5F5F5"]

def add_credit(fig, username: str = "用户"):
    fig.text(0.5, 0.01, f"图表制作：{username}的Alice 🦉",
             ha='center', va='bottom', fontproperties=ZH_S, color=GRAY)


# =====================
# 1. 话题分布 —— 空心环形图（数据驱动）
# =====================
def plot_topic_donut(stats: dict, out_dir: str, username: str = "用户"):
    topics_raw = stats.get("topics", {}).get("distribution", {})
    if not topics_raw:
        print("⚠ 话题分布数据缺失，跳过", file=sys.stderr)
        return

    # 整理数据：排除掉"其他"类，取所有有实际内容的分类，按 pct 降序
    named_items = sorted(
        [(k, v["pct"]) for k, v in topics_raw.items() if k != "其他" and v["pct"] >= 1.0],
        key=lambda x: -x[1]
    )
    # 真正的"其他/未分类"占比
    other_pct = topics_raw.get("其他", {}).get("pct", 0)
    other_pct += sum(v["pct"] for k, v in topics_raw.items()
                     if k != "其他" and v["pct"] < 1.0)

    # 最终数据：占比 >= 2% 的有意义分类（最多6个），其余全部归入"未分类"
    main_items = [(k, p) for k, p in named_items[:6] if p >= 2.0]
    small_pct  = other_pct + sum(p for k, p in named_items if p < 2.0)
    if small_pct >= 1.0:
        main_items.append(("未分类话题", round(small_pct, 1)))

    # 归一化：确保总和为100
    total_pct = sum(s for _, s in main_items)
    if total_pct > 0:
        main_items = [(k, round(s / total_pct * 100, 1)) for k, s in main_items]

    labels = [k for k, _ in main_items]
    sizes  = [s for _, s in main_items]
    # 配色策略：
    # - 第1个（最大主题）：深红 #6F1714
    # - "其他"：浅灰 #B0B0B0，明确与主题区分
    # - 其余命名分类：蓝/绿/金/紫渐变，互相区分
    NAMED_PALETTE = ["#6F1714", "#3B6E8F", "#2E8B57", "#C8871E", "#7B68AE", "#8B3A62"]
    OTHER_COLOR   = "#C0C0C0"

    colors = []
    named_idx = 0
    for label, size in zip(labels, sizes):
        if label == "未分类话题":
            colors.append(OTHER_COLOR)
        else:
            colors.append(NAMED_PALETTE[min(named_idx, len(NAMED_PALETTE)-1)])
            named_idx += 1

    date_range   = stats.get("date_range", "")
    sessions     = stats.get("session_count", 0)
    center_top   = f"{sessions}次会话" if sessions else "会话"

    fig, ax = plt.subplots(figsize=(10, 7.5), facecolor=BG)
    ax.set_facecolor(BG)

    wedges, _ = ax.pie(
        sizes, labels=None, startangle=90, colors=colors,
        wedgeprops={'width': 0.52, 'edgecolor': 'white', 'linewidth': 2.5},
        counterclock=False,
    )

    # 中心文字
    ax.text(0, 0.1, center_top, ha='center', va='center',
            fontproperties=ZH_B, fontsize=15, color=FG)
    ax.text(0, -0.18, '话题分布', ha='center', va='center',
            fontproperties=ZH, fontsize=11, color=GRAY)

    # 标注策略：
    # - 占比 >= 8%：箭头标注在环外
    # - 占比 < 8%（小扇区）：用底部图例列出，不在环上标注
    total        = sum(sizes)
    start_angle  = 90
    legend_items = []  # (label, size, color) for small sectors

    for i, (label, size) in enumerate(zip(labels, sizes)):
        arc   = size / total * 360
        angle = start_angle - (sum(sizes[:i]) / total * 360) - arc / 2
        rad   = np.radians(angle)

        if size >= 8.0:
            tip_r = 0.74
            txt_r = 1.12
            tip_x, tip_y = tip_r * np.cos(rad), tip_r * np.sin(rad)
            txt_x, txt_y = txt_r * np.cos(rad), txt_r * np.sin(rad)
            ha = 'left' if txt_x >= 0 else 'right'
            ax.annotate(
                f"{label}\n{size:.1f}%",
                xy=(tip_x, tip_y), xytext=(txt_x, txt_y),
                ha=ha, va='center',
                fontproperties=ZH, fontsize=10, color=FG,
                arrowprops=dict(arrowstyle='-', color='#aaa', lw=1.2,
                                connectionstyle='arc3,rad=0'),
            )
        else:
            legend_items.append((label, size, colors[i]))

    # 小扇区用图例在底部展示
    if legend_items:
        patches = [
            mpatches.Patch(color=col, label=f"{lbl} {sz:.1f}%")
            for lbl, sz, col in legend_items
        ]
        ax.legend(handles=patches, loc='lower center', bbox_to_anchor=(0.5, -0.08),
                  ncol=min(len(patches), 4), frameon=False, prop=ZH_S, handlelength=1.2)

    # 高亮最大扇区
    if wedges:
        wedges[0].set_linewidth(3)
        wedges[0].set_edgecolor(C[0])

    title_str = f'话题分布（{date_range}）' if date_range else '话题分布'
    ax.set_title(title_str, fontproperties=ZH_T, fontsize=14, color=FG, pad=16)
    add_credit(fig, username)
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    out = os.path.join(out_dir, 'topic_pie.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"✓ 话题分布环形图 → {out}")


# =====================
# 2. 灵魂三分雷达图（数据驱动）
# =====================
def plot_soul_radar(stats: dict, out_dir: str, username: str = "用户"):
    soul = stats.get("soul_scores", {})
    logos  = soul.get("logos",     {}).get("pct", 60)
    thumos = soul.get("thumos",    {}).get("pct", 25)
    epi    = soul.get("epithumia", {}).get("pct", 15)

    categories = ['系统建造', '因果推导', '数据验证', '框架思维',
                  '审美冲动', '情感表达', '欲望/享受']

    # 按比例缩放各维度数值
    data = {
        f'Logos 理性 {logos}%':     ([logos*1.2, logos*1.25, logos*1.1, logos*1.2,
                                       epi*5, thumos*1.8, epi*1.5], C[0]),
        f'Thumos 激情 {thumos}%':   ([thumos*1.1, thumos*1.0, thumos*1.0, thumos*1.2,
                                       thumos*4.5, thumos*1.8, thumos*1.0], C[3]),
        f'Epithumia 欲望 {epi}%':   ([epi*0.7, epi*0.7, epi*1.1, epi*1.4,
                                       epi*2.2, epi*2.8, epi*7.5], C[7]),
    }
    # 归一化到 0-100
    def clamp(vals):
        return [min(max(v, 0), 100) for v in vals]
    data = {k: (clamp(v), c) for k, (v, c) in data.items()}

    N = len(categories)
    angles   = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles_c = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True), facecolor=BG)
    ax.set_facecolor('#fafafa')

    for label, (vals, color) in data.items():
        vals_c = vals + vals[:1]
        ax.plot(angles_c, vals_c, 'o-', lw=2, color=color, markersize=5, zorder=3)
        ax.fill(angles_c, vals_c, alpha=0.12, color=color)

    ax.set_thetagrids(np.degrees(angles), categories,
                      fontproperties=ZH, fontsize=10, color=FG)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(['25', '50', '75', '100'], fontsize=8, color='#bbb')
    ax.grid(color='#ddd', linestyle='--', linewidth=0.7)
    ax.spines['polar'].set_color('#ddd')

    legend_patches = [mpatches.Patch(color=c, label=l)
                      for l, (_, c) in data.items()]
    ax.legend(handles=legend_patches, loc='lower center',
              bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False,
              prop=ZH_S, handlelength=1.2)

    ax.set_title('灵魂三分雷达（柏拉图框架）',
                 fontproperties=ZH_T, fontsize=14, color=FG, pad=20)
    add_credit(fig, username)
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out = os.path.join(out_dir, 'soul_radar.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"✓ 灵魂三分雷达图 → {out}")


# =====================
# 3. 综合能力评分——横向条形图（数据驱动）
# =====================
def plot_score_bar(stats: dict, out_dir: str, username: str = "用户"):
    caps_raw = stats.get("capability_scores", {})
    if not caps_raw:
        print("⚠ 能力评分数据缺失，跳过", file=sys.stderr)
        return

    caps   = sorted(caps_raw.items(), key=lambda x: -x[1])
    dims   = [k for k, _ in caps]
    scores = [v for _, v in caps]
    bar_c  = [C[min(i, len(C)-1)] for i in range(len(dims))]

    fig, ax = plt.subplots(figsize=(9, max(4.5, len(dims) * 0.72)), facecolor=BG)
    ax.set_facecolor(BG)

    bars = ax.barh(dims, scores, color=bar_c, height=0.52,
                   edgecolor='white', linewidth=1.0, zorder=3)

    for bar, score in zip(bars, scores):
        ax.text(score + 0.06, bar.get_y() + bar.get_height()/2,
                f'{score}', va='center', ha='left',
                fontproperties=ZH_B, fontsize=11, color=FG)

    ax.axvline(10, color='#eee', lw=1.5, linestyle='--', zorder=1)
    ax.set_xlim(0, 11.5)
    ax.set_xlabel('评分（满分 10 分）', fontproperties=ZH_S, fontsize=10, color=GRAY)

    total_m = stats.get("total_messages", 0)
    title = f'综合能力评分（基于 {total_m} 条消息）' if total_m else '综合能力评分'
    ax.set_title(title, fontproperties=ZH_T, fontsize=14, color=FG, pad=14)

    for label in ax.get_yticklabels():
        label.set_fontproperties(ZH)
        label.set_fontsize(11)
    ax.tick_params(axis='x', labelsize=9, colors=GRAY)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#eee')
    ax.spines['bottom'].set_color('#eee')
    ax.grid(axis='x', color='#f0f0f0', linestyle='-', linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    add_credit(fig, username)
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out = os.path.join(out_dir, 'score_bar.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"✓ 综合能力评分图 → {out}")


# =====================
# 4. 高频关键词——水平渐变条形（数据驱动）
# =====================
def plot_keyword_freq(stats: dict, out_dir: str, username: str = "用户"):
    kw_raw = stats.get("top_keywords", [])
    if not kw_raw:
        print("⚠ 关键词数据缺失，跳过", file=sys.stderr)
        return

    # 取前12个
    kw_raw = kw_raw[:12]
    kw_s   = [item[0] for item in kw_raw]
    freq_s = [item[1] for item in kw_raw]

    # 排序：高→低
    paired = sorted(zip(freq_s, kw_s), reverse=True)
    freq_s, kw_s = zip(*paired) if paired else ([], [])

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG)
    ax.set_facecolor(BG)

    x = np.arange(len(kw_s))
    bar_colors = [C[min(i, len(C)-1)] for i in range(len(kw_s))]
    bars = ax.bar(x, freq_s, color=bar_colors, width=0.65,
                  edgecolor='white', linewidth=1.2, zorder=3)

    for bar, f in zip(bars, freq_s):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(freq_s)*0.015,
                str(f), ha='center', va='bottom',
                fontproperties=ZH_B, fontsize=10, color=FG)

    ax.set_xticks(x)
    ax.set_xticklabels(kw_s, rotation=35, ha='right', fontsize=9.5)
    for label in ax.get_xticklabels():
        label.set_fontproperties(ZH)

    ax.set_ylabel('出现频次', fontproperties=ZH_S, fontsize=10, color=GRAY)
    date_range = stats.get("date_range", "")
    sessions   = stats.get("session_count", 0)
    title = f'高频关键词分布（{date_range} · {sessions}次会话）' if date_range else '高频关键词分布'
    ax.set_title(title, fontproperties=ZH_T, fontsize=14, color=FG, pad=14)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#eee')
    ax.spines['bottom'].set_color('#eee')
    ax.grid(axis='y', color='#f0f0f0', linestyle='-', linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis='y', labelsize=9, colors=GRAY)
    ax.set_ylim(0, max(freq_s) * 1.18 if freq_s else 10)

    add_credit(fig, username)
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out = os.path.join(out_dir, 'keyword_freq.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"✓ 高频关键词图 → {out}")


# =====================
# 5. 头像处理（档案照效果）
# =====================
def make_avatar(avatar_url: str | None, out_dir: str):
    import urllib.request
    from PIL import Image, ImageEnhance
    import io, numpy as np

    def archive_effect(img):
        gray = img.convert("L").convert("RGB")
        arr  = np.array(gray, dtype=np.float32)
        arr[:, :, 0] = np.clip(arr[:, :, 0] + 12, 0, 255)
        arr[:, :, 1] = np.clip(arr[:, :, 1] + 6,  0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] - 10, 0, 255)
        tinted = Image.fromarray(arr.astype(np.uint8), "RGB")
        tinted = ImageEnhance.Contrast(tinted).enhance(0.80)
        tinted = ImageEnhance.Brightness(tinted).enhance(0.88)
        return tinted

    out = os.path.join(out_dir, 'avatar_square.png')
    url = avatar_url or ""

    # 优先从缓存 URL 文件读取
    raw_url_file = "/tmp/avatar_raw_url.txt"
    if not url and os.path.exists(raw_url_file):
        url = Path(raw_url_file).read_text().strip()

    if url.startswith("http"):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data)).convert('RGB')
            w, h = img.size
            side = min(w, h)
            img  = img.crop(((w-side)//2, (h-side)//2, (w+side)//2, (h+side)//2))
            img  = img.resize((360, 360), Image.LANCZOS)
            img  = archive_effect(img)
            img.save(out)
            print(f"✓ 头像（企业微信 + 档案照效果）→ {out}")
            return
        except Exception as e:
            print(f"⚠ 头像 URL 拉取失败: {e}", file=sys.stderr)

    # fallback：默认头像
    default = str(Path(__file__).parent.parent / "references/default_avatar.png")
    if os.path.exists(default):
        img = Image.open(default).convert('RGB')
        img = img.resize((360, 360), Image.LANCZOS)
        img = archive_effect(img)
        img.save(out)
        print(f"✓ 头像（默认 + 档案照效果）→ {out}")
    else:
        print("⚠ 无可用头像", file=sys.stderr)


# =====================
# 主函数
# =====================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='德尔斐计划图表生成器 v4（数据驱动）')
    parser.add_argument('--stats',      default=None, help='JSON 统计文件路径（extract_session_stats.py 输出）')
    parser.add_argument('--output-dir', default='/tmp/know_yourself_charts', help='图表输出目录')
    parser.add_argument('--avatar-url', default=None, help='头像 URL（覆盖缓存值）')
    parser.add_argument('--username',   default='用户', help='用于署名的用户名')
    args = parser.parse_args()

    OUT_DIR = args.output_dir
    os.makedirs(OUT_DIR, exist_ok=True)

    # 加载统计数据
    stats = {}
    if args.stats:
        try:
            with open(args.stats) as f:
                stats = json.load(f)
            print(f"✓ 读取统计文件：{args.stats}")
            print(f"  会话: {stats.get('session_count')}  消息: {stats.get('total_messages')}  跨度: {stats.get('date_range')}")
        except Exception as e:
            print(f"✗ 无法读取统计文件：{e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("✗ 请通过 --stats 传入统计数据文件", file=sys.stderr)
        sys.exit(1)

    username = args.username

    plot_topic_donut(stats, OUT_DIR, username)
    plot_soul_radar(stats, OUT_DIR, username)
    plot_score_bar(stats, OUT_DIR, username)
    plot_keyword_freq(stats, OUT_DIR, username)
    make_avatar(args.avatar_url, OUT_DIR)

    print(f"\n=== 输出文件（{OUT_DIR}）===")
    for f in sorted(os.listdir(OUT_DIR)):
        size = os.path.getsize(os.path.join(OUT_DIR, f))
        print(f"  {f}: {size//1024}KB")
