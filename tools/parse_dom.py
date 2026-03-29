import json
import re

html = open('../debug_logs/dom_dump.html', encoding='utf-8').read()

extracted = []
tag_name = '<button'
start = 0

while True:
    idx = html.find(tag_name, start)
    if idx == -1: break
    end = html.find('</button>', idx)
    if end == -1: break
    
    chunk = html[idx:end+9]
    cls_idx = chunk.find('class=')
    cls = ''
    if cls_idx != -1:
        quote = chunk[cls_idx+6]
        if quote in ["'", '"']:
            c_end = chunk.find(quote, cls_idx+7)
            if c_end != -1:
                cls = chunk[cls_idx+7:c_end]
    
    # Strip inner HTML to get raw text
    text = re.sub(r'<[^>]+>', '', chunk).strip().replace('\n', ' ')
    extracted.append({'text': text, 'class': cls})
    start = end + 9

# Let's also find all links or divs acting as buttons (role="button" or containing "kiếm")
# To keep it simple, let's extract snippets containing "kiếm", "Chiến đấu", etc.
snippets = {}
keywords = ['Tìm kiếm', 'Tìm Kiếm', 'Chiến đấu', 'Bỏ chạy', 'Hạng', 'HP']
for kw in keywords:
    k_idx = html.find(kw)
    if k_idx != -1:
        snip = html[max(0, k_idx-200):min(len(html), k_idx+200)]
        snippets[kw] = snip

with open('../debug_logs/buttons.json', 'w', encoding='utf-8') as f:
    json.dump({'buttons': extracted, 'snippets': snippets}, f, ensure_ascii=False, indent=2)

print('Done creating buttons.json')
