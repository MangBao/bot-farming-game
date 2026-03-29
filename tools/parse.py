import json
import re

with open('../debug_logs/dom_dump.html', encoding='utf-8') as f:
    html = f.read()

# Make it multi-line by replacing >< with >\n<
html = html.replace('><', '>\n<')

with open('../debug_logs/dom_dump_pretty.html', 'w', encoding='utf-8') as f:
    f.write(html)

lines = html.split('\n')

print("--- Searching keywords ---")
keywords = ['Tìm', 'kiếm', 'Bỏng', 'Chạy', 'Chiến', 'đấu', 'Dùng', 'bóng', 'Đăng xuất', 'HP', 'Rank']
for i, line in enumerate(lines):
    line_lower = line.lower()
    for kw in keywords:
        if kw.lower() in line_lower:
            text = re.sub(r'<[^>]+>', '', line).strip()
            if text:
                print(f"L{i}: [{kw}] -> {text[:100]}")
            # Also print the HTML tag itself if it has class/id
            if 'class=' in line or 'id=' in line:
                m = re.search(r'<([a-zA-Z0-9_-]+)\s+([^>]+)>', line)
                if m:
                    print(f"    TAG: <{m.group(1)} {m.group(2)[:100]}>")

# Find all buttons
print("\n--- All buttons ---")
for i, line in enumerate(lines):
    if '<button' in line.lower() or 'button' in line.lower():
        text = re.sub(r'<[^>]+>', '', line).strip()
        print(f"L{i}: BUTTON -> {text} (HTML: {line[:100]})")

