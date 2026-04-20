#!/usr/bin/env python3
import pandas as pd
from collections import defaultdict

df = pd.read_excel("关键词库.xlsx", header=0)
positive_words = set()
category_words = defaultdict(list)

for _, row in df.iterrows():
    category = str(row.get('线索分类类型', '')).strip()
    if not category or category == 'nan':
        continue
    core = str(row.get('核心定性词', ''))
    for w in [x.strip() for x in core.replace('、', ',').replace('，', ',').split(',') if x.strip()]:
        positive_words.add(w)
        category_words[w].append(f"{category}(核心)")
    feature = str(row.get('特征词', ''))
    for w in [x.strip() for x in feature.replace('、', ',').replace('，', ',').split(',') if x.strip()]:
        positive_words.add(w)
        category_words[w].append(f"{category}(特征)")

exclude = str(df['排除词/降噪词'].iloc[0] if '排除词/降噪词' in df.columns else '')
exclude_words = [w.strip() for w in exclude.replace('、', ',').replace('，', ',').split(',') if w.strip()]

print("="*60)
print("【完全冲突】同时在排除词和涉检词中：")
conflicts = set(exclude_words) & positive_words
for w in sorted(conflicts):
    print(f"  ❌ '{w}' -> {category_words[w]}")

print("\n【部分包含】排除词包含于涉检词（会误伤）：")
for ex in exclude_words:
    for pos in positive_words:
        if ex in pos and ex != pos and len(ex) >= 2:
            print(f"  ⚠️  '{ex}' 会误伤 '{pos}' ({category_words[pos]})")
            break

print(f"\n统计：排除词{len(exclude_words)}个，涉检词{len(positive_words)}个，完全冲突{len(conflicts)}个")
