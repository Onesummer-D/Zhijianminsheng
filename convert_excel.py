#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_excel.py - 【隐藏字符清理版】
深度清理Excel中的隐藏字符（空格、换行、零宽字符）
"""

import pandas as pd
import re
import os

def clean_hidden_chars(text):
    """深度清理隐藏字符"""
    if not text or pd.isna(text):
        return ""
    text = str(text).strip()
    # 移除零宽字符
    text = re.sub(r'[\u200b-\u200f\u2060\ufeff]', '', text)
    # 移除所有空白字符（包括全角空格）
    text = ''.join(text.split())
    return text

def parse_keywords_cell(cell_value):
    """解析关键词（增强清理版）"""
    if pd.isna(cell_value) or str(cell_value).strip() in ['', 'nan']:
        return []
    
    text = clean_hidden_chars(str(cell_value))
    if not text:
        return []
    
    # 统一替换分隔符为 |
    for sep in ['、', '，', ',', '\n', '\r', '\t', ';', '；', '|', ' ']:
        text = text.replace(sep, '|')
    
    # 分割并去重
    keywords = []
    for k in text.split('|'):
        k = k.strip()
        if k and len(k) > 0:
            keywords.append(k)
    
    return list(set(keywords))

def convert_excel_to_python(excel_path="关键词库.xlsx", output_path="rule_engine_keywords.py"):
    if not os.path.exists(excel_path):
        print(f"❌ 找不到 {excel_path}")
        return False
    
    try:
        df = pd.read_excel(excel_path, header=0)
        df.columns = [str(col).strip() for col in df.columns]
        
        # 自动识别列
        col_category = None
        col_core = None
        col_feature = None
        col_exclude = None
        
        for col in df.columns:
            c = str(col).lower()
            if any(x in c for x in ['线索', '分类', '类型', 'category']):
                col_category = col
            elif any(x in c for x in ['核心', '定性', 'core']):
                col_core = col
            elif any(x in c for x in ['特征', 'feature']):
                col_feature = col
            elif any(x in c for x in ['排除', '降噪', 'exclude']):
                col_exclude = col
        
        if not col_category:
            print(f"❌ 未找到线索分类类型列")
            return False
        
        print(f"📊 列映射：类别={col_category}, 核心={col_core}, 特征={col_feature}, 排除={col_exclude}")
        
        keywords_db = {}
        all_excluded = []
        
        for idx, row in df.iterrows():
            category = clean_hidden_chars(str(row.get(col_category, '')))
            if not category or category == 'nan' or category == col_category:
                continue
            
            # 解析各类关键词
            core_words = parse_keywords_cell(row.get(col_core, '')) if col_core else []
            feature_words = parse_keywords_cell(row.get(col_feature, '')) if col_feature else []
            exclude_words = parse_keywords_cell(row.get(col_exclude, '')) if col_exclude else []
            
            all_excluded.extend(exclude_words)
            
            if not core_words and not feature_words:
                continue
            
            keywords_db[category] = {
                "核心定性词": {k: 3 for k in core_words},
                "特征词": {k: 1 for k in feature_words}
            }
            
            print(f"✅ {category}: 核心{len(core_words)}个({core_words[:3]}...), 特征{len(feature_words)}个")
        
        # 生成Python文件
        content = generate_python_content(keywords_db, all_excluded)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n🎉 生成成功：{output_path}")
        print(f"📊 共{len(keywords_db)}个类别，{len(all_excluded)}个排除词")
        
        # 验证生成的文件
        print(f"\n🔍 验证生成文件...")
        with open(output_path, 'r', encoding='utf-8') as f:
            first_500 = f.read(500)
            if '拖欠工资' in first_500 or '民事支持起诉' in first_500:
                print("✅ 验证通过：关键词已写入文件")
            else:
                print("⚠️ 验证警告：未找到预期关键词")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return False

def generate_python_content(keywords_db, excluded_words):
    # 构建 KEYWORDS_DB 字符串（使用传统 % 格式化）
    db_lines = ['KEYWORDS_DB = {']
    for cat, data in keywords_db.items():
        db_lines.append('    "%s": {' % cat)
        db_lines.append('        "核心定性词": {')
        core_items = ['"%s": %d' % (k, v) for k, v in data['核心定性词'].items()]
        if core_items:
            db_lines.append('            ' + ',\n            '.join(core_items))
        db_lines.append('        },')
        db_lines.append('        "特征词": {')
        feat_items = ['"%s": %d' % (k, v) for k, v in data['特征词'].items()]
        if feat_items:
            db_lines.append('            ' + ',\n            '.join(feat_items))
        db_lines.append('        },')
        db_lines.append('    },')
    db_lines.append('}')
    db_str = '\n'.join(db_lines)
    
    # 排除词
    ex_lines = ['EXCLUDE_WORDS = [']
    for w in set(excluded_words):
        if w and '"' not in w:
            ex_lines.append('    "%s",' % w)
    ex_lines.append(']')
    ex_str = '\n'.join(ex_lines)
    
    priority = '", "'.join(['刑事犯罪', '公益诉讼', '行政执法监督', '民事支持起诉'])
    
    # 构建 classify_single 函数（多标签版，使用 %s 避免转义问题）
    classify_func = '''
def classify_single(text):
    """单条分类 - 多标签支持版（阈值3分）"""
    if not text or len(text.strip()) < 5:
        return {"primary": None, "score": 0, "matched": [], "all_scores": {}, "reason": "文本过短", "core_detail": None, "secondaries": []}
    
    text = str(text)
    candidates = {}
    all_scores = {}
    all_details = {}
    
    for cat in KEYWORDS_DB.keys():
        result = calculate_confidence(text, cat)
        all_scores[cat] = result["score"]
        all_details[cat] = result
        
        # 关键：得分>=3分即可进入候选（支持多标签）
        if result["score"] >= 3:
            candidates[cat] = result
    
    if not candidates:
        return {
            "primary": None,
            "score": 0,
            "matched": [],
            "all_scores": all_scores,
            "reason": "无类别得分>=3分",
            "core_detail": None,
            "secondaries": []
        }
    
    # 排序：得分优先，同分按优先级
    def sort_key(item):
        cat, data = item
        score = data["score"]
        priority_idx = CATEGORY_PRIORITY.index(cat) if cat in CATEGORY_PRIORITY else 99
        return (-score, priority_idx)
    
    sorted_cats = sorted(candidates.items(), key=sort_key)
    best_cat, best_data = sorted_cats[0]
    
    # 计算次要类别：>=3分 且 与最高分差距<=3分
    secondaries = []
    primary_score = best_data["score"]
    
    for cat, data in sorted_cats[1:]:  # 跳过主要类别
        score = data["score"]
        gap = primary_score - score
        if score >= 3 and gap <= 3:
            secondaries.append({
                "category": cat,
                "score": score,
                "gap": gap,
                "matched_core": data["matched_core"][:2],
                "confidence": "high" if score >= 6 else "medium"
            })
    
    secondaries = secondaries[:2]  # 最多2个
    
    # 组装显示
    display = best_data["matched_core"][:3]
    if best_data["matched_feature"]:
        display += ["%s(特征)" % f for f in best_data["matched_feature"][:2]]
    
    conf = "高" if best_data["score"] >= 6 else ("中" if best_data["score"] >= 3 else "低")
    
    return {
        "primary": best_cat,
        "score": best_data["score"],
        "confidence_level": conf,
        "matched": display,
        "all_scores": all_scores,
        "reason": "命中核心词: %s | 得分: %s" % (best_data['matched_core'], best_data['score']),
        "core_detail": best_data,
        "secondaries": secondaries,
        "all_details": all_details
    }
'''
    
    # 构建点位函数（修复版，增加身份词清洗）
    location_func = '''
def extract_location(text):
    """点位提取 - 修复版（增加身份词清洗）"""
    if not text:
        return "—"
    
    import re
    
    # 第一步：清洗前缀（增强版）
    clean_text = text
    
    # 强力清洗各种前缀
    prefixes = [
        r'昨天\\s*', r'前天\\s*',
        r'我是\\s*', r'他是\\s*', r'她是\\s*',  # 【新增】清洗"我是"
        r'我在\\s*', r'我们在\\s*', r'来电人\\s*', r'投诉人\\s*',
        r'公司\\s*在?\\s*', r'工厂\\s*在?\\s*', r'工地\\s*在?\\s*',
        r'位于\\s*', r'住在?\\s*', r'住\\s*',
        r'地址是?\\s*', r'在\\s*',
        r'老板\\s*在?\\s*', r'包工头\\s*在?\\s*', r'负责人\\s*在?\\s*',
        r'他\\s*在\\s*', r'她\\s*在\\s*'
    ]
    
    for p in prefixes:
        clean_text = re.sub(p, '', clean_text)
    
    # 【关键新增】清洗身份词前缀（农民工、残疾人等）
    clean_text = re.sub(r'^[我是们]+', '', clean_text)
    clean_text = re.sub(r'^住', '', clean_text)
    clean_text = re.sub(r'^农民工[，,、]?\\s*', '', clean_text)  # 清洗"农民工，"
    clean_text = re.sub(r'^残疾人[，,、]?\\s*', '', clean_text)   # 清洗"残疾人，"
    clean_text = re.sub(r'^老人[，,、]?\\s*', '', clean_text)     # 清洗"老人，"
    clean_text = re.sub(r'^工人[，,、]?\\s*', '', clean_text)     # 清洗"工人，"
    
    # 第二步：清洗干扰词
    clean_text = re.sub(r'村委会|居委会', '', clean_text)
    clean_text = re.sub(r'附近|旁边|周边|有个|有座|底下', '', clean_text)
    clean_text = re.sub(r'^老板|包工头|负责人|公司|工厂|工地', '', clean_text)
    
    # 第三步：先截断文本，防止匹配过长
    stop_words = r'(?:有人|打架|动刀|流血|给|干|做|是|在|被|把|让|帮|和|与|或|但是|不过|就|都|也|还|要|会|能|可以|因为|所以|如果|虽然|但是)'
    match_stop = re.search(stop_words, clean_text)
    if match_stop:
        clean_text = clean_text[:match_stop.start()]
    
    # 第四步：匹配地址
    location_suffix = r'(?:村|社区|小区|家园|花园|公寓|路|街|巷|桥|广场|大厦|中心|园|城)'
    
    # 模式A：区+镇/街道+地标
    pattern_a = r'([一-龥]{2,4}区)([一-龥]{2,6}(?:镇|街道|乡))([一-龥]{2,8}' + location_suffix + r')?'
    match = re.search(pattern_a, clean_text)
    if match:
        addr = ''.join(filter(None, match.groups()))
        if 4 <= len(addr) <= 20:
            return addr
    
    # 模式A2：区名（无"区"字）+ 镇/街道
    pattern_a2 = r'([一-龥]{2,4})([一-龥]{2,6}(?:镇|街道|乡))'
    match = re.search(pattern_a2, clean_text)
    if match:
        addr = ''.join(match.groups())
        if 4 <= len(addr) <= 12 and not addr[0].isdigit():
            return addr
    
    # 模式B：镇/街道+地标（无区）
    pattern_b = r'([一-龥]{2,6}(?:镇|街道|乡))([一-龥]{2,8}' + location_suffix + r')'
    match = re.search(pattern_b, clean_text)
    if match:
        addr = ''.join(match.groups())
        if 4 <= len(addr) <= 16:
            return addr
    
    # 兜底：区+镇/街道
    fallback = r'([一-龥]{2,4}区)([一-龥]{2,6}(?:镇|街道|乡))'
    match = re.search(fallback, clean_text)
    if match:
        addr = ''.join(match.groups())
        return addr if len(addr) >= 4 else "—"
    
    return "—"
'''
    
    # 组装最终文件（使用 % 格式化）
    template = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rule_engine_keywords.py - 由Excel自动生成（多标签修复版）
"""

