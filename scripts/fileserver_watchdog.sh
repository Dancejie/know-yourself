#!/bin/bash
# fileserver 守护进程 — 每30秒检查，挂了自动重启
WORKSPACE="/home/node/.openclaw/workspace"
PORT=8899
LOG="/tmp/fileserver.log"

while true; do
  if ! curl -s -o /dev/null -w "%{http_code}" "http://10.40.123.131:${PORT}/" | grep -q "200"; then
    echo "[$(date '+%H:%M:%S')] fileserver 不响应，重启中..." >> /tmp/watchdog.log
    pkill -f "fileserver.py" 2>/dev/null
    sleep 1
    cd "${WORKSPACE}/public" && \
      nohup python3 ../skills/know-yourself/scripts/fileserver.py --port ${PORT} >> "${LOG}" 2>&1 &
    echo "[$(date '+%H:%M:%S')] 已重启 pid=$!" >> /tmp/watchdog.log
  fi
  sleep 30
done
