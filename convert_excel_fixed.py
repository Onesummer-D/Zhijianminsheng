import os
import glob
import pandas as pd
import json
import re

print("🔄 开始转换...")

os.makedirs('data', exist_ok=True)

def find_excel(pattern):
    files = glob.glob(pattern)
    if not files:
        files = glob.glob(pattern.replace(' ', '*'))
    if not files:
        raise FileNotFoundError(f"找不到匹配 {pattern} 的文件")
    return files[0]

kw_file = find_excel('*关键词库*.xlsx')
print(f"✅ 找到关键词库: {kw_file}")

df_kw = pd.read_excel(kw_file)
keywords_db = {}

for idx, row in df_kw.iterrows():
    try:
        category = str(row['线索分类类型']).strip()
        if not category or category == 'nan' or category == '线索分类类型':
            continue
        
        core_str = str(row['核心定性词']) if pd.notna(row['核心定性词']) else ""
        feature_str = str(row['特征词']) if pd.notna(row['特征词']) else ""
        dept_str = str(row['对应部门/监督词']) if pd.notna(row['对应部门/监督词']) else ""
        
        # 清理<br>标签和换行
        core_str = re.sub(r'<br\s*/?>|</br>', '', core_str)
        core_str = core_str.replace('\n', '、')
        feature_str = re.sub(r'<br\s*/?>|</br>', '', feature_str)
        feature_str = feature_str.replace('\n', '、')
        
        core_words = [w.strip() for w in re.split('[、,，]', core_str) if w.strip() and w.strip() != 'nan']
        feature_words = [w.strip() for w in re.split('[、,，]', feature_str) if w.strip() and w.strip() != 'nan']
        
        core_dict = {w: 3 for w in core_words}
        feature_dict = {w: 1 for w in feature_words}
        
        if category and (core_dict or feature_dict):
            keywords_db[category] = {
                "核心定性词": core_dict,
                "特征词": feature_dict,
                "对应部门": dept_str
            }
            print(f"  [{category}] 核心词{len(core_words)}个")
    except Exception as e:
        print(f"  ⚠️ 跳过第{idx+1}行: {e}")
        continue

# 生成正确的代码（匹配逻辑使用 _match_keyword）
py_content = '''"""
关键词库 - 从Excel自动生成（双层级权重 + 智能匹配）
核心定性词：+3分 | 特征词：+1分
"""

import jieba
import re

KEYWORDS_DB = ''' + json.dumps(keywords_db, ensure_ascii=False, indent=4) + '''

def _match_keyword(text: str, keyword: str) -> bool:
    """智能匹配：支持间隔词（如'拖欠我们工资'匹配'拖欠工资'）"""
    if not text or not keyword:
        return False
    
    # 精确匹配
    if keyword in text:
        return True
    
    # 字级模糊（间隔0-10字符）
    if len(keyword) > 1:
        pattern = "".join(re.escape(c) + ".{0,10}" for c in keyword[:-1]) + re.escape(keyword[-1])
        if re.search(pattern, text):
            return True
    
    # jieba兜底
    text_words = list(jieba.cut(text))
    kw_words = list(jieba.cut(keyword))
    
    if len(kw_words) == 1:
        return kw_words[0] in text_words
    
    try:
        idx = text_words.index(kw_words[0])
        for kw in kw_words[1:]:
            found = False
            for i in range(idx+1, min(idx+10, len(text_words))):
                if text_words[i] == kw:
                    idx = i
                    found = True
                    break
            if not found:
                return False
        return True
    except:
        pass
    
    return False

def calculate_confidence(text: str, category: str) -> dict:
    """双层级权重算法（关键修复：使用 _match_keyword 而不是简单的 in）"""
    if not text or not isinstance(text, str):
        return {"score": 0, "confidence": "低", "matched_core": [], "matched_feature": []}
    
    if category not in KEYWORDS_DB:
        return {"score": 0, "confidence": "低", "matched_core": [], "matched_feature": []}
    
    score = 0
    matched_core = []
    matched_feature = []
    cat_data = KEYWORDS_DB[category]
    
    # 核心修复：使用 _match_keyword 进行智能匹配
    for word, weight in cat_data["核心定性词"].items():
        if _match_keyword(text, word):  # 使用智能匹配！
            score += weight
            matched_core.append(word)
    
    for word, weight in cat_data["特征词"].items():
        if _match_keyword(text, word):  # 使用智能匹配！
            score += weight
            matched_feature.append(word)
    
    if score >= 6 or len(matched_core) >= 2:
        conf_level = "高"
    elif score >= 3 or len(matched_core) == 1:
        conf_level = "中"
    else:
        conf_level = "低"
    
    return {
        "score": score,
        "confidence": conf_level,
        "matched_core": matched_core,
        "matched_feature": matched_feature,
        "department": cat_data.get("对应部门", "")
    }

def keyword_match(text: str) -> str:
    """返回得分最高的类别（阈值3分）"""
    if not text:
        return None
    
    best_cat, best_score = None, 0
    
    for cat in KEYWORDS_DB.keys():
        result = calculate_confidence(text, cat)
        if result["score"] > best_score:
            best_score = result["score"]
            best_cat = cat
    
    return best_cat if best_score >= 3 else None
'''

with open('rule_engine_keywords.py', 'w', encoding='utf-8') as f:
    f.write(py_content)

print(f"\n✅ 已生成 rule_engine_keywords.py（{len(keywords_db)}个类别）")
print("🔍 关键修复：calculate_confidence 现在使用 _match_keyword 智能匹配！")
print("🎉 转换完成！重启 single_query_v2.py 测试")
