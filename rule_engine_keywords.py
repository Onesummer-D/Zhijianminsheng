#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rule_engine_keywords.py - 由Excel自动生成（多标签修复版）
"""

import re

KEYWORDS_DB = {
    "刑事犯罪": {
        "核心定性词": {
            "酒驾": 3,
            "高空抛物": 3,
            "吸毒": 3,
            "毒驾": 3,
            "赌博": 3,
            "醉驾": 3,
            "盗窃": 3,
            "爆炸": 3,
            "强奸": 3,
            "杀猪盘": 3,
            "赌场": 3,
            "猥亵": 3,
            "传销": 3,
            "层级返利": 3,
            "肇事逃逸": 3,
            "笑气": 3,
            "打K": 3,
            "投毒": 3,
            "逃匿": 3,
            "贩毒": 3,
            "冒充公检法": 3,
            "藏毒": 3,
            "拒不支付劳动报酬": 3,
            "寻衅滋事": 3,
            "溜冰": 3,
            "诈骗": 3,
            "放火": 3,
            "刷单诈骗": 3,
            "上头烟": 3,
            "运毒": 3,
            "电子烟": 3
        },
        "特征词": {
            "偷.*(电瓶": 1,
            "包工头跑路": 1,
            "偷电瓶": 1,
            "扔": 1,
            "拉人头": 1,
            "偷电动车": 1,
            "失踪": 1,
            "群殴": 1,
            "贼": 1,
            "REGEX:欠.*工资": 1,
            "溜.*冰": 1,
            "进贼": 1,
            "偷.*挖": 1,
            "扒手": 1,
            "跑了": 1,
            "洗.*脑": 1,
            "贵重": 1,
            "砍人": 1,
            "丢)": 1,
            "被骗": 1,
            "砍伤": 1,
            "交会费": 1,
            "发展下线": 1,
            "关机": 1,
            "东西)": 1,
            "赖.*工资": 1,
            "打伤": 1,
            "冒充": 1,
            "小偷": 1,
            "车": 1,
            "跑.*路": 1,
            "偷钢筋": 1,
            "电话打不通": 1,
            "盗.*采": 1,
            "洗脑": 1,
            "打人": 1,
            "持刀": 1,
            "持械": 1,
            "REGEX:顺.*(电瓶": 1,
            "顺走": 1,
            "斗殴": 1,
            "拖.*工资": 1,
            "保健品诈骗": 1,
            "骗钱": 1,
            "流血": 1,
            "REGEX:高空.*(抛": 1,
            "REGEX:搞.*传销": 1,
            "闹事": 1,
            "打架": 1,
            "失联": 1,
            "找不到人": 1,
            "拉.*人头": 1,
            "REGEX:非.*法.*采矿": 1,
            "REGEX:逃.*匿": 1,
            "伤人": 1,
            "捅伤": 1,
            "REGEX:吸.*毒": 1,
            "贩.*毒": 1,
            "动刀子": 1,
            "偷车": 1,
            "失.*联": 1,
            "捅人": 1,
            "丢了": 1,
            "跑路": 1,
            "撬门": 1
        },
    },
    "公益诉讼": {
        "核心定性词": {
            "污染": 3,
            "土地出让": 3,
            "疫苗": 3,
            "三无": 3,
            "腹泻": 3,
            "国资流失": 3,
            "病死猪": 3,
            "地沟油": 3,
            "偷挖沙石": 3,
            "过期食品": 3,
            "补贴": 3,
            "社保基金": 3,
            "挪用": 3,
            "被猎光": 3,
            "非法采矿": 3,
            "开荒": 3,
            "烈士陵园": 3,
            "排黑水": 3,
            "医保基金": 3,
            "非法添加": 3,
            "被吞": 3,
            "诋毁英雄": 3,
            "河水变黑": 3,
            "绝迹": 3,
            "黑作坊": 3,
            "小吃街": 3,
            "套取": 3,
            "毁林": 3,
            "排污": 3,
            "毒跑道": 3,
            "耕地": 3,
            "英烈": 3,
            "食物中毒": 3
        },
        "特征词": {
            "乱砍树": 1,
            "REGEX:挖山.采矿": 1,
            "噪音": 1,
            "废水": 1,
            "都投诉": 1,
            "我们都": 1,
            "味道刺鼻": 1,
            "猪粪.乱倒": 1,
            "REGEX:河水.(变黑": 1,
            "排废水)": 1,
            "没人处理": 1,
            "渗坑": 1,
            "一直没人管": 1,
            "填埋)": 1,
            "空气.呛人": 1,
            "养殖": 1,
            "学校.跑道.臭": 1,
            "倾倒渣土": 1,
            "反复举报": 1,
            "众多消费者": 1,
            "采砂": 1,
            "REGEX:树林.被砍": 1,
            "冒黑烟": 1,
            "建筑垃圾.堆放": 1,
            "毁林.开荒": 1,
            "粉尘": 1,
            "偷排": 1,
            "全村都": 1,
            "REGEX:垃圾.(乱倒": 1,
            "填埋垃圾": 1,
            "排黑水": 1,
            "REGEX:毒跑道": 1,
            "污水": 1,
            "暗管": 1,
            "垃圾乱倒": 1,
            "偷挖.沙石": 1,
            "拉肚子": 1,
            "塑胶跑道.异味": 1,
            "REGEX:养猪场.(排污": 1,
            "砍树": 1,
            "呛人": 1,
            "多次反映": 1,
            "挖沙子": 1,
            "水发臭": 1,
            "发臭)": 1,
            "挖空": 1,
            "挖山": 1,
            "非法.伐木": 1
        },
    },
    "民事支持起诉": {
        "核心定性词": {
            "没钱打官司": 3,
            "老人": 3,
            "五保户": 3,
            "不养爹妈": 3,
            "赡养费": 3,
            "工伤不赔": 3,
            "儿女不管": 3,
            "请不起律师": 3,
            "拖欠工资": 3,
            "不懂法": 3,
            "赖账": 3,
            "抚养费": 3,
            "医药费": 3,
            "丢下不管": 3,
            "农民工": 3,
            "没证据": 3,
            "困难户": 3,
            "低保": 3,
            "欠薪": 3,
            "残疾人": 3,
            "欠条": 3
        },
        "特征词": {
            "跳闸": 1,
            "不赔": 1,
            "漏水": 1,
            "包工.纠纷": 1,
            "合同纠纷": 1,
            "墙壁发霉": 1,
            "裂缝)": 1,
            "REGEX:建房.(质量差": 1,
            "作证": 1,
            "没人养": 1,
            "证人": 1,
            "放线错": 1,
            "盖房.纠纷": 1,
            "没人管)": 1,
            "找不着": 1,
            "干杂活": 1,
            "确认劳动关系": 1,
            "赡养)": 1,
            "REGEX:抚养费.不给": 1,
            "电话打不通": 1,
            "赖工资": 1,
            "没签合同": 1,
            "物业": 1,
            "REGEX:装修.(出问题": 1,
            "REGEX:工伤.*(不赔": 1,
            "REGEX:老人.(没人管": 1,
            "房子漏水": 1,
            "欠我": 1,
            "质量差)": 1,
            "不给钱": 1,
            "丢下孩子不管": 1,
            "前夫.不给.抚养费": 1,
            "门柱": 1,
            "不给结": 1,
            "不赔钱": 1
        },
    },
    "行政执法监督": {
        "核心定性词": {
            "保护伞": 3,
            "通风报信": 3,
            "推诿扯皮": 3,
            "以罚代管": 3,
            "不作为": 3,
            "小过重罚": 3,
            "乱作为": 3,
            "强拆": 3,
            "久拖不决": 3,
            "程序违法": 3,
            "首违不罚": 3,
            "钓鱼执法": 3,
            "暴力执法": 3,
            "同案不同罚": 3
        },
        "特征词": {
            "违法所得少罚款高": 1,
            "不当)": 1,
            "纵容": 1,
            "小本生意": 1,
            "首次.免罚": 1,
            "没给听证机会": 1,
            "走过场": 1,
            "包庇": 1,
            "奇葩证明": 1,
            "敷衍塞责": 1,
            "拖着": 1,
            "踢皮球": 1,
            "罚得太狠": 1,
            "REGEX:推诿.扯皮": 1,
            "久拖.*不决": 1,
            "今天拆明天建": 1,
            "不作为": 1,
            "相当)": 1,
            "REGEX:同案.(不同罚": 1,
            "选择性.执法": 1,
            "小过.重罚": 1,
            "不同处理)": 1,
            "罚款太重": 1,
            "材料反复交": 1,
            "REGEX:过罚.(不当": 1,
            "没动静": 1,
            "不亮证": 1,
            "罚我": 1,
            "一刀切": 1,
            "投诉没用": 1,
            "罚款.太重": 1,
            "扯皮": 1,
            "不罚": 1,
            "罚款不开票": 1,
            "REGEX:首违.(免罚": 1,
            "张口就罚": 1,
            "形式主义": 1,
            "迟迟不办": 1,
            "没告知申辩权": 1,
            "不出示执法证": 1,
            "从轻)": 1,
            "REGEX:程序.(违法": 1,
            "不出示.证件": 1,
            "石沉大海": 1,
            "整改": 1,
            "没人管": 1
        },
    },
}

EXCLUDE_WORDS = [
    "小说里",
    "假定",
    "模拟场景",
    "狼人杀",
    "假若",
    "譬如",
    "想象一下",
    "做梦",
    "梦话",
    "虚拟案例",
    "剧本里",
    "噩梦惊醒",
    "我举个例子",
    "如若",
    "假设情况",
    "倘若",
    "电影里",
    "杀人游戏",
    "假设",
    "假如说",
    "电视剧里",
    "假设一下",
    "梦见",
    "假如",
    "如果我是",
    "梦到",
    "游戏里",
    "梦里",
    "美梦",
    "梦境",
    "白日梦",
    "剧本杀",
    "虚构故事",
    "梦游",
    "情节里",
    "算了不",
    "设若",
    "噩梦",
]

CATEGORY_PRIORITY = ["刑事犯罪", "公益诉讼", "行政执法监督", "民事支持起诉"]

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
            pattern = r'[\s\S]{0,4}'.join(chars)
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



def extract_location(text):
    """点位提取 - 修复版（增加身份词清洗）"""
    if not text:
        return "—"
    
    import re
    
    # 第一步：清洗前缀（增强版）
    clean_text = text
    
    # 强力清洗各种前缀
    prefixes = [
        r'昨天\s*', r'前天\s*',
        r'我是\s*', r'他是\s*', r'她是\s*',  # 【新增】清洗"我是"
        r'我在\s*', r'我们在\s*', r'来电人\s*', r'投诉人\s*',
        r'公司\s*在?\s*', r'工厂\s*在?\s*', r'工地\s*在?\s*',
        r'位于\s*', r'住在?\s*', r'住\s*',
        r'地址是?\s*', r'在\s*',
        r'老板\s*在?\s*', r'包工头\s*在?\s*', r'负责人\s*在?\s*',
        r'他\s*在\s*', r'她\s*在\s*'
    ]
    
    for p in prefixes:
        clean_text = re.sub(p, '', clean_text)
    
    # 【关键新增】清洗身份词前缀（农民工、残疾人等）
    clean_text = re.sub(r'^[我是们]+', '', clean_text)
    clean_text = re.sub(r'^住', '', clean_text)
    clean_text = re.sub(r'^农民工[，,、]?\s*', '', clean_text)  # 清洗"农民工，"
    clean_text = re.sub(r'^残疾人[，,、]?\s*', '', clean_text)   # 清洗"残疾人，"
    clean_text = re.sub(r'^老人[，,、]?\s*', '', clean_text)     # 清洗"老人，"
    clean_text = re.sub(r'^工人[，,、]?\s*', '', clean_text)     # 清洗"工人，"
    
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

