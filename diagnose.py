#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本 - 检查关键词库加载情况
"""

import sys
import os

# 强制重新加载（避免缓存）
if 'rule_engine_keywords' in sys.modules:
    del sys.modules['rule_engine_keywords']

print("=" * 60)
print("诊断：关键词库加载测试")
print("=" * 60)

try:
    import rule_engine_keywords as rule
    
    print(f"\n✅ 模块加载成功")
    print(f"📊 类别数量：{len(rule.KEYWORDS_DB)}")
    print(f"🚫 排除词数量：{len(rule.EXCLUDE_WORDS)}")
    
    print(f"\n📋 可用类别：{list(rule.KEYWORDS_DB.keys())}")
    
    # 检查民事支持起诉
    if '民事支持起诉' in rule.KEYWORDS_DB:
        civil = rule.KEYWORDS_DB['民事支持起诉']
        core_words = list(civil.get('核心定性词', {}).keys())
        print(f"\n🔍 民事支持起诉 - 核心词数量：{len(core_words)}")
        print(f"前10个核心词：{core_words[:10]}")
        
        # 测试匹配
        test_text = "我是农民工，老板在房山区长阳镇碧桂园小区拖欠我们工资半年了"
        print(f"\n🧪 测试文本：{test_text}")
        
        result = rule.calculate_confidence(test_text, '民事支持起诉')
        print(f"原始得分：{result['raw_score']}")
        print(f"排除扣分：{result['exclude_penalty']}")
        print(f"净得分：{result['score']}")
        print(f"命中核心词：{result['matched_core']}")
        print(f"是否有核心词：{result['has_core']}")
        
        # 完整分类测试
        classify_result = rule.classify_single(test_text)
        print(f"\n🎯 完整分类结果：")
        print(f"主要类别：{classify_result['primary']}")
        print(f"得分：{classify_result['score']}")
        print(f"所有类别得分：{classify_result['all_scores']}")
    else:
        print("❌ 未找到 '民事支持起诉' 类别")
        
except Exception as e:
    print(f"❌ 错误：{e}")
    import traceback
    traceback.print_exc()