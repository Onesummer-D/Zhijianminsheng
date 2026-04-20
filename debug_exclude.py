#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
debug_exclude.py - 定位哪个排除词在误杀真实案件
"""

import sys
sys.path.insert(0, '/root/zhijianminsheng')

from rule_engine_keywords import EXCLUDED_WORDS, _match_keyword

# 你的测试 cases
test_cases = [
    "我是残疾人，在丰台区新村街道给一个公司做保洁，三个月没发工资了，一共欠我九千块",
    "我们在通州区马驹桥镇珠江逸景家园干完活，包工头跑了，电话打不通，欠我们十几个人工钱大概二十多万",
    "老板从去年12月就开始拖欠我们工资，一共欠了8万多"
]

print("🔍 开始排查是哪个排除词在误杀...\n")

for text in test_cases:
    print(f"测试文本：{text[:30]}...")
    found = False
    for word in EXCLUDED_WORDS:
        if _match_keyword(text, word):
            print(f"  ❌ 命中排除词：【{word}】")
            found = True
    if not found:
        print(f"  ✅ 未被任何排除词命中")
    print()

print(f"总共 {len(EXCLUDED_WORDS)} 个排除词")
print("如果发现【人名/地名/常见动词】被当成排除词，立即从Excel删除！")