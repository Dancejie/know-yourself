#!/usr/bin/env python3
"""生成 RPG 风格属性雷达图，含头像、等级、经验条"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import json, base64, os
from pathlib import Path
from PIL import Image
import urllib.request
import io

# ── 字体 ────────────────────────────────────────────────────────────────
font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_bold = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
fm.fontManager.addfont(font_path)
fm.fontManager.addfont(font_bold)
ZH   = fm.FontProperties(fname=font_path, size=11)
ZHB  = fm.FontProperties(fname=font_bold, size=12)
ZHS  = fm.FontProperties(fname=font_path, size=9)

# ── 配色（档案深色系） ─────────────────────────────────────────────────
BG   = "#1a1008"      # 深棕黑背景
CARD = "#2a1a0e"      # 面板底色
GRID = "#3a2a1e"      # 雷达网格
GOLD = "#c8a86e"      # 金色文字
RED  = "#8b2020"      # 深红填充
RED2 = "#c04040"      # 浅红边线
TEXT = "#e8d8b8"      # 主文字
DIM  = "#7a6a5a"      # 次要文字

RARITY_COLOR = {
    "隐藏": "#c0392b",
    "传说": "#e67e22",
    "史诗": "#9b59b6",
    "稀有": "#4a90d9",
    "普通": "#888888",
}

def load_avatar(url: str, size=100):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=5).read()
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        # 圆形裁剪
        mask = Image.new("L", (size, size), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(mask).ellipse((0, 0, size-1, size-1), fill=255)
        img.putalpha(mask)
        return np.array(img) / 255.0
    except Exception as e:
        print(f"  [avatar] 加载失败: {e}")
        return None

def draw_radar(ax, labels, values, max_val=100):
    N = len(labels)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]
    vals = [v/max_val for v in values]
    vals += vals[:1]

    # 网格
    for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
        pts = [[r*np.cos(a), r*np.sin(a)] for a in np.linspace(0, 2*np.pi, 100)]
        px, py = zip(*pts)
        ax.plot(px, py, color=GRID, linewidth=0.5, zorder=1)
    for a in angles[:-1]:
        ax.plot([0, np.cos(a)], [0, np.sin(a)], color=GRID, linewidth=0.5, zorder=1)

    # 填充
    x = [v*np.cos(a) for v, a in zip(vals, angles)]
    y = [v*np.sin(a) for v, a in zip(vals, angles)]
    ax.fill(x, y, alpha=0.35, color=RED, zorder=2)
    ax.plot(x, y, color=RED2, linewidth=1.5, zorder=3)
    ax.scatter(x[:-1], y[:-1], color=RED2, s=30, zorder=4)

    # 标签
    for i, (label, angle, val) in enumerate(zip(labels, angles[:-1], values)):
        r = 1.18
        lx, ly = r*np.cos(angle), r*np.sin(angle)
        ha = "center"
        if np.cos(angle) > 0.3: ha = "left"
        elif np.cos(angle) < -0.3: ha = "right"
        ax.text(lx, ly, f"{label}\n{val}", ha=ha, va="center",
                fontproperties=ZHS, color=TEXT, zorder=5,
                fontsize=8.5)

    ax.set_xlim(-1.4, 1.4)
    ax.set_ylim(-1.4, 1.4)
    ax.set_aspect("equal")
    ax.axis("off")

def exp_bar_text(exp, exp_next, width=20):
    filled = int((exp / exp_next) * width)
    return "█" * filled + "░" * (width - filled)

def main():
    char_path = "/home/node/.openclaw/workspace/memory/character_stats.json"
    char = json.loads(Path(char_path).read_text())
    p = char["profile"]
    attrs = char["attributes"]
    titles = char["titles"]

    labels = [v["label"] for v in attrs.values()]
    values = [v["value"] for v in attrs.values()]
    N = len(labels)

    avatar_url = "https://wework.qpic.cn/wwpic3az/382250_oTmlCLG4QrSRwmq_1759133127/0"

    # ── 画布 ────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(13, 8.5), facecolor=BG)

    # 左列：头像 + 基础信息 + 称号
    ax_info = fig.add_axes([0.0, 0.0, 0.38, 1.0])
    ax_info.set_facecolor(CARD)
    ax_info.axis("off")

    # 装饰线
    for y in [0.97, 0.03]:
        ax_info.axhline(y, color=GOLD, linewidth=0.8, alpha=0.6)

    # 头像（左上角）
    avatar = load_avatar(avatar_url, size=120)
    if avatar is not None:
        ax_av = fig.add_axes([0.02, 0.76, 0.13, 0.19])
        ax_av.imshow(avatar)
        ax_av.axis("off")
        circle = plt.Circle((0.5, 0.5), 0.49, transform=ax_av.transAxes,
                             fill=False, color=GOLD, linewidth=2.0)
        ax_av.add_patch(circle)

    # 职业 & 原型（头像右侧）
    ax_info.text(0.65, 0.94, p["class"], fontproperties=ZHB,
                 color=GOLD, fontsize=11, ha="center", va="center",
                 transform=ax_info.transAxes)
    ax_info.text(0.65, 0.895, p["archetype"].split("·")[-1].strip(), fontproperties=ZHS,
                 color=DIM, fontsize=7, ha="center", va="center",
                 transform=ax_info.transAxes)

    # 等级
    ax_info.text(0.5, 0.825, f"Lv. {p['level']}", fontproperties=ZHB,
                 color=TEXT, fontsize=22, ha="center", va="center",
                 transform=ax_info.transAxes)

    # 经验条
    exp_next = 100 + (p["level"] - 1) * 50
    bar = exp_bar_text(p["exp"], exp_next, width=18)
    ax_info.text(0.58, 0.745, f"EXP  {p['exp']}/{exp_next}", fontproperties=ZHS,
                 color=DIM, fontsize=8, ha="center", va="center",
                 transform=ax_info.transAxes)
    ax_info.text(0.58, 0.700, bar, fontproperties=ZHS,
                 color=RED2, fontsize=8.5, ha="center", va="center",
                 transform=ax_info.transAxes, family="monospace")

    # 分隔
    ax_info.axhline(0.672, color=GRID, linewidth=0.5, xmin=0.05, xmax=0.95)

    # 称号
    ax_info.text(0.1, 0.645, "称号", fontproperties=ZHB,
                 color=GOLD, fontsize=9.5, va="center",
                 transform=ax_info.transAxes)
    ty = 0.600
    for t in reversed(titles):
        rcolor = RARITY_COLOR.get(t.get("rarity","普通"), "#888")
        name = t["name"]
        rarity = t.get("rarity","普通")
        ax_info.text(0.1, ty, f"◆ {name}", fontproperties=ZHB,
                     color=rcolor, fontsize=9, va="center",
                     transform=ax_info.transAxes)
        ax_info.text(0.92, ty, rarity, fontproperties=ZHS,
                     color=rcolor, fontsize=7, va="center", ha="right",
                     transform=ax_info.transAxes)
        ty -= 0.052
        desc = t.get("desc","")
        if len(desc) > 22:
            desc = desc[:22] + "…"
        ax_info.text(0.12, ty + 0.010, desc, fontproperties=ZHS,
                     color=DIM, fontsize=6.5, va="center",
                     transform=ax_info.transAxes)
        ty -= 0.042

    # 分隔
    ax_info.axhline(ty + 0.018, color=GRID, linewidth=0.5, xmin=0.05, xmax=0.95)

    # 灵魂三分 — 从 character_stats.json soul 字段读取
    soul_data = [
        ("Logos  理性",    char.get("soul",{}).get("logos",    {}).get("value", 75),  "#6b8bae"),
        ("Thumos 激情",   char.get("soul",{}).get("thumos",   {}).get("value", 18),  "#ae6b6b"),
        ("Epithumia 欲望", char.get("soul",{}).get("epithumia",{}).get("value", 7),   "#6bae7a"),
    ]
    sy = ty - 0.015
    ax_info.text(0.1, sy, "灵魂三分", fontproperties=ZHB,
                 color=GOLD, fontsize=9.5, va="center",
                 transform=ax_info.transAxes)
    sy -= 0.060
    for soul_label, soul_val, soul_color in soul_data:
        ax_info.text(0.1, sy, soul_label, fontproperties=ZHS,
                     color=soul_color, fontsize=8, va="center",
                     transform=ax_info.transAxes)
        ax_info.text(0.92, sy, f"{soul_val}%", fontproperties=ZHS,
                     color=soul_color, fontsize=8, va="center", ha="right",
                     transform=ax_info.transAxes)
        sy -= 0.048

    # 档案底部
    ax_info.text(0.5, 0.015, "DELPHIC SYSTEMS · DS-PN-2026-DANGSI",
                 fontproperties=ZHS, color=DIM, fontsize=6,
                 ha="center", va="center", transform=ax_info.transAxes)

    # 右列：雷达图占满右侧（不留底部空白）
    ax_radar = fig.add_axes([0.40, 0.0, 0.58, 1.0])
    ax_radar.set_facecolor(BG)

    # 雷达图绘制区域在上方 70%
    # 用子坐标系模拟：先在 ax_radar 上画雷达，属性列表画在下方
    # 因为 add_axes 不能嵌套，改为：把雷达偏移到上方，属性标注在底部 axes 文本
    ax_radar.set_xlim(0, 1)
    ax_radar.set_ylim(0, 1)
    ax_radar.axis("off")

    # 标题
    ax_radar.text(0.5, 0.99, "能力雷达", fontproperties=ZHB, color=GOLD,
                  fontsize=12, ha="center", va="top", transform=ax_radar.transAxes)

    # 在 ax_radar 内部手动画雷达（坐标系映射到上方 65% 区域）
    N = len(labels)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles_closed = angles + angles[:1]
    vals_norm = [v/100 for v in values]
    vals_closed = vals_norm + vals_norm[:1]

    # 中心和半径（在 axes 坐标系中）
    cx, cy, r = 0.5, 0.57, 0.28

    # 网格圈
    for ring in [0.2, 0.4, 0.6, 0.8, 1.0]:
        xs = [cx + ring*r*np.cos(a - np.pi/2) for a in np.linspace(0, 2*np.pi, 100)]
        ys = [cy + ring*r*np.sin(a - np.pi/2) for a in np.linspace(0, 2*np.pi, 100)]
        ax_radar.plot(xs, ys, color=GRID, linewidth=0.5, transform=ax_radar.transAxes, zorder=1)
    for a in angles:
        ax_radar.plot([cx, cx + r*np.cos(a - np.pi/2)],
                      [cy, cy + r*np.sin(a - np.pi/2)],
                      color=GRID, linewidth=0.5, transform=ax_radar.transAxes, zorder=1)

    # 填充多边形
    xs = [cx + v*r*np.cos(a - np.pi/2) for v, a in zip(vals_closed, angles_closed)]
    ys = [cy + v*r*np.sin(a - np.pi/2) for v, a in zip(vals_closed, angles_closed)]

    poly = MplPolygon(list(zip(xs, ys)), closed=True, facecolor=RED, alpha=0.35,
                      transform=ax_radar.transAxes, zorder=2)
    ax_radar.add_patch(poly)
    ax_radar.plot(xs, ys, color=RED2, linewidth=1.8, transform=ax_radar.transAxes, zorder=3)
    # 节点
    for x_, y_ in zip(xs[:-1], ys[:-1]):
        ax_radar.plot(x_, y_, 'o', color=RED2, markersize=4,
                      transform=ax_radar.transAxes, zorder=4)

    # 标签
    label_r = r * 1.22
    for label, angle, val in zip(labels, angles, values):
        lx = cx + label_r * np.cos(angle - np.pi/2)
        ly = cy + label_r * np.sin(angle - np.pi/2)
        ha = "center"
        if np.cos(angle - np.pi/2) > 0.25: ha = "left"
        elif np.cos(angle - np.pi/2) < -0.25: ha = "right"
        ax_radar.text(lx, ly, f"{label}\n{val}",
                      fontproperties=ZHS, color=TEXT, fontsize=8,
                      ha=ha, va="center", transform=ax_radar.transAxes, zorder=5)

    # 属性数值列表（底部 25%，4列）
    cols = 4
    items = list(zip(labels, values))
    for i, (label, val) in enumerate(items):
        col = i % cols
        row = i // cols
        x0 = 0.04 + col * 0.245
        y0 = 0.245 - row * 0.115   # 起始位置上移
        vcolor = RED2 if val >= 80 else ("#c08060" if val >= 60 else DIM)
        bar_w = int(val / 5)
        bar_t = "█" * bar_w + "░" * (20 - bar_w)
        ax_radar.text(x0, y0, f"{label}  {val}", fontproperties=ZHB,
                      color=vcolor, fontsize=8.5, va="center",
                      transform=ax_radar.transAxes)
        ax_radar.text(x0, y0 - 0.052, bar_t, fontproperties=ZHS,
                      color=vcolor, fontsize=6.5, va="center",
                      transform=ax_radar.transAxes, family="monospace", alpha=0.8)

    out = "/tmp/rpg_radar.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0,
                facecolor=BG, edgecolor="none")
    plt.close()

    # 裁掉残余背景边距
    img = Image.open(out).convert("RGB")
    arr = np.array(img)
    bg_color = [26, 16, 8]
    tol = 20

    def is_bg_row(row):
        return all(abs(int(p[0])-bg_color[0]) < tol and
                   abs(int(p[1])-bg_color[1]) < tol and
                   abs(int(p[2])-bg_color[2]) < tol for p in row)

    top = 0
    for row in arr:
        if is_bg_row(row): top += 1
        else: break
    bot = 0
    for row in reversed(arr):
        if is_bg_row(row): bot += 1
        else: break
    h = arr.shape[0]
    if top > 0 or bot > 0:
        crop = img.crop((0, top, img.width, h - bot))
        crop.save(out)
        print(f"  裁剪: 顶部 -{top}px 底部 -{bot}px → {crop.size}")
    print(f"✓ 雷达图 → {out}")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    main()
