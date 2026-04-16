import os
import glob
import pandas as pd
import json
import re

print("🔄 开始转换团队交付物...")

# 创建data目录
os.makedirs('data', exist_ok=True)

# ========== 自动查找Excel文件（模糊匹配，避免文件名问题） ==========
def find_excel(pattern):
    """查找匹配模式的第一个Excel文件"""
    files = glob.glob(pattern)
    if not files:
        # 尝试更宽松的匹配
        files = glob.glob(pattern.replace(' ', '*'))
    if not files:
        raise FileNotFoundError(f"找不到匹配 {pattern} 的文件")
    return files[0]

try:
    kw_file = find_excel('*关键词库*.xlsx')
    law_file = find_excel('*法条关联表*.xlsx')
    print(f"✅ 找到关键词库: {kw_file}")
    print(f"✅ 找到法条关联表: {law_file}")
except Exception as e:
    print(f"❌ 文件查找失败: {e}")
    print("请确保已上传Excel文件到当前目录")
    exit(1)

# ========== 1. 转换关键词库 -> rule_engine_keywords.py ==========
print("\n📝 转换关键词库...")
try:
    df_kw = pd.read_excel(kw_file)
    
    keywords_db = {}
    for idx, row in df_kw.iterrows():
        try:
            category = str(row['线索分类类型']).strip()
            # 跳过空行或表头重复行
            if not category or category == 'nan' or category == '线索分类类型':
                continue
            
            # 处理各种分隔符（顿号、逗号、英文逗号）
            core_str = str(row['核心定性词']) if pd.notna(row['核心定性词']) else ""
            feature_str = str(row['特征词']) if pd.notna(row['特征词']) else ""
            dept_str = str(row['对应部门/监督词']) if pd.notna(row['对应部门/监督词']) else ""
            
            # 分割关键词（支持顿号、中英文逗号）
            core_words = [w.strip() for w in re.split('[、,，]', core_str) if w.strip() and w.strip() != 'nan']
            feature_words = [w.strip() for w in re.split('[、,，]', feature_str) if w.strip() and w.strip() != 'nan']
            
            # 构建权重字典（核心+3，特征+1）
            core_dict = {w: 3 for w in core_words}
            feature_dict = {w: 1 for w in feature_words}
            
            if category and (core_dict or feature_dict):  # 确保有数据才添加
                keywords_db[category] = {
                    "核心定性词": core_dict,
                    "特征词": feature_dict,
                    "对应部门": dept_str
                }
        except Exception as e:
            print(f"  ⚠️ 跳过第{idx+1}行: {e}")
            continue
    
    if not keywords_db:
        raise ValueError("关键词库为空，请检查Excel格式")
    
    # 生成Python文件内容（注意转义和缩进）
    py_content = '''"""
关键词库 - 从Excel自动生成（双层级权重）
核心定性词匹配：+3分
特征词匹配：+1分
"""

KEYWORDS_DB = ''' + json.dumps(keywords_db, ensure_ascii=False, indent=4) + '''

def calculate_confidence(text: str, category: str) -> dict:
    """双层级权重算法"""
    if not text or not isinstance(text, str):
        return {"score": 0, "confidence": "低", "matched_core": [], "matched_feature": []}
    
    if category not in KEYWORDS_DB:
        return {"score": 0, "confidence": "低", "matched_core": [], "matched_feature": []}
    
    score = 0
    matched_core = []
    matched_feature = []
    
    cat_data = KEYWORDS_DB[category]
    
    # 核心定性词 +3
    for word, weight in cat_data["核心定性词"].items():
        if word in text:
            score += weight
            matched_core.append(word)
    
    # 特征词 +1
    for word, weight in cat_data["特征词"].items():
        if word in text:
            score += weight
            matched_feature.append(word)
    
    # 判定置信度等级
    if score >= 6 or len(matched_core) >= 2:
        conf_level = "高"
    elif score >= 3 or len(matched_core) == 1:
        conf_level = "中"
    else:
        conf_level = "低"
    
    return {
        "score": score,
        "confidence": conf_level,  # 高/中/低
        "matched_core": matched_core,
        "matched_feature": matched_feature,
        "department": cat_data.get("对应部门", "")
    }

def keyword_match(text: str) -> str:
    """遍历所有类别，返回得分最高的类别（阈值3分）"""
    if not text:
        return None
    
    best_cat = None
    best_score = 0
    
    for cat in KEYWORDS_DB.keys():
        result = calculate_confidence(text, cat)
        if result["score"] > best_score:
            best_score = result["score"]
            best_cat = cat
    
    return best_cat if best_score >= 3 else None
'''
    
    with open('rule_engine_keywords.py', 'w', encoding='utf-8') as f:
        f.write(py_content)
    
    print(f"✅ 已生成 rule_engine_keywords.py（{len(keywords_db)}个类别）")
    print(f"   包含类别: {list(keywords_db.keys())}")

except Exception as e:
    print(f"❌ 关键词库转换失败: {e}")
    import traceback
    traceback.print_exc()

# ========== 2. 转换法条关联表 -> data/legal_basis.json ==========
print("\n📝 转换法条关联表...")
try:
    # 读取所有sheet或指定sheet
    xl = pd.ExcelFile(law_file)
    sheet_name = xl.sheet_names[0]  # 取第一个sheet
    df_law = pd.read_excel(law_file, sheet_name=sheet_name)
    
    legal_basis = {}
    
    for idx, row in df_law.iterrows():
        try:
            cat = str(row['关联线索类型']) if pd.notna(row['关联线索类型']) else ""
            cat = cat.strip()
            
            # 跳过表头或空行
            if not cat or cat == 'nan' or cat == '关联线索类型':
                continue
            
            if cat not in legal_basis:
                legal_basis[cat] = {"default": [], "extended": []}
            
            law_item = {
                "编号": str(row['法条编号']) if pd.notna(row['法条编号']) else "",
                "内容": str(row['核心内容']) if pd.notna(row['核心内容']) else "",
                "场景": str(row['关联场景（12345高频投诉类型）']) if pd.notna(row['关联场景（12345高频投诉类型）']) else ""
            }
            
            # 确保内容不为空
            if law_item["编号"] and law_item["内容"]:
                legal_basis[cat]["default"].append(law_item)
        except Exception as e:
            print(f"  ⚠️ 跳过第{idx+1}行: {e}")
            continue
    
    # 分配default（前3条）和extended（剩余）
    for cat in legal_basis:
        all_laws = legal_basis[cat]["default"]
        if len(all_laws) > 3:
            legal_basis[cat]["extended"] = all_laws[3:]
            legal_basis[cat]["default"] = all_laws[:3]
    
    with open('data/legal_basis.json', 'w', encoding='utf-8') as f:
        json.dump(legal_basis, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已生成 data/legal_basis.json（{len(legal_basis)}个类别）")
    print(f"   包含类别: {list(legal_basis.keys())}")

except Exception as e:
    print(f"❌ 法条关联表转换失败: {e}")
    import traceback
    traceback.print_exc()

print("\n🎉 转换流程结束！")
print("使用方法:")
print("1. 在single_query_v2.py里: from rule_engine_keywords import KEYWORDS_DB, calculate_confidence")
print("2. 法条库自动加载: data/legal_basis.json")