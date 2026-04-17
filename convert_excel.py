#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_excel.py - 从关键词库Excel自动生成 rule_engine_keywords.py
使用方法：python convert_excel.py
"""

import pandas as pd
import re
import os

def parse_keywords_cell(cell_value):
    """
    解析关键词单元格，处理顿号、逗号、换行分隔的情况
    返回: {关键词: 权重} 的字典
    """
    if pd.isna(cell_value) or str(cell_value).strip() == '':
        return {}
    
    # 统一替换常见分隔符为顿号，然后分割
    text = str(cell_value)
    # 替换逗号、英文逗号、换行为顿号
    text = text.replace('，', '、').replace(',', '、').replace('\n', '、')
    
    # 分割并清洗
    keywords = [k.strip() for k in text.split('、') if k.strip()]
    
    # 返回字典：关键词 -> 权重（这里默认权重为1，后续根据列名决定实际权重）
    return {k: 1 for k in keywords}

def convert_excel_to_python(excel_path="关键词库.xlsx", output_path="rule_engine_keywords.py"):
    """
    读取关键词库Excel，生成带权重的Python代码
    Excel格式要求：线索分类类型 | 核心定性词 | 特征词 | 对应部门/监督词
    """
    
    if not os.path.exists(excel_path):
        print(f"❌ 错误：找不到文件 {excel_path}")
        print("请确保关键词库Excel文件在当前目录下")
        return False
    
    try:
        # 读取Excel，指定第一行为表头
        df = pd.read_excel(excel_path, header=0)
        
        # 打印列名用于调试
        print(f"📊 检测到列名：{list(df.columns)}")
        
        # 标准化列名（去除空格）
        df.columns = [str(col).strip() for col in df.columns]
        
        keywords_db = {}
        
        # 遍历每一行（每个类别）
        for idx, row in df.iterrows():
            try:
                # 获取类别名称
                category = str(row.get('线索分类类型', '')).strip()
                if not category or category == '线索分类类型' or category == 'nan':
                    continue
                
                # 解析核心定性词（权重+3）
                core_words = parse_keywords_cell(row.get('核心定性词', ''))
                # 给核心词设置权重为3
                core_words = {k: 3 for k in core_words.keys()}
                
                # 解析特征词（权重+1）
                feature_words = parse_keywords_cell(row.get('特征词', ''))
                # 特征词权重保持为1
                feature_words = {k: 1 for k in feature_words.keys()}
                
                # 对应部门
                department = str(row.get('对应部门/监督词', '')).strip()
                if department == 'nan' or not department:
                    department = ""
                
                # 构建该类别的数据结构
                keywords_db[category] = {
                    "核心定性词": core_words,
                    "特征词": feature_words,
                    "对应部门": department
                }
                
                print(f"✅ 已处理类别：{category} - 核心词{len(core_words)}个，特征词{len(feature_words)}个")
                
            except Exception as e:
                print(f"⚠️ 处理第{idx+1}行时出错：{e}")
                continue
        
        if not keywords_db:
            print("❌ 错误：未能从Excel中提取到任何有效数据")
            return False
        
        # 生成Python代码内容
        python_content = generate_python_content(keywords_db)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(python_content)
        
        print(f"\n🎉 成功生成 {output_path}")
        print(f"📊 共包含 {len(keywords_db)} 个类别：{list(keywords_db.keys())}")
        return True
        
    except Exception as e:
        print(f"❌ 转换失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def generate_python_content(keywords_db):
    """
    生成完整的rule_engine_keywords.py文件内容
    """
    
    # 将字典转为格式化字符串
    db_str = "KEYWORDS_DB = {\n"
    
    for category, data in keywords_db.items():
        db_str += f'    "{category}": {{\n'
        
        # 核心定性词
        db_str += '        "核心定性词": {'
        core_items = [f'"{k}": {v}' for k, v in data['核心定性词'].items()]
        if core_items:
            db_str += '\n            ' + ',\n            '.join(core_items) + '\n        '
        db_str += '},\n'
        
        # 特征词
        db_str += '        "特征词": {'
        feature_items = [f'"{k}": {v}' for k, v in data['特征词'].items()]
        if feature_items:
            db_str += '\n            ' + ',\n            '.join(feature_items) + '\n        '
        db_str += '},\n'
        
        # 对应部门
        dept = data.get('对应部门', '').replace('"', '\\"')
        db_str += f'        "对应部门": "{dept}"\n'
        db_str += '    },\n'
    
    db_str += "}"
    
    # 完整的文件内容模板
    content = f'''"""
关键词库 - 从Excel自动生成（双层级权重 + jieba智能匹配）
核心定性词匹配：+3分
特征词匹配：+1分
生成时间：自动生成
"""

import jieba
import re

# ============================================================
# 自动生成的关键词数据库（不要手动编辑，请修改Excel后重新运行convert_excel.py）
# ============================================================
{db_str}

def _match_keyword(text: str, keyword: str) -> bool:
    """
    三层匹配策略：精确 -> jieba分词 -> 字级模糊
    """
    if not text or not keyword:
        return False
    
    text = str(text).lower()
    keyword = str(keyword).lower()
    
    # 层1：精确子串
    if keyword in text:
        return True
    
    # 层2：jieba分词子序列（容忍间隔词）
    text_words = list(jieba.cut(text))
    kw_words = list(jieba.cut(keyword))
    
    if len(kw_words) == 1:
        return kw_words[0] in text_words
    
    try:
        idx = text_words.index(kw_words[0])
        for kw in kw_words[1:]:
            found = False
            for i in range(idx+1, min(idx+4, len(text_words))):
                if text_words[i] == kw:
                    idx = i
                    found = True
                    break
            if not found:
                return False
        return True
    except:
        pass
    
    # 层3：字级模糊（间隔最多3个字符）
    if len(keyword) > 1:
        pattern = ".{{0,3}}".join(re.escape(c) for c in keyword)
        return bool(re.search(pattern, text))
    
    return False

def calculate_confidence(text: str, category: str) -> dict:
    """双层级权重算法 - jieba智能版"""
    if not text or not isinstance(text, str):
        return {{"score": 0, "confidence": "低", "matched_core": [], "matched_feature": []}}
    
    if category not in KEYWORDS_DB:
        return {{"score": 0, "confidence": "低", "matched_core": [], "matched_feature": []}}
    
    score = 0
    matched_core = []
    matched_feature = []
    cat_data = KEYWORDS_DB[category]
    
    # 核心定性词 +3（使用智能匹配）
    for word, weight in cat_data.get("核心定性词", {{}}).items():
        if _match_keyword(text, word):
            score += weight
            matched_core.append(word)
    
    # 特征词 +1（使用智能匹配）
    for word, weight in cat_data.get("特征词", {{}}).items():
        if _match_keyword(text, word):
            score += weight
            matched_feature.append(word)
    
    # 判定置信度等级
    if score >= 6:
        conf_level = "高"
    elif score >= 3:
        conf_level = "中"
    else:
        conf_level = "低"
    
    return {{
        "score": score,
        "confidence": conf_level,
        "matched_core": matched_core,
        "matched_feature": matched_feature,
        "department": cat_data.get("对应部门", "")
    }}

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
    return content

if __name__ == "__main__":
    # 默认转换当前目录下的关键词库.xlsx
    success = convert_excel_to_python("关键词库.xlsx", "rule_engine_keywords.py")
    if success:
        print("\n✨ 接下来请刷新Gradio页面或重启服务使更改生效")
    else:
        print("\n⚠️ 转换失败，请检查Excel文件格式是否正确")