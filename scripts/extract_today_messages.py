#!/usr/bin/env python3
"""
extract_today_messages.py — 从主 session JSONL 提取今日用户真实对话内容

用法：
  python3 extract_today_messages.py [--date YYYY-MM-DD] [--output /tmp/today_messages.txt]

输出：/tmp/today_messages.txt
  - 今日用户发言列表（去掉系统 metadata，只保留真实内容）
  - 适合晚间 cron 读取后生成真实洞察，而不是靠统计猜测
"""

import json
import os
import glob
import argparse
from datetime import date, datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path.home() / ".openclaw/agents/main/sessions"
DEFAULT_OUTPUT = "/tmp/today_messages.txt"


def extract_user_text(message_obj: dict) -> str | None:
    """从 message 对象中提取用户发言的纯文本。"""
    msg = message_obj.get("message", {})
    if not isinstance(msg, dict):
        return None
    if msg.get("role") != "user":
        return None

    content = msg.get("content", "")
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")

    # 去掉系统 metadata 头（Sender 元数据块）
    lines = text.split("\n")
    clean_lines = []
    skip = False
    for line in lines:
        # 跳过 ```json ... ``` 的 metadata 块
        if line.strip().startswith("```json") and "label" in text[:500]:
            skip = True
        if skip:
            if line.strip() == "```":
                skip = False
            continue
        # 跳过 [Wed 2026-xx-xx ...] 时间戳行
        if line.strip().startswith("[") and "GMT" in line:
            continue
        # 跳过 Sender (untrusted metadata): 行
        if "Sender (untrusted metadata)" in line:
            continue
        clean_lines.append(line)

    result = "\n".join(clean_lines).strip()
    return result if result else None


def get_today_messages(target_date: str) -> list[dict]:
    """
    扫描所有 JSONL，提取指定日期的用户真实消息。
    返回 [{"time": "HH:MM", "text": "..."}, ...]
    """
    messages = []

    jsonl_files = glob.glob(str(SESSIONS_DIR / "*.jsonl"))
    # 排除 trajectory.jsonl（工具调用轨迹，不含对话）
    jsonl_files = [f for f in jsonl_files if "trajectory" not in f]

    for filepath in sorted(jsonl_files):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if obj.get("type") != "message":
                        continue

                    # 检查时间戳
                    ts = obj.get("timestamp")
                    if not ts:
                        continue

                    try:
                        if isinstance(ts, (int, float)):
                            dt = datetime.fromtimestamp(ts / 1000 if ts > 1e10 else ts)
                        else:
                            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                            dt = dt.astimezone().replace(tzinfo=None)
                    except Exception:
                        continue

                    if dt.date().isoformat() != target_date:
                        continue

                    # 提取用户文本
                    text = extract_user_text(obj)
                    if text and len(text) > 5:
                        messages.append({
                            "time": dt.strftime("%H:%M"),
                            "text": text,
                        })
        except Exception as e:
            print(f"  ⚠️  读取文件失败 {filepath}: {e}")

    # 过滤 cron 触发消息和系统消息（不是真实用户发言）
    messages = [
        m for m in messages
        if not m["text"].startswith("[cron:")
        and "Pre-compaction memory flush" not in m["text"]
        and "Use the message tool if you need" not in m["text"]
        and len(m["text"].strip()) > 10
    ]

    # 去重（同一条内容可能出现多次）
    seen = set()
    unique = []
    for m in messages:
        key = m["text"][:100]
        if key not in seen:
            seen.add(key)
            unique.append(m)

    return unique


def main():
    parser = argparse.ArgumentParser(description="提取今日用户真实对话内容")
    parser.add_argument("--date", default=date.today().isoformat(), help="目标日期 YYYY-MM-DD")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="输出文件路径")
    parser.add_argument("--max-chars", type=int, default=8000, help="单条消息最大字符数（防止超长）")
    args = parser.parse_args()

    print(f"📅 提取日期：{args.date}")
    messages = get_today_messages(args.date)
    print(f"✅ 共找到 {len(messages)} 条用户消息")

    if not messages:
        output = f"[{args.date}] 今日暂无用户消息记录。\n"
    else:
        lines = [f"# 今日用户对话记录 — {args.date}\n"]
        lines.append(f"共 {len(messages)} 条消息\n\n")
        for i, m in enumerate(messages, 1):
            text = m["text"]
            if len(text) > args.max_chars:
                text = text[:args.max_chars] + "...[截断]"
            lines.append(f"## [{m['time']}] 消息 {i}\n{text}\n")
        output = "\n".join(lines)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"📄 已写入：{args.output}（{len(output)} 字符）")

    # 打印摘要供调试
    if messages:
        print("\n📋 消息摘要：")
        for m in messages[:5]:
            print(f"  [{m['time']}] {m['text'][:80]}...")
        if len(messages) > 5:
            print(f"  ... 还有 {len(messages)-5} 条")


if __name__ == "__main__":
    main()