import re

%s

%s

CATEGORY_PRIORITY = ["%s"]

def _match_keyword_strict(text, keyword):
    """增强匹配：支持正则前缀+智能间隔匹配"""
    if not text or not keyword:
        return False
    text = str(text).lower()
    keyword = str(keyword).lower()
    
    # 1. 精确子串匹配
    if keyword in text:
        return True
    
    # 2. 正则匹配
    if keyword.startswith("regex:"):
        try:
            pattern = keyword[6:]
            return bool(re.search(pattern, text, re.IGNORECASE))
        except:
            return False
    
    # 3. 智能间隔匹配（4字以上关键词）
    if len(keyword) >= 4:
        try:
            chars = [re.escape(c) for c in keyword]
            pattern = r'[\\s\\S]{0,4}'.join(chars)
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except:
            pass
    
    return False

def calculate_confidence(text, category):
    """计算置信度"""
    if not text:
        return {"score": 0, "has_core": False, "matched_core": [], "matched_feature": []}
    
    text = str(text).lower()
    cat_data = KEYWORDS_DB.get(category, {})
    
    if not cat_data:
        return {"score": 0, "has_core": False, "matched_core": [], "matched_feature": []}
    
    # 核心词匹配
    core_score = 0
    matched_core = []
    for kw, score in cat_data.get("核心定性词", {}).items():
        if _match_keyword_strict(text, kw):
            core_score += score
            matched_core.append(kw)
    
    # 特征词匹配
    feature_score = 0
    matched_feature = []
    for kw, score in cat_data.get("特征词", {}).items():
        if _match_keyword_strict(text, kw):
            feature_score += score
            matched_feature.append(kw)
    
    total = core_score + feature_score
    
    # 排除词软过滤（扣分制）
    penalty = 0
    exclude_hits = []
    for word in EXCLUDE_WORDS:
        if word in text:
            penalty += 2
            exclude_hits.append(word)
    
    final_score = max(0, total - penalty)
    
    return {
        "score": final_score,
        "raw_score": total,
        "penalty": penalty,
        "has_core": len(matched_core) > 0,
        "matched_core": matched_core,
        "matched_feature": matched_feature,
        "exclude_hits": exclude_hits
    }

%s

%s
'''
    
    # 使用 % 替换（避免f-string转义地狱）
    final_content = template % (db_str, ex_str, priority, classify_func, location_func)
    
    return final_content

if __name__ == "__main__":
    convert_excel_to_python()