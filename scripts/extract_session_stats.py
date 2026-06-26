#!/usr/bin/env python3
"""
extract_session_stats.py  v2.0
从 OpenClaw session JSONL（v3 格式）提取行为指纹统计数据。

用法：
    python3 extract_session_stats.py <session_dir_or_file> [--days N] [--output path]

输出：JSON 格式的行为统计摘要（写入 --output 或 stdout）。

v3 JSONL 格式说明：
  每行一个 JSON 对象，类型通过顶层 "type" 字段区分：
  - type=session   → 会话元数据（首行）
  - type=message   → 对话消息，内容在 message.role / message.content
  - 其他 type      → 系统事件，忽略
"""

import json
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import re


# ──────────────────────────────────────────────────────────
# 1. JSONL 加载（v3 格式）
# ──────────────────────────────────────────────────────────

def load_messages(path: str, days: int | None = None, since_ts: float | None = None) -> list[dict]:
    """
    加载指定路径（目录或单文件）的 JSONL 日志，返回用户消息列表。

    过滤规则（任一满足即过滤）：
      - days 参数：只保留最近 N 天的消息
      - since_ts：只保留 timestamp > since_ts（Unix 秒）的消息

    返回列表每项包含：
      { "role", "text", "timestamp" (datetime), "session_id" }
    """
    cutoff_dt = None
    if days is not None:
        cutoff_dt = datetime.now(tz=timezone.utc) - timedelta(days=days)
    if since_ts is not None:
        since_dt = datetime.fromtimestamp(since_ts, tz=timezone.utc)
        cutoff_dt = max(cutoff_dt, since_dt) if cutoff_dt else since_dt

    files = []
    if os.path.isdir(path):
        for f in sorted(os.listdir(path)):
            if f.endswith(".jsonl"):
                full = os.path.join(path, f)
                # 跳过 deleted/reset 会话
                if ".deleted." not in f and ".reset." not in f:
                    files.append(full)
    elif os.path.isfile(path):
        files = [path]
    else:
        print(f"[error] 路径不存在：{path}", file=sys.stderr)
        return []

    messages = []
    for fpath in files:
        session_id = os.path.basename(fpath).replace(".jsonl", "")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # 只处理 type=message
                    if obj.get("type") != "message":
                        continue

                    msg = obj.get("message", {})
                    role = msg.get("role", "")
                    if role not in ("user", "human"):
                        continue

                    # 时间戳：外层 timestamp（ISO 字符串）或 message.timestamp（毫秒整数）
                    ts_raw = obj.get("timestamp") or msg.get("timestamp")
                    dt = _parse_timestamp(ts_raw)

                    if cutoff_dt and dt and dt < cutoff_dt:
                        continue

                    text = _extract_text(msg)
                    if not text.strip():
                        continue

                    messages.append({
                        "role": role,
                        "text": text,
                        "timestamp": dt,
                        "session_id": session_id,
                    })
        except Exception as e:
            print(f"[warn] 无法读取 {fpath}: {e}", file=sys.stderr)

    return messages


def _parse_timestamp(raw) -> datetime | None:
    if raw is None:
        return None
    try:
        if isinstance(raw, (int, float)):
            # 毫秒整数（>1e10）转换为秒
            ts = raw / 1000 if raw > 1e10 else raw
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(raw, str):
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        pass
    return None


def _extract_text(msg: dict) -> str:
    """从 message 对象提取纯文本，兼容 content 为字符串或 list。
    同时剥离 OpenClaw 注入的 untrusted metadata 头部块。
    """
    content = msg.get("content") or msg.get("text") or ""
    if isinstance(content, str):
        raw = content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
        raw = "\n".join(p for p in parts if p)
    else:
        return ""

    # 剥离 OpenClaw 注入的系统元数据头部：
    # 格式为 "Conversation info (untrusted metadata):\n```json\n{...}\n```\n"
    # 或    "Sender (untrusted metadata):\n```json\n{...}\n```\n"
    # 后面跟着时间戳 "[Mon 2026-04-20 ...]" 再是真实用户内容
    stripped = re.sub(
        r"(?:Conversation info|Sender)\s+\(untrusted metadata\)[^\n]*\n```[^\n]*\n[\s\S]+?```\n?",
        "",
        raw,
    ).strip()

    # 再去掉可能残留的时间戳行首 "[Mon 2026-04-20 15:46 GMT+8] "
    stripped = re.sub(r"^\[[A-Za-z]{3}\s+\d{4}-\d{2}-\d{2}\s+[\d:]+\s+GMT[^\]]*\]\s*", "", stripped)

    return stripped if stripped else raw


