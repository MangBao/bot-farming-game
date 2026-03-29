import json
import re

try:
    with open('../debug_logs/encounter_dump.html', encoding='utf-8') as f:
        html = f.read()

    snippets = {}
    keywords = ['Tìm kiếm', 'Chiến đấu', 'Bỏ chạy', 'Hạng', 'HP', 'Dùng bóng', 'Pokeball', 'Ultra ball', 'math', 'captcha']

    for kw in keywords:
        # find in lowercase or exact
        k_idx = html.find(kw)
        if k_idx == -1:
            k_idx = html.lower().find(kw.lower())

        if k_idx != -1:
            snip = html[max(0, k_idx-300):min(len(html), k_idx+300)]
            # strip all tags and continuous spaces to see the plain text context
            snip_clean = re.sub(r'<[^>]+>', ' [TAG] ', snip)
            snip_clean = ' '.join(snip_clean.split())
            snippets[kw] = snip
            snippets[kw + '_clean'] = snip_clean
        else:
            snippets[kw] = "NOT_FOUND"

    with open('../debug_logs/encounter_buttons.json', 'w', encoding='utf-8') as f:
        json.dump(snippets, f, ensure_ascii=False, indent=2)

    print('OK')

except Exception as e:
    print(f'ERROR: {e}')
