import json

with open('skills/website_build/references/catalog.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Total templates:', len(data['templates']))
by_scope = {}
for t in data['templates']:
    s = t['scope']
    by_scope.setdefault(s, []).append(t)

for s, items in by_scope.items():
    print(f"\n### {s} ({len(items)} templates)")
    for item in items:
        print(f"- **`{item['relative_path']}`** ({item['name']}): Theme `{item['theme']}`, BG `{item['bg_mode']}`. Tags: {', '.join(item['tags'][:5])}")