# ──────────────────────────────────────────────────────────
# 2. 统计分析函数
# ──────────────────────────────────────────────────────────

def analyze_time_pattern(messages: list[dict]) -> dict:
    """分析活跃时段分布（Asia/Shanghai GMT+8）。"""
    hour_counts = Counter()
    for msg in messages:
        dt = msg.get("timestamp")
        if dt:
            # 转为 GMT+8
            local_hour = (dt.hour + 8) % 24
            hour_counts[local_hour] += 1

    if not hour_counts:
        return {
            "peak_hours": "21-24",
            "pattern_label": "数据不足",
            "hour_distribution": {},
        }

    # Top-3 活跃小时
    peak_hours_list = [h for h, _ in hour_counts.most_common(3)]
    peak_hours_str = f"{min(peak_hours_list)}-{max(peak_hours_list)+1}"

    # 时段分类（按消息数加权）
    def classify(h):
        if 6 <= h < 12:
            return "morning"
        elif 12 <= h < 18:
            return "afternoon"
        elif 18 <= h < 23:
            return "evening"
        else:
            return "late_night"

    # 按时段合并计数
    period_counts = Counter()
    for h, cnt in hour_counts.items():
        period_counts[classify(h)] += cnt

    dominant = period_counts.most_common(1)[0][0]
    labels = {
        "morning":    "晨型思考者",
        "afternoon":  "白昼工作者",
        "evening":    "夜间活跃者",
        "late_night": "深夜思考者",
    }

    return {
        "peak_hours": peak_hours_str,
        "pattern_label": labels.get(dominant, "全天型"),
        "hour_distribution": dict(hour_counts),
    }


def analyze_topics(messages: list[dict]) -> dict:
    """关键词分类统计话题分布（互斥，按优先级首次命中）。"""
    # 按优先级排列，越靠前越优先（防止"策略"同时命中多类）
    topic_rules = [
        ("AI/大模型",   [
            # 模型与框架
            "模型", "AI", "大模型", "prompt", "Prompt", "agent", "Agent",
            "LLM", "GPT", "Claude", "Gemini", "Kimi", "Qwen", "embedding",
            "推理", "微调", "fine-tune", "RAG", "向量", "召回", "检索",
            # Prompt Engineering
            "PE", "PE ", " PE", "tagging", "打标", "Tagging", "标注",
            "skill", "Skill", "workflow", "Workflow", "few-shot", "CoT",
            "热点", "打分", "改写", "预热", "query", "Query",
            # AI 系统与工程
            "OpenClaw", "clawhub", "SkillHub", "session", "Session",
            "cron", "Cron", "sub-agent", "subagent", "sandbox",
            "redoc", "Redoc", "REDoc", "文档", "档案", "SKILL.md",
            "知识库", "向量库", "语义搜索", "分类器", "意图",
            # 数据与评测
            "数据集", "评测", "badcase", "标签", "分类", "PE重构",
            "批量", "并发", "pipeline", "流程", "调用", "token", "Token",
            "context", "Context", "memory", "Memory",
        ]),
        ("投资策略",    [
            "白银", "股票", "仓位", "回撤", "止损", "期货", "收益",
            "基金", "涨", "跌", "交易", "持仓", "仓差", "布林",
            "技术分析", "量化", "回测", "K线", "均线", "筹码",
            "做多", "做空", "杠杆", "期权", "套利", "择时",
        ]),
        ("工程工具",    [
            "代码", "脚本", "SQL", "python", "Python", "shell", "bash",
            "API", "接口", "数据库", "git", "配置", "debug",
            "npm", "node", "docker", "linux", "curl", "grep",
            "函数", "类", "变量", "报错", "异常", "traceback",
        ]),
        ("文学人文",    [
            "散文", "写作", "读书", "诗", "文章", "哲学", "历史",
            "认知", "思维", "意义", "美学", "人文", "叙事", "表达",
            "书评", "观影", "电影", "小说", "文字", "笔记",
        ]),
        ("人际情感",    [
            "她", "女生", "男生", "朋友", "对象", "恋爱", "感情",
            "喜欢", "表白", "见面", "聊天", "分手", "在一起",
            "暗恋", "相处", "孤独", "陪伴", "亲密", "信任",
        ]),
        ("生活健康",    [
            "运动", "体重", "健康", "饮食", "作息", "睡眠", "减肥",
            "跑步", "健身", "卡路里", "心率", "状态", "精力",
        ]),
        ("职业规划",    [
            "职业", "求职", "面试", "升职", "跳槽", "方向",
            "赛道", "发展", "规划", "目标", "成长", "晋升",
            "简历", "offer", "薪资", "title", "影响力",
        ]),
    ]

    topic_counts = Counter()
    for msg in messages:
        text = msg["text"]
        matched = False
        for topic, keywords in topic_rules:
            if any(kw in text for kw in keywords):
                topic_counts[topic] += 1
                matched = True
                break  # 互斥：首次命中即停
        if not matched:
            topic_counts["其他"] += 1

    total = max(sum(topic_counts.values()), 1)
    distribution = {
        k: {"pct": round(v / total * 100, 1), "trend": "stable"}
        for k, v in sorted(topic_counts.items(), key=lambda x: -x[1])
    }
    return {"distribution": distribution}


