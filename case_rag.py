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
    """伪RAG：类别强锁 + 去停用词 + 场景词加权（修复版）"""
    if not CASE_LIBRARY or not main_category or main_category == "非涉检":
        return "—", "—", []
    
    # 【新增】停用词表（过滤通用虚词）
    STOP_WORDS = {
        "我们", "他们", "你们", "我的", "他的", "她的", "这个", "那个", "一个", "没有",
        "就是", "不是", "但是", "然后", "因为", "所以", "如果", "希望", "政府", "帮忙",
        "反映", "举报", "投诉", "问题", "情况", "事情", "时候", "现在", "已经", "一直",
        "多次", "怎么办", "怎么处理", "能不能", "可以吗",
        "房山区", "北京", "北京市", "街道", "镇", "村", "小区", "社区", "居民", "群众",
        "来电人", "来电", "反映人", "投诉人", "举报人", "本人", "自己", "家里", "家中",
        "附近", "周围", "旁边", "里面", "外面", "上面", "下面", "有人", "发现",
        "看到", "听说", "知道", "认为", "觉得", "非常", "特别", "十分", "很", "太", "都",
        "也", "还", "就", "才", "又", "再", "给", "被", "让", "把", "对", "向", "从",
        "在", "到", "为", "和", "与", "或", "及", "等", "的", "了", "是", "有", "在", "我",
        "他", "她", "它", "你", "这", "那", "什么", "怎么", "为什么", "哪里", "谁", "多少"
    }
    
    # 【新增】提取有效词（过滤停用词）
    def extract_words(text):
        words = set(re.findall(r'[一-龥]{2,6}', text))
        return words - STOP_WORDS
    
    query_words = extract_words(text)
    
    # 类别强锁（保持你原来的逻辑）
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
        return "—", "—", []
    
    # 【新增】精确场景词映射（按主类别定制，权重20分）
    CRIME_SCENE_WORDS = {
        "刑事犯罪": ["盗窃", "诈骗", "贪污", "职务侵占", "伤害", "酒驾", "逃逸", 
                  "假酒", "文物", "采矿", "狩猎", "抛物", "交通肇事", "失火", 
                  "虐待", "个人信息", "爆炸", "闪爆", "盗墓", "刻字", "拓印", 
                  "拘禁", "传销", "斗殴", "勒索", "绑架", "强奸", "猥亵", "放火", 
                  "投毒", "毒品", "赌博", "杀人", "抢劫", "高空", "抛掷", "砸"],
        "公益诉讼": ["污染", "环境", "垃圾", "文物", "生态", "河水", "黑烟", 
                  "噪音", "耕地", "养猪场", "倾倒", "烧垃圾", "臭", "扬尘", 
                  "排污", "毒跑道", "地沟油", "过期食品", "食品安全", "饮用水", 
                  "固废", "砍伐", "采砂", "废气"],
        "民事支持起诉": ["欠薪", "工资", "农民工", "赡养", "装修", "合同", 
                      "预付", "健身房", "培训机构", "跑路", "离婚", "抚养费", 
                      "工伤", "劳务费", "劳动报酬", "欠条", "包工头", "拖欠", 
                      "讨薪", "房租", "押金", "大棚", "材料款"],
        "行政执法监督": ["罚款", "处罚", "城管", "不作为", "首违", "过罚相当", 
                      "占道", "无证", "卫生费", "执法证", "野蛮执法", "推诿", 
                      "踢皮球", "强拆", "乱收费", "钓鱼执法", "程序违法", 
                      "久拖不决", "同案不同罚", "走过场", "石沉大海"]
    }
    
    scene_words = CRIME_SCENE_WORDS.get(main_category, [])
    
    # 【修改】评分逻辑：去停用词 + 提高权重
    scored_cases = []
    for case in candidates:
        summary = case.get("summary", "")
        summary_words = extract_words(summary)
        
        # 基础交集分（去停用词后）
        base_score = len(query_words & summary_words)
        
        # 主类别强制加分（从10分提高到25分）
        cat_score = 0
        if main_category in case.get("categories", []):
            cat_score = 25
        elif second_category and second_category in case.get("categories", []):
            cat_score = 15
        
        # 场景词双命中加分（从8分提高到20分）
        scene_score = 0
        for sw in scene_words:
            if sw in text and sw in summary:
                scene_score += 20
        
        total = base_score + cat_score + scene_score
        scored_cases.append((total, case))
    
    scored_cases.sort(key=lambda x: x[0], reverse=True)
    
    if not scored_cases or scored_cases[0][0] < 5:
        return "—", "—", []
    
    best_case = scored_cases[0][1]
    best_name = best_case.get("name", "—")
    best_law = (best_case.get("laws") or ["—"])[0]
    
    # 【新增】Top3 其他案例
    others = []
    for total, case in scored_cases[1:4]:
        sim = min(95, max(60, 60 + total * 2))
        others.append({
            "title": case.get("name", "未知"),
            "similarity": sim,
            "law": (case.get("laws") or ["—"])[0]
        })
    
    return best_name, best_law, others