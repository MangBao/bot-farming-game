import json
import re
import os

try:
    with open('debug_logs/dom_dump.html', encoding='utf-8') as f:
        html = f.read()

    # Find the "Khu Vực Săn Bắt" section
    # The structure usually is a button with text 'Khu Vực Săn Bắt', followed by a div containing '<a>' or '<div>' links.
    idx = html.find('Khu Vực Săn Bắt')
    if idx == -1:
        print('Could not find Khu Vực Săn Bắt')
        exit(1)

    # We take a reasonable chunk after this text (e.g. 5000 characters)
    chunk = html[idx:idx+5000]

    # Stop parsing this chunk when we hit the next section (often another button or section)
    # But usually, it's just a bunch of <a> and <div> with class similar to 'block px-2 py-0.5'
    
    maps_info = {}

    # Find unlocked maps using <a> tags
    # <a class="..." href="/map/vung-kanto">Vùng Kanto</a>
    unlocked_pattern = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>')
    for match in unlocked_pattern.finditer(chunk):
        href = match.group(1).strip()
        name = match.group(2).strip()
        if href.startswith('/map/'):
            maps_info[name] = {
                "unlocked": True,
                "url": href,
                "requirement": ""
            }

    # Find locked maps using <div> tags with title (Yêu cầu...)
    # <div title="Requires Level 20" class="...">Vùng Hoenn</div>
    locked_pattern = re.compile(r'<div[^>]*title="([^"]+)"[^>]*>([^<]+)</div>')
    for match in locked_pattern.finditer(chunk):
        req = match.group(1).strip()
        name = match.group(2).strip()
        # Ensure it's not a generic div by checking if name sounds like a map or req looks like a requirement
        if 'Vùng' in name or 'yêu cầu' in req.lower() or 'level' in req.lower():
            maps_info[name] = {
                "unlocked": False,
                "url": "",
                "requirement": req
            }

    # Save to bot/maps.json
    out_file = 'bot/maps.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(maps_info, f, ensure_ascii=False, indent=4)
        
    print(f"Parsed {len(maps_info)} maps recursively into {out_file}.")
    for m, d in maps_info.items():
        print(f"  - {m}: [{'Unlocked' if d['unlocked'] else 'LOCKED'}] {d.get('url', '')} {d.get('requirement', '')}")

except Exception as e:
    print(f"Error parsing maps: {e}")
