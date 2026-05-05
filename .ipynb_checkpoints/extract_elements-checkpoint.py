# -*- coding: utf-8 -*-
"""
要素提取器 - 针对四大类分别提取结构化信息
"""

import re

# ========== 全局常量 ==========
SPOKEN_WORDS = ['那个', '这个', '一个', '哪个', '几个', '某', '什么']
LOC_PREFIXES = ['镇', '街道', '乡', '村', '区', '路', '县', '市']
BAD_ENDS = ['个', '十', '百', '千', '万', '两', '几', '多', '来', '去', '在', '从', '到', '的', '是', '和', '与', '们']


def is_valid_project_name(s):
    """过滤掉包含口语指示代词的项目名称"""
    return not any(w in s for w in SPOKEN_WORDS)


def extract_salary_elements(text):
    """拖欠工资类要素提取（纯正则，无需API）"""
    if not text:
        return {}
    
    result = {}
    
    # 1. 工人人数
    m = re.search(r'(?:我|他|来电人|反映人|本人)(?:跟|和|与|同|带)\s*(\d+)\s*个?\s*[一-龥]{0,3}?(?:工友|工人|农民工|人)', text)
    if m:
        result['工人人数'] = str(int(m.group(1)) + 1) + '人'
    else:
        m = re.search(r'(\d+)\s*个?\s*[一-龥]{0,3}?(?:工友|工人|农民工|人)', text)
        if not m:
            cn_nums = {'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,
                       '十一':11,'十二':12,'十三':13,'十四':14,'十五':15,'十六':16,'十七':17,'十八':18,'十九':19,'二十':20}
            found = False
            for cn, num in cn_nums.items():
                pattern = cn + r'\s*个?\s*[一-龥]{0,3}?(?:工友|工人|农民工|人)'
                if re.search(pattern, text):
                    result['工人人数'] = str(num) + '人'
                    found = True
                    break
            if not found:
                result['工人人数'] = '未提及'
        else:
            result['工人人数'] = m.group(1) + '人'
    
    # 2. 欠薪数额
    m = re.search(r'(?:欠|被欠|拖欠)[^。，\d]{0,15}?(\d+(?:\.\d+)?)\s*多?\s*(万|千|百|元|块)', text)
    if m:
        amount, unit = m.group(1), m.group(2)
        between = m.group(0)[m.group(0).find(amount)+len(amount):m.group(0).rfind(unit)]
        result['欠薪数额'] = amount + ('多' if '多' in between else '') + unit
    else:
        m = re.search(r'(\d+(?:\.\d+)?)\s*多?\s*(万|千|百|元|块)', text)
        if m:
            amount, unit = m.group(1), m.group(2)
            between = m.group(0)[m.group(0).find(amount)+len(amount):m.group(0).rfind(unit)]
            result['欠薪数额'] = amount + ('多' if '多' in between else '') + unit
        else:
            result['欠薪数额'] = '未提及'
    
    # 3. 开工/务工时间
    m = re.search(r'(?:从|自|于)?(\d{4}年\d{1,2}月)', text)
    result['开工时间'] = m.group(1) if m else '未提及'
    
    # 4. 欠薪主体 —— 分三层
    company_keywords = r'(?<![一-龥])(劳务公司|用人单位|总包单位|分包单位|项目部|施工队|建筑公司|开发商|装修公司)'
    boundary = r'(?=\s|，|。|！|？|给|拖|欠|不|没|找|来|去|的|和|与|叫|让|打|工|干|上|下|里|外|老|一|说|没|周|负|责|经|理|人|家|孩|希|望|政|府|能|帮|要|回|血|汗|钱|就|是|姓|手|电|已|今|明|日|天|个|人|啊|呢|呀|哪|那|这)'
    m = re.search(company_keywords + boundary, text)
    if not m:
        m = re.search(r'(?<!老)(老板|包工头)', text)
    if not m:
        m = re.search(r'([一-龥]{0,4}?(?:公司|项目部|施工队))' + boundary, text)
        if m:
            raw = m.group(1)
            for lp in LOC_PREFIXES:
                if raw.startswith(lp):
                    raw = raw[len(lp):]
                    break
            bad_prefixes = ['我们去', '他们去', '你们去', '去', '来', '到', '在', '从', '跟', '向', '找', '让', '叫', '给', '说', '我们', '他们', '你们', '我', '他']
            for bp in sorted(bad_prefixes, key=len, reverse=True):
                if raw.startswith(bp):
                    raw = raw[len(bp):]
                    break
            result['欠薪主体'] = raw if raw else m.group(1)
        else:
            result['欠薪主体'] = '未提及'
    else:
        result['欠薪主体'] = m.group(1)
    
    # 5. 工程地点
    m = re.search(r'房山区[^\s，。]{2,12}(?:镇|街道|乡|村|小区|工地|物流园)', text)
    result['工程地点'] = m.group(0) if m else '未提及'
    
    # 6. 工程项目名称 —— 【只定义一次，用Unicode码点终极清洗】
    proj_name = None
    
    m = re.search(r'工程项目?[叫是为][：:]?\s*(.{2,25}?)(?:，|。|！|？|结果|干完|工资|我们|但|老板|希望|到|现在|从|已|都|一共)', text)
    if m:
        raw = m.group(1).strip()
        # 运行时生成中文引号，100%绕过文件编码问题
        quote_chars = [
            chr(0x201c), chr(0x201d),  # " "
            chr(0x2018), chr(0x2019),  # ' '
            '"', "'",                  # ASCII
            '「', '」', '『', '』', '《', '》'
        ]
        for q in quote_chars:
            raw = raw.replace(q, '')
        prefix_verbs = ['叫', '是', '为', '叫做', '名为']
        for pv in sorted(prefix_verbs, key=len, reverse=True):
            if raw.startswith(pv):
                raw = raw[len(pv):].strip()
                break
        if len(raw) >= 4 and raw not in ['工程', '项目', '小区', '工地', '建筑'] and is_valid_project_name(raw):
            # 逐字符Unicode码点过滤，只保留汉字/字母/数字
            cleaned = []
            for c in raw:
                if ('\u4e00' <= c <= '\u9fff') or c.isalnum():
                    cleaned.append(c)
            proj_name = ''.join(cleaned) if cleaned else None
    
    # 模式A-F 兜底
    if not proj_name:
        m = re.search(r'(?:在|位于|到|去|从)\s*([一-龥]{2,8}?(?:项目|工程|小区))', text)
        if m and is_valid_project_name(m.group(1)):
            proj_name = m.group(1)
    if not proj_name:
        m = re.search(r'房山区\s*([一-龥]{2,8}?(?:项目|工程|小区|工地))', text)
        if m and is_valid_project_name(m.group(1)):
            proj_name = m.group(1)
    if not proj_name:
        m = re.search(r'(?:叫做|名为|叫|是)\s*([一-龥]{2,12})\s*(?:项目|工程|小区)', text)
        if m:
            raw = m.group(1)
            if raw.endswith('的'):
                raw = raw[:-1]
            if raw and is_valid_project_name(raw):
                proj_name = raw
    if not proj_name:
        m = re.search(r'([一-龥]{2,12})(?:项目|工程|小区)', text)
        if m:
            raw_name = m.group(1)
            prefix_verbs = ['个叫做', '叫做', '名为', '叫', '是', '做', '干', '负责', '承建', '承包', '在', '从', '到', '去', '的', '个', '这', '那']
            for pv in sorted(prefix_verbs, key=len, reverse=True):
                if raw_name.startswith(pv):
                    raw_name = raw_name[len(pv):]
                    break
            if raw_name.endswith('的'):
                raw_name = raw_name[:-1]
            if raw_name and is_valid_project_name(raw_name):
                proj_name = raw_name
    if not proj_name:
        m = re.search(r'([一-龥]{2,6})(?:工地|建筑)', text)
        if m and is_valid_project_name(m.group(1)):
            prefix = m.group(1)
            if not any(prefix.endswith(w) for w in BAD_ENDS):
                full = m.group(0)
                pos = text.find(full)
                after = text[pos+len(full):pos+len(full)+2]
                if '公司' not in after:
                    proj_name = full
    
    result['工程项目名称'] = proj_name if proj_name else '未提及'
    
    # 7. 是否签订劳动合同
    neg_words = ['没签', '没有合同', '没有签', '未签', '未签订', '口头', '没写', '不懂']
    pos_words = ['合同', '书面', '协议', '欠条', '字据']
    if any(w in text for w in neg_words):
        result['是否签订劳动合同'] = '否'
    elif any(w in text for w in pos_words):
        result['是否签订劳动合同'] = '是'
    else:
        result['是否签订劳动合同'] = '未明确'
    
    return result


