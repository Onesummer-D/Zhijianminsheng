#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单条工单智能识别 - 修复版
修复：1.核心词显示 2.多标签法条 3.法条截断 4.快速通道阈值 5.环保强制触发 6.多次要标签 7.点位
"""

import gradio as gr
import json
import os
import sys
from case_rag import find_similar_case
from extract_elements import auto_extract, format_elements

if 'rule_engine_keywords' in sys.modules:
    del sys.modules['rule_engine_keywords']

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

try:
    from rule_engine_keywords import (
        KEYWORDS_DB, calculate_confidence, classify_single, 
        extract_location, CATEGORY_PRIORITY
    )
    print(f"✅ 规则引擎加载成功：{len(KEYWORDS_DB)} 类别")
except ImportError as e:
    print(f"❌ 规则引擎加载失败: {e}")
    sys.exit(1)

# ========== 【覆盖】独立的点位提取函数（根治版） ==========
# 房山区镇街道乡白名单（含简写形式，按长度降序排列，长的优先匹配）
FANGSHAN_TOWNS = [
    # 街道（全称优先）
    '城关街道', '拱辰街道', '西潞街道',
    '城关街', '拱辰街', '西潞街',
    # 镇（全称优先）
    '韩村河镇', '青龙湖镇', '大石窝镇', '周口店镇', '琉璃河镇',
    '良乡镇', '阎村镇', '窦店镇', '石楼镇', '长阳镇', 
    '河北镇', '长沟镇', '张坊镇', '十渡镇',
    '韩村河', '青龙湖', '大石窝', '周口店', '琉璃河',
    '良乡', '阎村', '窦店', '石楼', '长阳',
    '河北', '长沟', '张坊', '十渡',
    # 乡（全称优先）
    '霞云岭乡', '佛子庄乡', '大安山乡', '史家营乡',
    '南窖乡', '蒲洼乡',
    '霞云岭', '佛子庄', '大安山', '史家营',
    '南窖', '蒲洼',
]

def extract_location(text):
    """点位提取 - 支持有区/无区两种模式，支持简写形式"""
    if not text:
        return "—"
    import re
    
    # ========== 第一步：通用前缀清洗 ==========
    prefix_pattern = r'(我在|我们在|老板|包工头|负责人|公司|工厂|工地|装修工人|农民工|在|从|到|去|蔓延到|位于|住在|我是)'
    text_clean = re.sub(prefix_pattern, '', str(text))
    text_clean = re.sub(r'(村委会|附近|旁边)', '', text_clean)
    # 【新增】清洗口语指示词，防止"那个餐饮连锁店"被吃进地址
    text_clean = re.sub(r'(那个|这个|一家|一个)', '', text_clean)
    
    # ========== 第二步：有区模式（房山区优先）==========
    result = None
    
    idx = text_clean.find("房山区")
    if idx != -1:
        search_text = text_clean[idx:idx+25]
        # 【修改】suffix 移除店/馆/站，防止场所名被误匹配为地址地标
        suffix = r'(?:村|社区|小区|家园|花园|公寓|路|街|巷|桥|广场|大厦|中心|园|城|码头|河|头|塔|乡|镇|街道)'
        
        # 模式A：区+镇/街道/乡+地标
        m = re.search(r'(房山区)([一-龥]{2,6}(?:镇|街道|乡))([一-龥]{2,8}' + suffix + r')?', search_text)
        if m:
            addr = ''.join(filter(None, m.groups()))
            if 4 <= len(addr) <= 22:
                addr = re.sub(r'的(村|路|街|巷|桥|广场|大厦|中心|园|城|码头|河|头|塔|乡|镇|街道|社区|小区|家园|花园|公寓)$', r'\1', addr)
                addr = re.sub(r'(村|路|街|巷|桥|广场|大厦|中心|园|城|码头|河|头|塔|乡|镇|街道)\1+$', r'\1', addr)
                result = addr
        
        # 模式B：区+镇/街道/乡
        if not result:
            m = re.search(r'(房山区)([一-龥]{2,6}(?:镇|街道|乡))', search_text)
            if m:
                addr = ''.join(m.groups())
                if 4 <= len(addr) <= 12:
                    result = addr
        
        # 模式C：区+白名单简写
        if not result:
            for town in FANGSHAN_TOWNS:
                pattern = f'(房山区)({re.escape(town)})'
                m = re.search(pattern, search_text)
                if m:
                    addr = ''.join(m.groups())
                    if 4 <= len(addr) <= 15:
                        result = addr
    
    # ========== 第三步：无区模式 ==========
    # 模式D：镇/街道/乡 + 地标（标准形式）
    if not result:
        m = re.search(r'([一-龥]{2,6}(?:镇|街道|乡))([一-龥]{2,8}(?:村|社区|小区|家园|花园|公寓|路|街|巷|桥|广场|大厦|中心|园|城|码头|河|头|塔))?', text_clean)
        if m:
            addr = ''.join(filter(None, m.groups()))
            if 3 <= len(addr) <= 16:
                addr = re.sub(r'的(村|路|街|巷|桥|广场|大厦|中心|园|城|码头|河|头|塔|乡|镇|街道|社区|小区|家园|花园|公寓)$', r'\1', addr)
                addr = re.sub(r'(村|路|街|巷|桥|广场|大厦|中心|园|城|码头|河|头|塔|乡|镇|街道)\1+$', r'\1', addr)
                town_match = re.search(r'([一-龥]{2,6}(?:镇|街道|乡))', addr)
                if town_match and town_match.group(1) in FANGSHAN_TOWNS:
                    result = addr
    
    # 模式E：白名单遍历匹配（支持简写）
    if not result:
        for town in FANGSHAN_TOWNS:
            idx = text_clean.find(town)
            if idx != -1:
                context_before = text_clean[max(0, idx-10):idx]
                if re.search(r'(火势|蔓延|扩散|波及)', context_before):
                    continue
                result = town
    
    # ========== 【新增】第四步：后缀清洗（兜底）==========
    if result:
        # 截断地址后面的非地址动词/场景词/口语词
        suffix_triggers = [
            '开了', '干了', '去了', '做了', '来了', '走了', '打工', '干活', '开店',
            '理发', '工作', '居住', '生活', '吃饭', '睡觉', '种地', '上班', '上学',
            '看病', '买东西', '卖东西', '摆摊', '修', '建', '拆', '搬', '搞', '弄',
            '那个', '这个', '一家', '一个', '有个', '开了个'
        ]
        for trigger in suffix_triggers:
            if trigger in result:
                idx = result.find(trigger)
                # 向前搜索最近的地址关键词
                for kw in ['镇', '街道', '乡', '村', '小区', '工地', '物流园', '路', '号', '院']:
                    kw_idx = result.rfind(kw, 0, idx)
                    if kw_idx != -1:
                        result = result[:kw_idx + len(kw)]
                        break
                break  # 只处理第一个匹配的trigger
    
    return result if result else "—"

LEGAL_BASIS = {}

def load_legal_basis():
    paths = ['./data/legal_basis_v2.json', './data/legal_basis.json']
    for path in paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ 法条库加载成功: {path} ({len(data)}个类别)")
                return data
    print("❌ 未找到法条文件")
    return {}

LEGAL_BASIS = load_legal_basis()

# 【替换】TF-IDF相似度匹配引擎
from similarity_matcher import CaseSimilarityMatcher
MATCHER = CaseSimilarityMatcher('./data/case_library.json')

def get_laws_for_category(category: str):
    if not category or "非涉检" in category:
        return {"default": [], "extended": []}
    return LEGAL_BASIS.get(category, {"default": [], "extended": []})

def sort_laws_by_match(laws_list, match_text):
    """按法条编号与命中核心词的匹配度排序，匹配度高的在前"""
    import re
    if not laws_list or not match_text:
        return laws_list or []
    
    def extract_words(text):
        words = set()
        for i in range(len(text) - 1):
            for j in [2, 3, 4]:
                if i + j <= len(text):
                    w = text[i:i+j]
                    if re.match(r'^[\u4e00-\u9fa5]+$', w):
                        words.add(w)
        return words
    
    stop_words = {"三年以下", "有期徒刑", "拘役", "管制", "罚金", "处罚金", "或者", "以上", "以下", "情节", "严重", "特别", "下列", "情形", "第一款", "前款", "依照", "规定", "处罚", "并处", "没收财产", "无期徒刑", "死刑", "七年以上", "十年以上", "单位犯", "直接责任", "主管人员", "其他", "处三年", "处二年", "处五年", "处七年", "处十年", "处十五", "年以上", "年以下", "并处罚", "单处罚", "或者单", "或者并", "有期徒", "有前款", "犯前款", "第一款罪", "第二款"}
    
    match_words = extract_words(match_text) - stop_words
    
    # ========== 刑事类场景映射（保留原有完整内容）==========
    crime_scene_map = {
        "职务侵占": ["套取", "集体资金", "单位", "占为己有", "工作人员", "村支书", "村干部"],
        "贪污": ["套取", "骗取", "补偿款", "公共财物", "国家工作人员", "侵吞", "利用职务", "公款"],
        "高空抛物": ["高空", "抛掷", "扔", "从楼上", "坠落物", "砸", "砸坏", "扔下来", "12楼", "11楼", "13楼"],
        "生产、销售伪劣产品": ["假酒", "伪劣", "掺杂", "掺假", "不合格", "销售金额", "假货", "灌装", "私自灌装"],
        "寻衅滋事": ["殴打", "追逐", "拦截", "辱骂", "恐吓", "强拿硬要", "损毁", "占用", "起哄闹事"],
        "诈骗": ["诈骗", "骗取", "虚构", "隐瞒", "非法占有", "骗钱", "骗术", "骗子"],
        "故意伤害": ["伤害", "殴打", "轻伤", "重伤", "砍伤", "捅伤", "打伤"],
        "盗窃": ["盗窃", "偷", "窃取", "入户", "扒窃", "偷走", "被盗", "拉车门", "不翼而飞"],
        "交通肇事": ["交通", "肇事", "逃逸", "重大事故", "重伤", "死亡", "撞伤", "碾轧"],
        "拒不支付劳动报酬": ["拖欠", "欠薪", "劳动报酬", "逃匿", "转移财产", "不发工资"],
        "非法拘禁": ["拘禁", "剥夺", "人身自由", "绑架", "扣留", "关起来"],
        "危险驾驶": ["酒驾", "醉驾", "毒驾", "追逐竞驶", "超员", "超速", "喝酒后开车"],
        "重大责任事故": ["生产", "作业", "安全管理", "重大伤亡", "事故", "闪爆", "液化气"],
        "妨害安全驾驶": ["暴力", "驾驶人员", "抢控", "公共交通工具", "行驶中"],
        "假冒注册商标": ["假冒", "注册商标", "商标", "同一种商品"],
        "侵犯公民个人信息": ["个人信息", "出售", "提供", "公民信息", "泄露信息", "骚扰电话", "二维码", "账号", "冒用", "白条"],
        "虐待": ["虐待", "家庭成员", "情节恶劣", "家暴", "打骂", "轻伤"],
        "妨害公务": ["暴力", "威胁", "阻碍", "国家机关", "执行职务", "警察", "协警", "交警"],
        "污染环境": ["污染", "环境", "排放", "倾倒", "处置", "有毒物质", "有害物质", "养猪场", "猪粪", "臭水", "饮用水井", "渗黑水", "刺鼻", "化学品味"],
        "非法狩猎": ["狩猎", "禁猎区", "禁猎期", "野生动物", "破坏资源", "拍笼", "诱鸟", "黄眉柳莺", "捕鸟", "野生鸟类", "逮鸟", "抓鸟", "电鱼", "捕猎"],
        "非法采矿": ["采矿", "擅自采矿", "矿产资源", "采矿许可证", "国家规划矿区", "挖山", "偷挖", "山体破坏", "钩机", "石头", "矿石", "山石", "挖矿", "卖石头"],
        "敲诈勒索": ["威胁", "要挟", "强行索要", "勒索", "敲诈"],
        "放火": ["放火", "引燃", "燃烧", "火灾", "纵火", "烧纸", "山火"],
        "爆炸": ["爆炸", "闪爆", "引爆", "爆炸物", "液化气"],
        "投毒": ["投毒", "投放", "毒害性", "危险物质"],
        "强奸": ["强奸", "强行发生", "性关系", "违背意志"],
        "猥亵": ["猥亵", "侮辱", "妇女", "儿童", "性骚扰"],
        "聚众斗殴": ["聚众", "斗殴", "打架", "群殴", "持械"],
        "虚假诉讼": ["虚假诉讼", "捏造", "妨害司法", "假官司", "假调解", "公积金"],
        "非法吸收公众存款": ["非法吸收", "公众存款", "集资", "承诺回报", "存款", "理财", "投资", "取现"],
        "集资诈骗": ["集资", "诈骗", "非法集资", "骗取集资款"],
        "合同诈骗": ["合同", "诈骗", "签订合同", "骗取财物", "履行合同", "装修", "装修公司", "停工", "家具"],
        "组织、领导传销活动": ["传销", "层级返利", "拉人头", "入门费", "团队计酬"],
        "开设赌场": ["开设赌场", "赌博", "抽头渔利", "赌资", "网咖", "网吧"],
        "贩卖毒品": ["贩卖", "毒品", "走私", "运输", "制造", "吸毒"],
        "非法持有毒品": ["持有", "毒品", "非法持有", "海洛因", "冰毒"],
        "容留他人吸毒": ["容留", "吸毒", "注射毒品", "场所", "烟雾缭绕", "抽烟"],
        "洗钱": ["洗钱", "掩饰", "隐瞒", "犯罪所得", "收益"],
        "帮助信息网络犯罪活动": ["帮助", "信息网络", "犯罪活动", "技术支持", "广告推广", "支付结算"],
        "拒不执行判决、裁定": ["拒不执行", "判决", "裁定", "有能力执行", "转移财产"],
        "伪证": ["伪证", "证人", "鉴定人", "记录人", "翻译人", "故意作虚假"],
        "窝藏、包庇": ["窝藏", "包庇", "犯罪分子", "作假证明", "帮助逃匿"],
        "掩饰、隐瞒犯罪所得": ["掩饰", "隐瞒", "犯罪所得", "收益", "窝藏", "转移", "收购", "代为销售"],
        "故意损毁文物": ["文物", "文化", "刻字", "拓印", "文物破坏", "塔身", "石经", "地宫", "古迹", "损毁文物", "昊天塔", "云居寺"],
        "盗掘古文化遗址、古墓葬": ["盗墓", "遗址", "探坑", "洛阳铲", "古文化", "古墓葬", "西周燕都"],
    }
    
    # ========== 【新增】行政执法监督类：法律名称 -> 触发词 ==========
    law_name_map = {
        "行政处罚法": ["罚款", "处罚", "罚", "小本", "早餐店", "摆摊", "小商贩", "过罚相当", "比例", "裁量", "从轻", "减轻", "首违", "初次", "无证经营"],
        "行政诉讼法": ["行政诉讼", "法律监督", "裁判", "判决", "裁定", "抗诉", "调解书"],
        "人民检察院组织法": ["法律监督", "职权", "检察院", "检察", "诉讼活动"],
        "人民检察院行政诉讼监督规则": ["行政诉讼", "监督", "抗诉", "检察建议", "争议化解", "实质性化解", "纠正违法"],
        "人民检察院检察建议工作规定": ["检察建议", "纠正违法", "社会治理", "再审"],
        "推进行刑双向衔接": ["行刑衔接", "移送", "涉嫌犯罪", "行政处罚", "刑事立案", "双向衔接"],
    }
    
    # ========== 【新增】条款序号 -> 触发词（精确匹配）==========
    article_scene_map = {
        "第五条": ["小本", "早餐店", "摆摊", "小商贩", "过罚相当", "比例", "罚不起", "八万", "8万", "高额", "过重", "相当", "公正", "公开"],
        "第三十三条": ["首违", "初次", "第一次", "刚开张", "证还在办", "无证经营", "轻微", "及时改正", "未造成危害", "无危害后果", "没有危害", "不罚"],
        "第三十二条": ["从轻", "减轻", "主动消除", "立功", "配合", "胁迫", "诱骗", "尚未掌握"],
        "第三十四条": ["裁量基准", "未说明理由", "未听取意见", "裁量权", "规范", "公布"],
        "第二十条": ["法律监督", "职权", "诉讼活动", "判决裁定", "监狱", "看守所"],
        "第十一条": ["行政诉讼", "法律监督", "检察监督"],
        "第三条": ["监督", "抗诉", "检察建议", "争议化解", "实质性化解", "纠正", "支持"],
        "第四条": ["监督", "抗诉", "检察建议", "争议化解"],
        "第六条": ["监督", "抗诉", "检察建议", "争议化解", "实质性化解"],
        "第九条": ["依职权", "国家利益", "公共利益", "贪污受贿", "徇私舞弊", "枉法裁判"],
        "第九十三条": ["抗诉", "生效判决", "裁定", "调解书", "再审"],
    }
    
    # 小过重罚全局触发词
    penalty_trigger_words = ["罚", "罚款", "处罚", "小本", "早餐店", "摆摊", "小商贩", "无证经营", "过罚相当", "从轻", "减轻", "首违", "初次", "刚开张"]
    is_penalty_case = any(w in match_text for w in penalty_trigger_words)
    
    scored = []
    for item in laws_list:
        number = item.get("编号", "")
        content = item.get("内容", "")
        score = 0
        
        # 1. 刑事类：从法条编号提取"XX罪"关键词
        crime_names = re.findall(r'([\u4e00-\u9fa5]{2,12})罪', number)
        for cname in crime_names:
            if cname in match_text:
                score += 20
            else:
                for char in cname:
                    if char in match_text:
                        score += 3
            scene_words = crime_scene_map.get(cname, [])
            for sw in scene_words:
                if sw in match_text:
                    score += 15
        
        # 2. 【新增】法律名称匹配
        for law_name, triggers in law_name_map.items():
            if law_name in number:
                hit_count = sum(1 for t in triggers if t in match_text)
                score += hit_count * 10
        
        # 3. 【新增】条款序号精确匹配
        for article, triggers in article_scene_map.items():
            if article in number:
                hit_count = sum(1 for t in triggers if t in match_text)
                score += hit_count * 15
        
        # 4. 【新增】小过重罚场景全局加分
        if is_penalty_case and "行政处罚法" in number:
            score += 25
        
        # 5. 滑动窗口场景词匹配
        content_words = extract_words(content) - stop_words
        common = content_words & match_words
        score += len(common) * 5
        
        # 6. 公益诉讼/行政场景辅助匹配
        if any(w in content for w in ["环境", "污染", "生态"]):
            if any(w in match_text for w in ["污染", "臭", "污水", "垃圾", "烧", "刺鼻"]):
                score += 5
        if any(w in content for w in ["文物", "文化"]):
            if any(w in match_text for w in ["文物", "拓印", "刻字", "遗址", "塔", "宅"]):
                score += 5
        if any(w in content for w in ["野生动物", "狩猎", "渔业"]):
            if any(w in match_text for w in ["鸟", "猎", "捕", "鱼", "电鱼"]):
                score += 5
        
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]

def get_similar_cases(category: str, text: str = ""):
    """TF-IDF余弦相似度案例匹配（接入真实similarity_matcher）"""
    if not category or "非涉检" in category:
        return None, []
    
    # 使用真实余弦相似度引擎（已加载 MATCHER）
    best, others = MATCHER.match(text, category, top_k=3)
    if not best:
        return None, []
    
    # 构造前端兼容格式
    def _fmt_law(case):
        laws = case.get("laws")
        if isinstance(laws, list) and len(laws) > 0:
            return laws[0]
        return case.get("law", "—")
    
    best_fmt = {
        "title": best.get("title", "—"),
        "案例标题": best.get("title", "—"),
        "similarity": best.get("similarity", 85),
        "匹配度": best.get("similarity", 85),
        "law": _fmt_law(best)
    }
    
    others_fmt = []
    for o in (others or []):
        others_fmt.append({
            "title": o.get("title", "未知"),
            "similarity": o.get("similarity", 60),
            "law": _fmt_law(o)
        })
    
    return best_fmt, others_fmt

# ========== 【新增】热重载关键词库（无需重启服务） ==========
def reload_rule_engine():
    """每次分析前强制重新加载最新关键词库（不覆盖点位函数）"""
    global KEYWORDS_DB, calculate_confidence, classify_single, CATEGORY_PRIORITY
    if 'rule_engine_keywords' in sys.modules:
        del sys.modules['rule_engine_keywords']
    try:
        import rule_engine_keywords as rule
        KEYWORDS_DB = rule.KEYWORDS_DB
        calculate_confidence = rule.calculate_confidence
        classify_single = rule.classify_single
        # 【关键】不再覆盖 extract_location，保留 single_query_v2.py 里定义的根治版
        CATEGORY_PRIORITY = rule.CATEGORY_PRIORITY
    except Exception as e:
        print(f"⚠️ 关键词库重载失败: {e}")

# ========== 【修复版 analyze_real】 ==========
def analyze_real(text):
    try:
        reload_rule_engine()  # 自动加载最新关键词库，无需重启服务
        
        if not text or len(text.strip()) < 5:
            return {
                "主要类别": "—", "次要类别": "—", "置信度等级": "⚪ 低",
                "建议操作": "请输入完整内容", "核心定性词": "—", "点位": "—",
                "双引擎详情": "内容过短", "相似案例": None, "相似案例列表": [],
                "all_categories": [],
                "net_score": 0
            }
        
        text = text.strip()
        
        # 1. 规则引擎分析所有类别
        all_scores = {}
        matched_keywords = []
        all_exclude_hits = set()
        
        for cat in ["刑事犯罪", "公益诉讼", "民事支持起诉", "行政执法监督"]:
            result = calculate_confidence(text, cat)
            score = result.get("score", 0)
            all_scores[cat] = score
            if result.get("matched_core"):
                matched_keywords.extend(result["matched_core"])
            if result.get("matched_feature"):
                matched_keywords.extend([f"{m}(特征)" for m in result["matched_feature"]])
            for w in result.get("exclude_hits", []):
                all_exclude_hits.add(w)
        
        # 2. 排序找主类别和规则引擎次要类别
        sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
        rule_primary, rule_score = sorted_scores[0]
        
        second_cat = None
        second_score = 0
        score_gap = rule_score
        rule_secondaries = []
        
        if len(sorted_scores) > 1:
            second_cat, second_score = sorted_scores[1]
            score_gap = rule_score - second_score
            for cat, score in sorted_scores[1:]:
                if score >= 3 and len(rule_secondaries) < 2:
                    rule_secondaries.append({"category": cat, "score": score})
        
        # 3. 核心词显示
        core_parts = [m for m in matched_keywords if "(特征)" not in m]
        feature_parts = [m.replace("(特征)", "") for m in matched_keywords if "(特征)" in m]
        
        if core_parts:
            core_display = "、".join(core_parts[:3])
            if feature_parts:
                core_display += f"\n特征词：{'、'.join(feature_parts[:2])}"
        else:
            core_display = f"特征词：{'、'.join(feature_parts[:2])}" if feature_parts else "无"
        
        # 4. 快速通道（规则引擎高置信度，跳过API省成本）
        has_potential_cross = second_score >= 3
        is_env_with_admin = (rule_primary == "公益诉讼" and 
                           ("污染" in text or "环境" in text) and 
                           ("没人管" in text or "反映" in text or "走过场" in text))
        
        is_quick_pass = (rule_score >= 6 and score_gap >= 3)
        
        if is_quick_pass:
            # 【修复】快速通道也返回次要类别（如果次类别>=3）
            second_display = "无"
            if second_score >= 3 and second_cat:
                second_display = second_cat
            
            location = extract_location(text)
            best_case, other_cases = get_similar_cases(rule_primary, text)
            detail_lines = [
                f"【规则引擎高置信度命中】{rule_primary}",
                f"得分：{rule_score}分（>=6分，直接输出）",
                f"次高类别：{second_cat or '无'}({second_score}分)",
                f"分差：{score_gap}分（>=3分，无交叉风险）",
                f"未触发DeepSeek（快速通道）",
                f"命中核心词：{core_parts[:3]}",
                f"命中特征词：{feature_parts[:2]}"
            ]
            
            all_cats = [rule_primary]
            if second_score >= 3 and second_cat and second_cat not in all_cats:
                all_cats.append(second_cat)
            
            return {
                "主要类别": rule_primary,
                "次要类别": second_display,
                "置信度等级": f"🟢 高置信度（{rule_score}分）",
                "建议操作": "🟢 建议优先处理",
                "核心定性词": core_display,
                "点位": location,
                "双引擎详情": "\n".join(detail_lines),
                "相似案例": best_case,
                "相似案例列表": other_cases,
                "all_categories": all_cats,
                "要素提取": format_elements(auto_extract(text, rule_primary)),
                "net_score": rule_score
            }
        
        # 【新增】排除词强保护：触发排除词且扣分后最高分<3，直接非涉检
        if all_exclude_hits and rule_score < 3:
            return {
                "主要类别": "无",
                "次要类别": "无",
                "置信度等级": "⚪ 非涉检线索",
                "建议操作": "⚪ 无需检察介入（排除词过滤）",
                "核心定性词": f"触发排除词：{'、'.join(list(all_exclude_hits)[:3])}",
                "点位": "—",
                "双引擎详情": f"规则引擎触发排除词：{list(all_exclude_hits)}\n扣分后最高分：{rule_score}，直接过滤，未调用API",
                "相似案例": None,
                "相似案例列表": [],
                "all_categories": [],
                "net_score": rule_score
            }
        
        # 5. 【关键修复】所有非快速通道案件统一走API（包括rule_score=0）
        api_primary = rule_primary
        api_secondaries = []
        api_reason = "API未调用或调用失败"
        elements = []
        cross_type = "单一类别"
        handling = "常规审查"
        
        try:
            from api_client import DeepSeekClient
            client = DeepSeekClient()
            
            rule_secondaries_list = []
            if second_score >= 3:
                rule_secondaries_list = [{"category": second_cat, "score": second_score}]
            
            api_result = client.analyze_multi_label(
                text, 
                rule_primary, 
                rule_secondaries_list,
                all_scores
            )
            
            if api_result:
                api_primary = api_result.get("primary", rule_primary)
                api_secondaries = api_result.get("secondaries", [])
                api_reason = api_result.get("reasoning", "")
                elements = api_result.get("elements", [])
                cross_type = api_result.get("cross_type", "")
                handling = api_result.get("handling", "")
                
        except Exception as e:
            api_reason = f"API错误: {str(e)[:30]}"
            if rule_score == 0:
                return {
                    "主要类别": "无",
                    "次要类别": "无",
                    "置信度等级": "⚪ 非涉检线索",
                    "建议操作": "⚪ 无需检察介入（API不可用）",
                    "核心定性词": "无匹配核心词",
                    "点位": "—",
                    "双引擎详情": f"规则引擎未命中（得分: {all_scores}）\nAPI调用失败: {api_reason}",
                    "相似案例": None,
                    "相似案例列表": [],
                    "all_categories": [],
                    "net_score": 0
                }
        
        # 6. 【关键修复】融合决策：API可覆盖规则引擎漏检（包括0分）
        final_primary = api_primary
        final_secondaries = []
        
        if rule_secondaries:
            for s in rule_secondaries:
                cat_name = s["category"] if isinstance(s, dict) else s
                if cat_name and cat_name != final_primary and cat_name not in final_secondaries:
                    final_secondaries.append(cat_name)
        
        if api_secondaries:
            for sec in api_secondaries:
                if isinstance(sec, str) and sec != final_primary and sec not in final_secondaries:
                    final_secondaries.append(sec)
                elif isinstance(sec, dict):
                    sc = sec.get("category", "")
                    if sc and sc != final_primary and sc not in final_secondaries:
                        final_secondaries.append(sc)
        
        # 7. 【关键修复】非涉检最终判定（标签对齐：统一用"无"）
        if (not final_primary or 
            "非涉检" in final_primary or 
            final_primary == "未知" or 
            final_primary == "—" or
            final_primary == "普通投诉（非涉检）"):
            return {
                "主要类别": "无",
                "次要类别": "无",
                "置信度等级": "⚪ 非涉检线索",
                "建议操作": "⚪ 无需检察介入",
                "核心定性词": "无匹配核心词",
                "点位": "—",
                "双引擎详情": f"规则引擎未命中（得分: {all_scores}）\nDeepSeek亦未识别涉检线索",
                "相似案例": None,
                "相似案例列表": [],
                "all_categories": [],
                "net_score": 0
            }
        
        # 8. 点位提取：基于最终判定
        location = extract_location(text)
        
        # 9. 【关键修复】次要类别显示：统一为纯类别名（去掉分数/DeepSeek后缀）
        second_cat_display = "无"
        sec_candidates = []
        
        if api_secondaries:
            for sec in api_secondaries[:2]:
                if isinstance(sec, str):
                    sec_candidates.append(sec)
                elif isinstance(sec, dict):
                    sec_candidates.append(sec.get('category', ''))
        
        if not sec_candidates and rule_secondaries:
            for s in rule_secondaries[:2]:
                if isinstance(s, dict):
                    sec_candidates.append(s['category'])
                else:
                    sec_candidates.append(str(s))
        
        # 清洗并取第一个有效次类别
        import re
        for sp in sec_candidates:
            if sp and sp != final_primary:
                clean_sp = re.sub(r'[（(].*?[）)]', '', sp).strip()
                if clean_sp in ['刑事犯罪', '公益诉讼', '民事支持起诉', '行政执法监督']:
                    second_cat_display = clean_sp
                    break
        
        # 10. 建议操作与置信度
        is_high_conf = rule_score >= 6
        is_unchanged = (api_primary == rule_primary) and not api_secondaries
        
        if is_high_conf and is_unchanged:
            suggestion = "🟢 建议优先处理"
            conf_level_final = f"🟢 高置信度（{rule_score}分）"
        else:
            if handling and "先刑后民" in handling and "🔄" not in handling:
                handling = f"🔄 {handling}"
            handling_display = f"（{handling}）" if handling and handling != "常规审查" else ""
            suggestion = f"🟡 建议人工复核 {handling_display}"
            conf_level_final = f"🟡 中置信度（{rule_score}分）+ DeepSeek精修"
            if final_secondaries or (api_primary != rule_primary):
                conf_level_final += " ⚠️【交叉线索】"
        
        # 11. 相似案例
        best_case, other_cases = get_similar_cases(final_primary, text)
        
        # 12. 构建详情
        rule_second_display_final = second_cat_display if second_cat_display != "无" else "无"
        detail_lines = [
            f"【DeepSeek多标签精修】",
            f"规则引擎初步：{rule_primary}（{rule_score}分）+ {rule_second_display_final}",
            f"DeepSeek精修：主={api_primary}，次={api_secondaries if api_secondaries else '无'}",
            f"关键要素：{elements}",
            f"法律关系：{cross_type}",
            f"处理方式：{handling}",
            f"推理：{api_reason}"
        ]
        
        # 13. 【关键修复】多类别法条查询列表
        all_cats = [final_primary]
        
        if api_secondaries:
            for s in api_secondaries[:2]:
                if isinstance(s, str) and s not in all_cats:
                    all_cats.append(s)
                elif isinstance(s, dict):
                    sc = s.get("category", "")
                    if sc and sc not in all_cats:
                        all_cats.append(sc)
        
        if rule_secondaries:
            for s in rule_secondaries[:2]:
                cat_name = s["category"] if isinstance(s, dict) else s
                if cat_name and cat_name not in all_cats:
                    all_cats.append(cat_name)
        
        # 14. 核心词显示增强
        final_core_display = core_display
        if elements:
            final_core_display += f"\nDeepSeek补充：{', '.join(elements[:2])}"
        
        # 15. 要素提取
        elements = auto_extract(text, final_primary)
        
        return {
            "主要类别": final_primary,
            "次要类别": second_cat_display,
            "置信度等级": conf_level_final,
            "建议操作": suggestion,
            "核心定性词": final_core_display,
            "点位": location,
            "双引擎详情": "\n".join(detail_lines),
            "相似案例": best_case,
            "相似案例列表": other_cases,
            "all_categories": all_cats,
            "要素提取": format_elements(elements),
            "net_score": rule_score
        }
        
    except Exception as e:
        import traceback
        return {
            "主要类别": "识别失败", "次要类别": "—",
            "置信度等级": "❌ 错误", "建议操作": "请重试",
            "核心定性词": str(e)[:30], "点位": "—",
            "双引擎详情": traceback.format_exc()[:500],
            "相似案例": None, "相似案例列表": [],
            "all_categories": [],
            "net_score": -1,
        }
# ========== UI部分（完全保持原样） ==========
def create_ui():
    with gr.Blocks(title="智检民声 - 12345涉检线索智能筛查系统", css="""
        .output-box { 
            border: 1px solid #e0e0e0; 
            border-radius: 4px; 
            padding: 10px; 
            background: white;
        }
        .main-title {
            margin-bottom: 12px !important;
            margin-top: 8px !important;
        }
        h3 {
            font-size: 20px !important;  
            font-weight: 600 !important;
            margin-bottom: 12px !important;
        }
        .law-container {
            margin-top: -4px !important;
            padding-top: 0px !important;
        }
        .law-item {
            margin-bottom: 12px;
            line-height: 1.6;
            margin-top: 0px !important;
        }
        .law-item:first-child {
            margin-top: 0px !important;
            padding-top: 0px !important;
        }
        .law-title {
            font-weight: bold;
            font-size: 15px;
            margin-bottom: 4px;
            margin-top: 0px !important;
        }
        .law-content {
            font-size: 15px;
            color: #333;
            margin-left: 0;
        }
    """) as demo:
        
        gr.Markdown("""
        <div style="margin-left: 0px; font-size: 24px; font-weight: bold;">🔍智检民声 - 12345涉检线索智能筛查系统</div>
        """, elem_classes=["main-title"])
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📝 工单内容")
                input_text = gr.TextArea(
                    label="",
                    placeholder="请输入12345工单内容（如：我是农民工，老板拖欠工资半年...）", 
                    lines=6, 
                    show_label=False
                )
                
                with gr.Row():
                    analyze_btn = gr.Button("🔍 开始分析", variant="primary", scale=2)
                    clear_btn = gr.Button("🔄 清空", scale=1)
                
                gr.Markdown("### 🧪 快速测试")
                with gr.Row():
                    t1 = gr.Button("💰 讨薪案例", size="sm")
                    t2 = gr.Button("🏭 环保案例", size="sm")
                    t3 = gr.Button("🚫 传销案例", size="sm")
                    t4 = gr.Button("⚖️ 小过重罚", size="sm")
                
                with gr.Row():
                    t5 = gr.Button("💭 假设语境", size="sm")
                    t6 = gr.Button("🔇 非涉检", size="sm")
            
            with gr.Column(scale=2):
                gr.Markdown("### 📋 识别结果")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        main_cat = gr.Textbox(
                            label="预期主要类别", 
                            interactive=False,
                            elem_classes=["output-box"]
                        )
                    with gr.Column(scale=1):
                        second_cat = gr.Textbox(
                            label="预期次要类别", 
                            interactive=False, 
                            value="—",
                            elem_classes=["output-box"]
                        )
                
                with gr.Row():
                    with gr.Column(scale=1):
                        conf_level = gr.Textbox(
                            label="置信度等级", 
                            interactive=False,
                            elem_classes=["output-box"]
                        )
                    with gr.Column(scale=1):
                        suggestion = gr.Textbox(
                            label="处理建议", 
                            interactive=False,
                            elem_classes=["output-box"]
                        )
                
                keywords = gr.Textbox(
                    label="🎯 命中核心定性词", 
                    interactive=False, 
                    lines=2,
                    elem_classes=["output-box"]
                )
                
                gr.Markdown("### 📍 点位信息")
                location = gr.Textbox(
                    label="涉检点位/地理位置", 
                    interactive=False, 
                    value="—",
                    elem_classes=["output-box"]
                )
                
                gr.Markdown("### ⚖️ 关联法条")
                laws = gr.HTML(label="", show_label=False, elem_classes=["law-container"])
                
                with gr.Accordion("📚 查看更多法条", open=False):
                    ext_laws = gr.HTML(label="", show_label=False)
                
                gr.Markdown("### 🔍 相似案例提示")
                with gr.Row():
                    with gr.Column(scale=3):
                        similar_case = gr.Textbox(
                            label="最佳匹配案例", 
                            interactive=False, 
                            value="—",
                            elem_classes=["output-box"]
                        )
                    with gr.Column(scale=1):
                        similarity_score = gr.Textbox(
                            label="匹配度", 
                            interactive=False, 
                            value="—",
                            elem_classes=["output-box"]
                        )
                
                with gr.Accordion("📂 查看更多相似案例（Top 3）", open=False):
                    similar_cases_list = gr.HTML(label="", show_label=False)
                
                with gr.Accordion("🔧 双引擎判定详情（技术调试）", open=False):
                    detail = gr.Textbox(
                        label="", 
                        interactive=False, 
                        lines=8, 
                        show_label=False,
                        elem_classes=["output-box"]
                    )
        
        def on_analyze(text):
            result = analyze_real(text)
            cat = result["主要类别"]

            all_categories = result.get("all_categories", [])
            match_text = text[:80]
            combined_laws = {"default": [], "extended": []}
            seen_ids = set()
            
            if all_categories:
                primary_cat = all_categories[0]
                secondary_cats = [c for c in all_categories[1:] if c and c not in ("非涉检", "无")][:2]
                
                sec_slots = min(len(secondary_cats) * 2, 2)
                pri_slots = 6 - sec_slots
                
                p_laws = get_laws_for_category(primary_cat)
                all_p_laws = p_laws.get("default", []) + p_laws.get("extended", [])
                all_p_sorted = sort_laws_by_match(all_p_laws, match_text)
                
                for item in all_p_sorted[:pri_slots]:
                    item_id = item.get('编号', item.get('title', str(item)))
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        combined_laws["default"].append(item)
                for item in all_p_sorted[pri_slots:pri_slots+3]:
                    item_id = item.get('编号', item.get('title', str(item)))
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        combined_laws["extended"].append(item)
                
                if secondary_cats and sec_slots > 0:
                    per_sec = max(1, sec_slots // len(secondary_cats))
                    for sec_cat in secondary_cats:
                        s_laws = get_laws_for_category(sec_cat)
                        all_s_laws = s_laws.get("default", []) + s_laws.get("extended", [])
                        all_s_sorted = sort_laws_by_match(all_s_laws, match_text)
                        
                        for item in all_s_sorted[:per_sec]:
                            item_id = item.get('编号', item.get('title', str(item)))
                            if item_id not in seen_ids:
                                seen_ids.add(item_id)
                                combined_laws["default"].append(item)
                        for item in all_s_sorted[per_sec:per_sec+2]:
                            item_id = item.get('编号', item.get('title', str(item)))
                            if item_id not in seen_ids:
                                seen_ids.add(item_id)
                                combined_laws["extended"].append(item)
            
            if cat not in ("非涉检", "无") and "失败" not in cat and "—" not in cat and all_categories:
                law_html = '<div class="law-container" style="margin-top:-12px;padding-top:0px;">'
                if combined_laws.get("default"):
                    for i, l in enumerate(combined_laws["default"][:3], 1):
                        content = l.get('内容', '')
                        number = l.get('编号', '')
                        law_html += f'<div class="law-item" style="margin-top:0px;margin-bottom:12px;"><div class="law-title" style="margin-top:0px;">{i}. {number}</div><div class="law-content">{content}</div></div>'
                law_html += "</div>"
                
                ext_html = '<div class="law-container" style="margin-top:0px;padding-top:0px;">'
                if combined_laws.get("extended"):
                    for l in combined_laws["extended"][:3]:
                        content = l.get('内容', '')
                        number = l.get('编号', '')
                        ext_html += f'<div class="law-item" style="margin-top:0px;margin-bottom:10px;"><div class="law-title" style="margin-top:0px;font-size:14px;">{number}</div><div class="law-content" style="font-size:14px;">{content}</div></div>'
                ext_html += "</div>"
            else:
                law_html = '<span style="color:#999; font-size:15px;">非涉检线索，无需关联法条</span>'
                ext_html = '<span style="color:#999; font-size:15px;">—</span>'
            
            best = result.get("相似案例")
            if best:
                case_name = best.get("title", best.get("案例标题", "—"))
                raw_sim = best.get('similarity', best.get('匹配度', 0))
                sim_score = f"{raw_sim}%" if isinstance(raw_sim, (int, float)) else "85%"
            else:
                case_name = "—"
                sim_score = "—"
            
            others = result.get("相似案例列表", [])
            if others:
                cases_html = """
                <table style='width:100%;font-size:14px;border-collapse:collapse;'>
                    <thead>
                        <tr style='border-bottom:1px solid #999;'>
                            <th style='text-align:left;padding:8px 4px;font-weight:600;color:#333;'>案例</th>
                            <th style='text-align:center;padding:8px 4px;font-weight:600;color:#333;width:80px;'>匹配度</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for c in others:
                    title = c.get('title', c.get('案例标题', '未知'))
                    sim_val = c.get('similarity', 0)
                    sim_str = f"{sim_val}%" if isinstance(sim_val, (int, float)) else "80%"
                    
                    if isinstance(sim_val, (int, float)):
                        if sim_val >= 90:
                            color = "#2e7d32"
                        elif sim_val >= 80:
                            color = "#1565c0"
                        else:
                            color = "#757575"
                    else:
                        color = "#757575"
                    
                    cases_html += f"""
                        <tr style='border-bottom:1px solid #eee;transition:background 0.2s;' onmouseover="this.style.background='#fafafa'" onmouseout="this.style.background='white'">
                            <td style='padding:8px 4px;color:#333;'>{title}</td>
                            <td style='padding:8px 4px;text-align:center;font-weight:600;color:{color};'>{sim_str}</td>
                        </tr>
                    """
                cases_html += "</tbody></table>"
            else:
                cases_html = "<span style='color:#999; font-size:14px;'>暂无其他相似案例</span>"
            
            return [
                result["主要类别"], 
                result["次要类别"], 
                result["置信度等级"],
                result["建议操作"], 
                result["核心定性词"], 
                result["点位"],
                law_html, 
                ext_html,
                case_name, 
                sim_score, 
                cases_html, 
                result["双引擎详情"]
            ]
        
        def clear():
            return [
                "—", "—", "—", "—", "—", "—",
                '<span style="color:#999; font-size:15px;">等待分析...</span>',
                '<span style="color:#999; font-size:15px;">—</span>',
                "—", "—", 
                "<span style='color:#999; font-size:14px;'>等待分析...</span>",
                "等待分析..."
            ]
        
        outputs = [
            main_cat, second_cat, conf_level, suggestion, keywords, location,
            laws, ext_laws,
            similar_case, similarity_score, similar_cases_list,
            detail
        ]
        
        analyze_btn.click(fn=on_analyze, inputs=input_text, outputs=outputs)
        clear_btn.click(fn=clear, inputs=None, outputs=outputs)
        
        test_cases = {
            t1: "我是农民工，老板在房山区长阳镇碧桂园小区拖欠我们工资半年了，一共欠了8万多，实在没办法了",
            t2: "河北镇檀木港村村委会附近有个工厂天天排黑烟，污染环境，河水都变黑了，多次反映没人管",
            t3: "有人在小区搞传销，天天拉人头开会洗脑，还我血汗钱",
            t4: "市场监管局说我货架摆放不合格，张口就罚五万，小本生意罚不起",
            t5: "如果盗窃罪判几年？假设我偷了东西会怎么处理？做梦梦见被罚款",
            t6: "邻里纠纷，邻居装修太吵，影响休息，物业不管"
        }
        
        for btn, txt in test_cases.items():
            btn.click(fn=lambda x=txt: x, outputs=input_text)
            btn.click(fn=on_analyze, inputs=input_text, outputs=outputs)
    
    return demo

if __name__ == "__main__":
    demo = create_ui()
    demo.launch(server_name="0.0.0.0", server_port=6009)