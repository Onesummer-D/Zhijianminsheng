#!/usr/bin/env python3
import sys
if 'rule_engine_keywords' in sys.modules:
    del sys.modules['rule_engine_keywords']

import rule_engine_keywords as rule

test_text = "我是农民工，老板在房山区长阳镇碧桂园小区拖欠我们工资半年了，一共欠了8万多"

print("=" * 60)
print("调试：关键词匹配细节")
print("=" * 60)

# 检查民事支持起诉的数据
cat_data = rule.KEYWORDS_DB.get('民事支持起诉', {})
core_words = list(cat_data.get('核心定性词', {}).keys())

print(f"\n1. 数据库中的核心词数量: {len(core_words)}")
print(f"2. 核心词列表: {core_words}")
print(f"3. 测试文本长度: {len(test_text)}")
print(f"4. 测试文本内容: {repr(test_text)}")

print(f"\n5. 逐个匹配测试:")
for kw in core_words:
    kw_clean = str(kw).lower()
    text_clean = test_text.lower()
    match = kw_clean in text_clean
    print(f"   '{kw}' -> 在文本中? {match}")
    if match:
        idx = text_clean.find(kw_clean)
        print(f"      匹配位置: {idx}, 上下文: ...{text_clean[max(0,idx-5):idx+len(kw)+5]}...")

print(f"\n6. 调用calculate_confidence:")
result = rule.calculate_confidence(test_text, '民事支持起诉')
print(f"   原始得分: {result['raw_score']}")
print(f"   命中核心: {result['matched_core']}")
print(f"   是否有核心: {result['has_core']}")

print(f"\n7. 调用classify_single:")
final = rule.classify_single(test_text)
print(f"   最终结果: {final['primary']}")
print(f"   最终得分: {final['score']}")