def extract_env_elements(text):
    """公益诉讼-环境污染类要素提取"""
    result = {}
    
    pollution_types = [
        "河水", "空气", "土壤", "地下水", "井水", "垃圾", "噪音", "扬尘", 
        "黑烟", "臭气", "淤泥", "堆积", "固废", "污水", "废水", "废气",
        "黑臭水体", "河道淤塞", "污泥", "渗漏", "辐射", "重金属",
        "地沟油", "过期食品", "病死猪", "毒跑道", "塑料", "化学"
    ]
    found = [pt for pt in pollution_types if pt in text]
    result['污染类型'] = "、".join(found[:3]) if found else '未提及'
    
    m = re.search(r'房山区[^\s，。]{0,6}(?:镇|街道|乡)?[^\s，。]{0,8}(?:河|路|桥|码头|桥下|交叉口|交叉|小区|村|工地|工厂|养殖场)', text)
    if not m:
        m = re.search(r'房山区.{2,15}(?:河|路|桥|码头|桥下|村|小区|工地)', text)
    if not m:
        m = re.search(r'([一-龥]{2,6}河[一-龥]{0,4}(?:与|和|跟)[一-龥]{2,6}路.{0,6}(?:桥下|交叉|交叉口))', text)
    result['污染地点'] = m.group(0) if m else '未提及'
    
    m = re.search(r'(?:从|自|于)?(\d{4}年\d{1,2}月)', text)
    result['发现时间'] = m.group(1) if m else '未提及'
    
    m = re.search(r'(?:化工厂|养猪场|工地|工厂|企业|养殖场|清淤单位|排放方|施工单位|运输公司|物业公司|环卫|城管|市政)', text)
    if not m:
        if any(w in text for w in ['没人管', '没人清', '一直不', '久拖', '推诿']):
            result['涉事企业/主体'] = '疑似市政/环卫部门（监管缺失）'
        else:
            result['涉事企业/主体'] = '未提及'
    else:
        result['涉事企业/主体'] = m.group(0)
    
    m = re.search(r'(\d+)\s*户|附近居民|周边群众|全校|全村|整条街', text)
    result['影响范围'] = m.group(0) if m else '未提及'
    
    feelings = []
    if any(w in text for w in ['臭', '熏', '呛', '刺鼻', '难闻']):
        feelings.append('恶臭/异味')
    if any(w in text for w in ['吵', '噪音', '响', '震', '轰鸣']):
        feelings.append('噪音扰民')
    if any(w in text for w in ['黑', '脏', '浑浊', '发黄', '变色']):
        feelings.append('视觉污染')
    result['群众感受'] = "、".join(feelings) if feelings else '未提及'
    
    return result


def format_elements(elements):
    """格式化为前端展示文本"""
    if not elements:
        return "—"
    lines = [f"• {k}：{v}" for k, v in elements.items()]
    return "\n".join(lines)


def auto_extract(text, category):
    """按类别自动路由"""
    if category == "民事支持起诉" or "欠薪" in text or "工资" in text:
        return extract_salary_elements(text)
    elif category == "公益诉讼" or any(w in text for w in ["污染", "垃圾", "臭", "黑烟"]):
        return extract_env_elements(text)
    return {}