def analyze_question_style(messages: list[dict]) -> dict:
    """
    分析互动意图分类（非互斥，每条消息可命中多类）。

    分类维度：
      - 分析型：追问原因、推理、本质
      - 执行型：委托任务、要求生成/操作
      - 情感型：情绪表达、人际叙事、情感倾诉
      - 创意型：头脑风暴、假设、方案设计
      - 陈述型：同步信息、描述现状（非问句也非委托）
    """
    style_rules = [
        ("分析型",  ["为什么", "原因", "原理", "本质", "机制", "如何理解",
                     "分析", "解释", "推断", "推理", "逻辑", "说明一下"]),
        ("执行型",  ["怎么做", "如何操作", "步骤", "帮我", "生成", "写",
                     "创建", "执行", "实现", "运行", "改", "修", "做一个",
                     "给我", "帮忙", "跑一下", "配置"]),
        ("情感型",  ["感觉", "担心", "焦虑", "开心", "难过", "郁闷",
                     "压力", "困扰", "害怕", "紧张", "烦", "心情",
                     "她", "他", "喜欢", "想念", "在意", "在乎"]),
        ("创意型",  ["设计", "创造", "想象", "如果", "假设", "优化",
                     "改进", "头脑风暴", "点子", "方案", "思路"]),
    ]

    # 非互斥：一条消息可以命中多类
    style_counts = Counter()
    for msg in messages:
        text = msg["text"]
        hit = False
        for style, markers in style_rules:
            if any(m in text for m in markers):
                style_counts[style] += 1
                hit = True
        if not hit:
            style_counts["陈述型"] += 1  # 未命中任何分类 = 纯陈述/同步信息

    total = max(sum(style_counts.values()), 1)
    dist_pct = {k: round(v / total * 100, 1) for k, v in style_counts.most_common()}

    # 主导风格 = 非"陈述型"中最高的
    non_stmt = {k: v for k, v in style_counts.items() if k != "陈述型"}
    dominant = max(non_stmt, key=non_stmt.get) if non_stmt else "陈述型"

    return {
        "style_label": f"{dominant}主导，几乎无闲聊",
        "style_distribution": dist_pct,
    }


def analyze_language_style(messages: list[dict]) -> dict:
    """分析语言风格：消息长度、emoji 使用率。"""
    # _extract_text 已做过元数据清理，直接用
    texts = [msg["text"] for msg in messages if msg["text"].strip()]
    if not texts:
        return {"avg_message_length": 0, "style_label": "数据不足", "emoji_usage_pct": 0.0}

    cleaned = texts  # 已在 _extract_text 中清理过

    lengths = [len(t) for t in cleaned]
    avg_len = round(sum(lengths) / len(lengths), 1)

    emoji_pattern = re.compile(
        r"[\U0001F300-\U0001F9FF\U00002600-\U000027FF\U0001FA00-\U0001FA9F]"
    )
    emoji_count = sum(1 for t in cleaned if emoji_pattern.search(t))
    emoji_pct = round(emoji_count / len(cleaned) * 100, 1)

    if avg_len < 30:
        style = "极简短句型"
    elif avg_len < 80:
        style = "简洁直接型"
    elif avg_len < 200:
        style = "详述表达型"
    else:
        style = "长篇深度型"

    return {
        "avg_message_length": avg_len,
        "style_label": style,
        "emoji_usage_pct": emoji_pct,
        "sample_count": len(cleaned),
    }


