#!/usr/bin/env python3
"""
德尔斐计划 — 文件服务器
支持静态文件访问 + POST /api/destruct 真实销毁档案文件。

用法：
    python3 fileserver.py [--port 8899] [--public-dir ./public]

健康检查：
    GET /health → {"ok": true}

销毁接口：
    POST /api/destruct
    body: {"file": "persona-xxx.html", "token": "<sha256前16位>"}
    → {"ok": true}  / {"ok": false, "error": "..."}
"""

import argparse
import hashlib
import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse


class ArchiveHandler(SimpleHTTPRequestHandler):
    public_dir: str = "."

    def log_message(self, fmt, *args):
        # 简化日志：只打印非 200 请求
        code = args[1] if len(args) > 1 else "?"
        if str(code) not in ("200", "304"):
            print(f"[fileserver] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {"ok": True, "public_dir": self.public_dir})
            return
        # 静态文件：从 public_dir 提供
        self.directory = self.public_dir
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/destruct":
            self._handle_destruct()
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def _handle_destruct(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except Exception:
            self._json(400, {"ok": False, "error": "invalid JSON"})
            return

        filename = body.get("file", "")
        token    = body.get("token", "")

        # 安全校验：文件名不能包含路径穿越
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            self._json(400, {"ok": False, "error": "invalid filename"})
            return

        # token 校验：sha256(filename)[:16]
        expected = hashlib.sha256(filename.encode()).hexdigest()[:16]
        if token != expected:
            self._json(403, {"ok": False, "error": "invalid token"})
            return

        target = Path(self.public_dir) / filename
        if not target.exists():
            # 文件已不存在也视为成功（幂等）
            self._json(200, {"ok": True, "note": "already gone"})
            return

        try:
            target.unlink()
            print(f"[fileserver] 已销毁：{filename}", flush=True)
            self._json(200, {"ok": True})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="德尔斐计划文件服务器")
    parser.add_argument("--port",       type=int, default=8899,   help="监听端口（默认 8899）")
    parser.add_argument("--public-dir", default="~/.openclaw/workspace/public",
                        help="静态文件目录")
    args = parser.parse_args()

    public_dir = os.path.expanduser(args.public_dir)
    os.makedirs(public_dir, exist_ok=True)

    ArchiveHandler.public_dir = public_dir

    server = HTTPServer(("0.0.0.0", args.port), ArchiveHandler)
    print(f"[fileserver] 启动：http://0.0.0.0:{args.port}  public={public_dir}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[fileserver] 已停止", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
