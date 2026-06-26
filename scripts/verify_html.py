#!/usr/bin/env python3
"""
verify_html.py — 生成后自动校验 HTML 档案完整性
用法: python3 verify_html.py /tmp/persona-dangsi-5min.html
"""
import re, sys, time
from pathlib import Path

html = Path(sys.argv[1]).read_text()
errors = []

m = re.search(r'const EXPIRE_AT=(\d+)', html)
if not m:
    errors.append("❌ EXPIRE_AT 未注入")
else:
    left = (int(m.group(1)) - int(time.time()*1000)) // 1000
    if left < 0:
        errors.append(f"❌ EXPIRE_AT 已过期")
    else:
        print(f"✅ 倒计时正常，剩余 {left}秒")

for var, ph in [('DEST_FILE', r'const DEST_FILE="([^"]+)"'),
                ('DEST_TOKEN', r'const DEST_TOKEN="([^"]+)"'),
                ('SERVER', r'const SERVER="([^"]+)"')]:
    m2 = re.search(ph, html)
    val = m2.group(1) if m2 else ''
    if not val or any(x in val for x in ['__', 'FILENAME', 'TOKEN', 'SERVER']):
        errors.append(f"❌ {var} 未注入: '{val}'")
    else:
        print(f"✅ {var} = {val}")

for elem in ['cd-display', 'rbtn', 'top-bar', 'archetype-stamp']:
    if elem not in html:
        errors.append(f"❌ 缺失 DOM: #{elem}")

for ph in ['__EXPIRE_MS__', '__FILENAME__', '__TOKEN__', '__SERVER__']:
    if ph in html:
        errors.append(f"❌ 残留占位符: {ph}")

if errors:
    for e in errors: print(e)
    sys.exit(1)
else:
    print("✅ 校验全部通过")
