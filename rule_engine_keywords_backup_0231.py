#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rule_engine_keywords.py - 由Excel自动生成
"""

import re
import pandas as pd

KEYWORDS_DB = {
    "刑事犯罪": {
        "核心定性词": {
            "流血": 3,
            "洗脑": 3,
            "砍伤": 3,
            "骗子": 3,
            "拉人头": 3,
            "顺走": 3,
            "投毒": 3,
            "溜冰": 3,
            "打人": 3,
            "冒充": 3,
            "群殴": 3,
            "撬门": 3,
            "被骗": 3,
            "发展下线": 3,
            "贷款": 3,
            "藏毒": 3,
            "寻衅滋事": 3,
            "打伤": 3,
            "贷": 3,
            "赌博": 3,
            "小偷": 3,
            "持械": 3,
            "上头烟": 3,
            "捅人": 3,
            "斗殴": 3,
            "肇事逃逸": 3,
            "砸车": 3,
            "嗑药": 3,
            "丢了": 3,
            "下药": 3,
            "砍人": 3,
            "上坟烧纸": 3,
            "毒驾": 3,
            "听话水": 3,
            "放火": 3,
            "冒充公检法": 3,
            "赌场": 3,
            "贼": 3,
            "盗窃": 3,
            "高空抛物": 3,
            "闹事": 3,
            "电子烟": 3,
            "强奸": 3,
            "偷车": 3,
            "醉驾": 3,
            "套牌": 3,
            "偷电瓶": 3,
            "运毒": 3,
            "笑气": 3,
            "酒驾": 3,
            "伤人": 3,
            "杀猪盘": 3,
            "偷电动车": 3,
            "进贼": 3,
            "传销": 3,
            "爆炸": 3,
            "打K": 3,
            "打架": 3,
            "保健品": 3,
            "骗钱": 3,
            "被偷": 3,
            "吸毒": 3,
            "毁坏财物": 3,
            "骗人": 3,
            "交会费": 3,
            "扎轮胎": 3,
            "飙车": 3,
            "顶包": 3,
            "偷拍": 3,
            "诈骗": 3,
            "层级返利": 3,
            "贩毒": 3,
            "校园贷": 3,
            "持刀": 3,
            "网贷": 3,
            "偷钢筋": 3,
            "贵重": 3,
            "猥亵": 3,
            "迷药": 3,
            "捅伤": 3,
            "三唑仑": 3,
            "动刀子": 3,
            "刷单": 3,
            "扒手": 3
        },
        "特征词": {
            "REGEX:欠.工资": 1,
            "引发.火灾REGEX:非法.采矿": 1,
            "洗脑": 1,
            "偷.(电瓶": 1,
            "楼上.扔东西REGEX:失火": 1,
            "拉人头": 1,
            "扔": 1,
            "东西)": 1,
            "溜冰": 1,
            "赖.工资": 1,
            "冰毒": 1,
            "包工头.跑路": 1,
            "海洛因REGEX:高空.(抛": 1,
            "东西)REGEX:搞传销": 1,
            "贩毒": 1,
            "沙石)": 1,
            "放火": 1,
            "偷挖.(矿": 1,
            "打针": 1,
            "石头": 1,
            "丢)": 1,
            "限制人身自由REGEX:吸毒": 1,
            "车": 1,
            "欠薪": 1,
            "REGEX:顺.(电瓶": 1
        },
    },
    "公益诉讼": {
        "核心定性词": {
            "反复举报": 3,
            "众多消费者": 3,
            "水发臭": 3,
            "粉尘": 3,
            "砍树": 3,
            "社保基金": 3,
            "套取": 3,
            "拉肚子": 3,
            "垃圾乱倒": 3,
            "排污": 3,
            "黑作坊": 3,
            "英烈": 3,
            "耕地": 3,
            "小吃街": 3,
            "偷排": 3,
            "都投诉": 3,
            "全村都": 3,
            "食物中毒": 3,
            "没人处理": 3,
            "疫苗": 3,
            "呛人": 3,
            "倾倒渣土": 3,
            "填埋垃圾": 3,
            "烈士陵园": 3,
            "土地出让": 3,
            "绝迹": 3,
            "开荒": 3,
            "河水变黑": 3,
            "养殖": 3,
            "三无": 3,
            "非法采矿": 3,
            "毁林": 3,
            "地沟油": 3,
            "挖山": 3,
            "被吞": 3,
            "过期食品": 3,
            "国资流失": 3,
            "基金": 3,
            "暗管": 3,
            "噪音": 3,
            "挪用": 3,
            "我们都": 3,
            "挖沙子": 3,
            "偷挖沙石": 3,
            "挖空": 3,
            "非法添加": 3,
            "诋毁英雄": 3,
            "排黑水": 3,
            "渗坑": 3,
            "医保基金": 3,
            "污染": 3,
            "病死猪": 3,
            "好几个人": 3,
            "味道刺鼻": 3,
            "污水": 3,
            "乱砍树": 3,
            "多次反映": 3,
            "毒跑道": 3,
            "废水": 3,
            "补贴": 3,
            "冒黑烟": 3,
            "被猎光": 3,
            "腹泻": 3,
            "一直没人管": 3
        },
        "特征词": {
            "发臭)": 1,
            "塑胶跑道.异味": 1,
            "空气.呛人REGEX:垃圾.(乱倒": 1,
            "排黑水": 1,
            "学校.跑道.臭REGEX:挖山.采矿": 1,
            "猪粪.乱倒REGEX:毒跑道": 1,
            "非法.伐木REGEX:河水.(变黑": 1,
            "排废水)": 1,
            "偷挖.沙石REGEX:树林.被砍": 1,
            "毁林.开荒": 1,
            "建筑垃圾.堆放": 1,
            "填埋)": 1,
            "REGEX:养猪场.(排污": 1
        },
    },
    "民事支持起诉": {
        "核心定性词": {
            "儿女不管": 3,
            "物业": 3,
            "请不起律师": 3,
            "不懂法": 3,
            "不知道告谁": 3,
            "欠条": 3,
            "老板": 3,
            "不给工资": 3,
            "拖欠": 3,
            "房子漏水": 3,
            "没钱打官司": 3,
            "残疾人": 3,
            "不认账": 3,
            "不会写状子": 3,
            "没签合同": 3,
            "建筑工": 3,
            "找不着": 3,
            "工伤不赔": 3,
            "不给钱": 3,
            "欠我": 3,
            "清洁工": 3,
            "欠工资": 3,
            "赖账": 3,
            "保安": 3,
            "电话打不通": 3,
            "丢下孩子不管": 3,
            "抚养费": 3,
            "低保": 3,
            "不赔钱": 3,
            "丢下不管": 3,
            "偷工减料": 3,
            "五保户": 3,
            "拖欠工资": 3,
            "赖工资": 3,
            "作证": 3,
            "赡养费": 3,
            "老人": 3,
            "老年人": 3,
            "证人": 3,
            "不给结": 3,
            "不养爹妈": 3,
            "没证据": 3,
            "合同纠纷": 3,
            "不赔": 3,
            "包工头跑路": 3,
            "干杂活": 3,
            "跳闸": 3,
            "欠薪": 3,
            "放线错": 3,
            "门柱": 3,
            "农民工": 3,
            "困难户": 3,
            "墙壁发霉": 3,
            "医药费": 3,
            "跑了": 3
        },
        "特征词": {
            "没人管)": 1,
            "漏水": 1,
            "前夫.不给.抚养费REGEX:装修.(出问题": 1,
            "盖房.纠纷REGEX:老人.(没人管": 1,
            "REGEX:建房.(质量差": 1,
            "赡养)REGEX:抚养费.不给": 1,
            "质量差)": 1,
            "包工.纠纷REGEX:工伤.*(不赔": 1,
            "裂缝)": 1,
            "没人养": 1,
            "确认劳动关系": 1
        },
    },
    "行政执法监督": {
        "核心定性词": {
            "程序违法": 3,
            "投诉没用": 3,
            "材料反复交": 3,
            "没人管": 3,
            "一刀切": 3,
            "虚假销号": 3,
            "以罚代管": 3,
            "乱作为": 3,
            "免罚": 3,
            "不亮证": 3,
            "乱罚款": 3,
            "推诿": 3,
            "首违": 3,
            "暴力执法": 3,
            "不作为": 3,
            "今天拆明天建": 3,
            "同案不同罚": 3,
            "石沉大海": 3,
            "踢皮球": 3,
            "违法所得少罚款高": 3,
            "张口就罚": 3,
            "没告知申辩权": 3,
            "通风报信": 3,
            "钓鱼执法": 3,
            "首违不罚": 3,
            "罚款太重": 3,
            "罚款不开票": 3,
            "走过场": 3,
            "罚我": 3,
            "罚得太狠": 3,
            "拖着": 3,
            "保护伞": 3,
            "扯皮": 3,
            "强拆": 3,
            "没给听证机会": 3,
            "处罚不公": 3,
            "没动静": 3,
            "不出示执法证": 3,
            "奇葩证明": 3,
            "小过重罚": 3,
            "迟迟不办": 3,
            "整改": 3,
            "小本生意": 3
        },
        "特征词": {
            "首次.免罚REGEX:过罚.(不当": 1,
            "选择性.执法REGEX:程序.(违法": 1,
            "不同处理)": 1,
            "从轻)": 1,
            "不当)": 1,
            "不作为": 1,
            "罚款.太重REGEX:同案.(不同罚": 1,
            "踢皮球": 1,
            "REGEX:首违.(免罚": 1,
            "不出示.证件REGEX:推诿.扯皮": 1,
            "小过.重罚": 1,
            "相当)": 1,
            "久拖.*不决": 1,
            "不罚": 1
        },
    },
}

EXCLUDE_WORDS = [
    "小说里",
    "假设情况",
    "设若",
    "电影里",
    "梦里",
    "假如",
    "梦见",
    "假设一下",
    "梦话",
    "虚构故事",
    "梦境",
    "如果我是",
    "假设",
    "想象一下",
    "剧本杀",
    "噩梦惊醒",
    "假若",
    "狼人杀",
    "美梦",
    "做梦",
    "倘若",
    "如若",
    "杀人游戏",
    "梦游",
    "我举个例子",
    "假定",
    "梦到",
    "情节里",
    "譬如",
    "剧本里",
    "模拟场景",
    "假如说",
    "游戏里",
    "虚拟案例",
    "噩梦",
    "白日梦",
    "电视剧里",
    "算了不",
]

CATEGORY_PRIORITY = ["刑事犯罪", "公益诉讼", "行政执法监督", "民事支持起诉"]

def _match_keyword_strict(text: str, keyword: str) -> bool:
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

def calculate_confidence(text: str, category: str) -> dict:
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

def classify_single(text: str) -> dict:
    """单条分类 - 多标签支持版"""
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
        
        if result["has_core"] and result["score"] >= 3:
            candidates[cat] = result
    
    if not candidates:
        return {
            "primary": None,
            "score": 0,
            "matched": [],
            "all_scores": all_scores,
            "reason": "无核心词命中或得分过低",
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
    
    # 计算次要类别：>=4分 且 差距<=3分
    secondaries = []
    primary_score = best_data["score"]
    
    for cat, data in sorted_cats[1:]:
        score = data["score"]
        gap = primary_score - score
        if score >= 4 and gap <= 3:
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
        display += [f"{f}(特征)" for f in best_data["matched_feature"][:2]]
    
    conf = "高" if best_data["score"] >= 6 else ("中" if best_data["score"] >= 3 else "低")
    
    return {
        "primary": best_cat,
        "score": best_data["score"],
        "confidence_level": conf,
        "matched": display,
        "all_scores": all_scores,
        "reason": f"命中核心词: {best_data['matched_core']} | 得分: {best_data['raw_score']}- penalty {best_data['penalty']} = {best_data['score']}",
        "core_detail": best_data,
        "secondaries": secondaries,
        "all_details": all_details
    }

# ========== 修复版：点位提取 ==========
def extract_location(text):
    if not text:
        return "—"
    
    # 第一步：清洗前缀
    clean_text = text
    prefixes = [
        r'昨天\\s*', r'前天\\s*',
        r'我在\\s*', r'我们在\\s*', r'来电人\\s*', r'投诉人\\s*',
        r'公司\\s*在?\\s*', r'工厂\\s*在?\\s*', r'工地\\s*在?\\s*',
        r'位于\\s*', r'住在?\\s*', r'住\\s*',
        r'地址是?\\s*', r'在\\s*',
        r'老板\\s*在?\\s*', r'包工头\\s*在?\\s*', r'负责人\\s*在?\\s*',
        r'他\\s*在\\s*', r'她\\s*在\\s*'
    ]
    
    for p in prefixes:
        clean_text = re.sub(p, '', clean_text)
    
    clean_text = re.sub(r'^[我是们]+', '', clean_text)
    clean_text = re.sub(r'^住', '', clean_text)
    
    # 第二步：清洗干扰词
    clean_text = re.sub(r'村委会|居委会', '', clean_text)
    clean_text = re.sub(r'附近|旁边|周边|有个|有座|底下', '', clean_text)
    clean_text = re.sub(r'^老板|包工头|负责人|公司|工厂|工地', '', clean_text)
    
    # 第三步：截断文本
    stop_words = r'(?:有人|打架|动刀|流血|给|干|做|是|在|被|把|让|帮|和|与|或|但是|不过|就|都|也|还|要|会|能|可以|因为|所以|如果|虽然|但是)'
    match_stop = re.search(stop_words, clean_text)
    if match_stop:
        clean_text = clean_text[:match_stop.start()]
    
    # 第四步：匹配地址（使用原始字符串避免转义问题）
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
