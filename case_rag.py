import json
import os
import re

CASE_LIBRARY_PATH = "data/case_library.json"

def load_case_library():
    if not os.path.exists(CASE_LIBRARY_PATH):
        return []
    with open(CASE_LIBRARY_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

CASE_LIBRARY = load_case_library()

# 跨类别映射：让标注为"跨类别"的案例对涉及的四大类可见
CROSS_CATEGORY_MAP = {
    "跨类别": ["刑事犯罪", "公益诉讼", "民事支持起诉", "行政执法监督"]
}

# 场景关键词权重：同类核心场景词匹配额外加分
SCENE_KEYWORDS = {
    "刑事犯罪": ["盗窃", "诈骗", "贪污", "职务侵占", "伤害", "酒驾", "逃逸", 
              "假酒", "文物", "采矿", "狩猎", "抛物", "交通肇事", "失火", 
              "虐待", "个人信息", "爆炸", "闪爆", "盗墓", "刻字", "拓印"],
    "公益诉讼": ["污染", "环境", "垃圾", "文物", "生态", "河水", "黑烟", 
              "噪音", "耕地", "养猪场", "倾倒", "烧垃圾", "臭", "扬尘"],
    "民事支持起诉": ["欠薪", "工资", "农民工", "赡养", "装修", "合同", 
                  "预付", "健身房", "培训机构", "跑路", "离婚"],
    "行政执法监督": ["罚款", "处罚", "城管", "不作为", "首违", "过罚相当", 
                  "占道", "无证", "卫生费", "执法证", "野蛮执法"]
}

def find_similar_case(text, main_category, second_category=None):
    """伪RAG：类别强锁 + 关键词加权匹配（修复版）"""
    if not CASE_LIBRARY or not main_category or main_category == "非涉检":
        return "—", "—"
    
    # 1. 类别强锁：只取主类别或跨类别案例
    candidates = []
    for case in CASE_LIBRARY:
        cats = case.get("categories", [])
        matched = False
        
        if main_category in cats:
            matched = True
        else:
            for c in cats:
                if c in CROSS_CATEGORY_MAP and main_category in CROSS_CATEGORY_MAP[c]:
                    matched = True
                    break
        
        if matched or (second_category and second_category in cats):
            candidates.append(case)
    
    if not candidates:
        return "—", "—"
    
    words = set(re.findall(r'[一-龥]{2,4}', text))
    
    best_score, best_case = -1, candidates[0]
    for case in candidates:
        summary = case.get("summary", "")
        summary_words = set(re.findall(r'[一-龥]{2,4}', summary))
        score = len(words & summary_words)
        
        # 主类别基础分
        if main_category in case.get("categories", []):
            score += 10
        elif any(c in CROSS_CATEGORY_MAP for c in case.get("categories", [])):
            score += 5
        
        # 次类别额外分
        if second_category and second_category in case.get("categories", []):
            score += 3
        
        # 场景关键词加权（核心修复点）
        scene_words = SCENE_KEYWORDS.get(main_category, [])
        for kw in scene_words:
            if kw in text and kw in summary:
                score += 8  # 场景词双命中，高权重
        
        if score > best_score:
            best_score = score
            best_case = case
    
    return best_case.get("name", "—"), (best_case.get("laws") or ["—"])[0]