def extract_keywords(messages: list[dict], topn: int = 20) -> list[list]:
    """
    提取高频实体关键词（中文词汇 + 英文术语）。
    不依赖 jieba，使用正则 + 自定义词典。
    """
    # 技术/领域词典（越具体越好）
    domain_vocab = [
        # AI/大模型
        "Agent", "PE", "Prompt", "LLM", "RAG", "embedding", "Claude", "GPT",
        "大模型", "智能体", "向量召回", "微调", "推理", "Tagging", "打标",
        "Skill", "MCP", "热点预热", "批量打标", "五段式", "workflow",
        # 投资
        "白银", "股票", "回撤", "止损", "仓位", "期货", "布林带",
        "回测", "交易策略", "量化",
        # 工程
        "SQL", "Python", "shell", "cron", "pipeline", "架构设计",
        "可视化", "图表", "API",
        # 文学/人文
        "散文", "写作", "读书笔记", "美丽新世界", "哲学",
        # 其他项目
        "know-yourself", "德尔斐", "内容安全", "涉政", "价值观",
    ]

    counts = Counter()
    for msg in messages:
        text = msg["text"]
        for vocab in domain_vocab:
            if vocab.lower() in text.lower():
                counts[vocab] += 1

    # 返回 [[词, 频次], ...] 格式
    return [[k, v] for k, v in counts.most_common(topn) if v > 0]


def count_sessions(path: str, since_ts: float | None = None) -> int:
    """统计有效会话数（目录模式）。"""
    if not os.path.isdir(path):
        return 1
    files = [
        f for f in os.listdir(path)
        if f.endswith(".jsonl")
        and ".deleted." not in f
        and ".reset." not in f
    ]
    if since_ts is None:
        return len(files)
    # 只统计修改时间 > since_ts 的文件
    count = 0
    for f in files:
        mtime = os.path.getmtime(os.path.join(path, f))
        if mtime > since_ts:
            count += 1
    return count


def get_date_range(messages: list[dict]) -> str:
    """返回消息的日期跨度字符串。"""
    dts = [m["timestamp"] for m in messages if m["timestamp"]]
    if not dts:
        return "N/A"
    earliest = min(dts)
    latest = max(dts)
    fmt = lambda d: d.strftime("%Y-%m-%d")
    if fmt(earliest) == fmt(latest):
        return fmt(earliest)
    return f"{fmt(earliest)} ~ {fmt(latest)}"


# ──────────────────────────────────────────────────────────
# 3. 主函数
# ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="提取 OpenClaw session 行为指纹统计（v3 JSONL 格式）"
    )
    parser.add_argument("path", help="JSONL 会话目录或单文件路径")
    parser.add_argument("--days",   type=int,   default=None,
                        help="只分析最近 N 天（不传则全量）")
    parser.add_argument("--since",  type=float, default=None,
                        help="只分析此时间戳（Unix 秒）之后的会话（增量模式）")
    parser.add_argument("--output", type=str,   default=None,
                        help="输出 JSON 文件路径（不传则打印到 stdout）")
    args = parser.parse_args()

    messages = load_messages(args.path, days=args.days, since_ts=args.since)

    if not messages:
        result = {
            "error": "未找到符合条件的用户消息",
            "path": args.path,
            "session_count": 0,
            "total_messages": 0,
        }
        out = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w") as f:
                f.write(out)
        else:
            print(out)
        sys.exit(1)

    session_count = count_sessions(args.path, since_ts=args.since)

    result = {
        "session_count":  session_count,
        "total_messages": len(messages),
        "date_range":     get_date_range(messages),
        "time_pattern":   analyze_time_pattern(messages),
        "language_style": analyze_language_style(messages),
        "question_style": analyze_question_style(messages),
        "topics":         {"distribution": analyze_topics(messages)["distribution"]},
        "top_keywords":   extract_keywords(messages),
        # 以下字段需手动/外部填入（无法从文本自动推导）
        "soul_scores": {
            "logos":     {"pct": 75, "label": "理性执政官"},
            "thumos":    {"pct": 18, "label": "战略武士"},
            "epithumia": {"pct":  7, "label": "纯粹求知者"},
        },
        "capability_scores": {
            "框架思维": 9.0, "AI工程深度": 8.5, "文学表达": 8.5,
            "数据素养": 8.0, "执行力": 7.0,
        },
        "_note": "soul_scores 和 capability_scores 为主观评估基准值，可在此文件中手动覆盖后使用。"
    }

    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = args.output
        # 写入前，若已有旧文件则备份为 _prev（供增量对比用）
        import shutil
        prev_path = output_path.replace(".json", "_prev.json")
        if os.path.exists(output_path):
            shutil.copy2(output_path, prev_path)
            print(f"  旧版统计已备份：{prev_path}", file=sys.stderr)
        with open(output_path, "w") as f:
            f.write(out)
        print(f"✓ 统计结果已写入：{output_path}", file=sys.stderr)
        print(f"  会话数：{session_count}  消息数：{len(messages)}  时间跨度：{result['date_range']}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
