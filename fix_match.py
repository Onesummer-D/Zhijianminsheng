import re

# 读取原文件
with open('rule_engine_keywords.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 _match_keyword 函数为修复版
old_func = '''def _match_keyword(text: str, keyword: str) -> bool:
    """
    三层匹配策略：精确 -> jieba分词 -> 字级模糊
    """
    if not text or not keyword:
        return False
    
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
        pattern = ".{0,3}".join(re.escape(c) for c in keyword)
        return bool(re.search(pattern, text))
    
    return False'''

new_func = '''def _match_keyword(text: str, keyword: str) -> bool:
    """
    三层匹配策略：精确子串 -> 字级模糊 -> jieba分词兜底
    修复：优先精确匹配，支持'拖欠我们工资'匹配'拖欠工资'
    """
    if not text or not keyword:
        return False
    
    # 层1：精确子串（最高优先级）
    if keyword in text:
        return True
    
    # 层2：字级模糊匹配（强力兜底，支持间隔词）
    # 例如：'拖欠我们工资' 能匹配 '拖欠工资'
    if len(keyword) > 1:
        # 每个字之间允许0-6个任意字符（包括'我们'这种词）
        pattern = "".join(re.escape(c) + ".{0,6}" for c in keyword[:-1]) + re.escape(keyword[-1])
        if re.search(pattern, text):
            return True
    
    # 层3：jieba分词匹配（原始逻辑，作为最后兜底）
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
    
    return False'''

content = content.replace(old_func, new_func)

with open('rule_engine_keywords.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ _match_keyword 函数已修复")
