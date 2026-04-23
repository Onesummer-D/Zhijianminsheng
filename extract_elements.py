# -*- coding: utf-8 -*-
"""
要素提取器 - 针对四大类分别提取结构化信息
当前优先实现：拖欠工资类（榜题明确要求）
"""

import re

def extract_salary_elements(text):
    """拖欠工资类要素提取（纯正则，无需API）"""
    if not text:
        return {}
    
    result = {}
    
    # 1. 工人人数
    m = re.search(r'(\d+)\s*个?\s*(?:工友|工人|农民工|人)', text)
    result['工人人数'] = m.group(1) + '人' if m else '未提及'
    
    # 2. 欠薪数额（优先匹配"欠X万"格式，其次全局找金额）
    m = re.search(r'(?:欠|被欠|拖欠)[^\d。，]{0,8}(\d+(?:\.\d+)?)\s*(?:万|千|百|元|块)', text)
    if not m:
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:万|千|百|元|块)', text)
    result['欠薪数额'] = m.group(0) if m else '未提及'
    
    # 3. 开工/务工时间
    m = re.search(r'(?:从|自)(\d{4}年\d{1,2}月)', text)
    result['开工时间'] = m.group(1) if m else '未提及'
    
    # 4. 欠薪主体
    m = re.search(r'(?:老板|包工头|公司|劳务公司|用人单位|总包|分包)[^\s，。]{0,6}', text)
    result['欠薪主体'] = m.group(0) if m else '未提及'
    
    # 5. 工程地点（房山区内）
    m = re.search(r'房山区[^\s，。]{2,12}(?:镇|街道|乡|村|小区|工地|物流园)', text)
    result['工程地点'] = m.group(0) if m else '未提及'
    
    # 6. 工程项目名称
    m = re.search(r'([一-龥]{2,8}(?:项目|工程|小区|工地|建筑|大棚|装修))', text)
    result['工程项目名称'] = m.group(1) if m else '未提及'
    
    # 7. 是否签订劳动合同
    if any(w in text for w in ['合同', '书面', '协议', '欠条', '字据']):
        result['是否签订劳动合同'] = '是（有书面凭证）'
    elif any(w in text for w in ['没签', '没有合同', '口头', '没写', '不懂']):
        result['是否签订劳动合同'] = '否（口头约定）'
    else:
        result['是否签订劳动合同'] = '未明确'
    
    return result

def extract_env_elements(text):
    """公益诉讼-环境污染类要素提取"""
    result = {}
    
    m = re.search(r'(河水|空气|土壤|地下水|井水|垃圾|噪音|扬尘|黑烟|臭气)', text)
    result['污染类型'] = m.group(1) if m else '未提及'
    
    m = re.search(r'房山区[^\s，。]{2,12}(?:镇|街道|乡|村|小区|河|路)', text)
    result['污染地点'] = m.group(0) if m else '未提及'
    
    m = re.search(r'(\d{4}年\d{1,2}月)', text)
    result['发现时间'] = m.group(1) if m else '未提及'
    
    m = re.search(r'(?:化工厂|养猪场|工地|工厂|企业|养殖场)', text)
    result['涉事企业/主体'] = m.group(0) if m else '未提及'
    
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