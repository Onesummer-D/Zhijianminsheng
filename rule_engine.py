"""
规则引擎模块 - 本地关键词匹配兜底
与DeepSeek API形成"双引擎"架构
"""

import re
from typing import Optional, Dict, List

# 关键词库 - 可维护的法律知识图谱（简化版）
# B同学后续可扩展为从JSON文件读取
KEYWORDS_DB = {
    "公益诉讼": {
        "关键词": ["污染", "环境", "生态", "废水", "废气", "排污", "土壤", "噪音", 
                 "辐射", "破坏", "损毁", "食药", "食品", "药品", "有毒有害"],
        "法条": ["《环境保护法》第58条", "《民事诉讼法》第55条"],
        "置信度": 0.75
    },
    "民事支持起诉": {
        "关键词": ["欠薪", "拖欠工资", "克扣", "未支付", "讨薪", "劳动报酬", 
                 "劳务纠纷", "赡养", "抚养", "抚育费", "弱势群体", "农民工"],
        "法条": ["《劳动合同法》第30条", "《民事诉讼法》第15条"],
        "置信度": 0.72
    },
    "刑事犯罪": {
        "关键词": ["诈骗", "欺诈", "盗窃", "抢劫", "故意伤害", "杀人", "死亡", 
                 "重伤", "非法集资", "传销", "毒品", "制假售假", "伪造", "放火", 
                 "爆炸", "危险物质", "破坏", "贪污", "受贿", "挪用"],
        "法条": ["《刑法》第2条（任务）", "《刑事诉讼法》第3条"],
        "置信度": 0.80
    },
    "行政执法监督": {
        "关键词": ["执法不公", "执法不严", "滥用职权", "程序违法", "不作为", 
                 "乱作为", "越权", "超期办案", "超期羁押", "刑讯逼供", 
                 "违法拘留", "违法查封", "扣押", "冻结", "处罚不当"],
        "法条": ["《行政处罚法》第7条", "《行政诉讼法》第11条"],
        "置信度": 0.70
    }
}

def keyword_match(text: str) -> Optional[str]:
    """
    关键词匹配规则引擎
    输入投诉文本，返回匹配的线索类别或None
    
    算法：简单包含匹配（后续可升级为TF-IDF或正则）
    """
    if not text or not isinstance(text, str):
        return None
    
    text_lower = text.lower()
    matched_categories = []
    
    for category, data in KEYWORDS_DB.items():
        keywords = data["关键词"]
        # 计算命中关键词数
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > 0:
            matched_categories.append((category, hits))
    
    # 返回命中关键词最多的类别
    if matched_categories:
        best_match = max(matched_categories, key=lambda x: x[1])
        return best_match[0]  # 返回类别名
    
    return None

def regex_match(text: str, pattern: str) -> bool:
    """
    正则表达式高级匹配（预留接口）
    用于复杂模式识别，如身份证号、金额、时间等
    """
    if not text:
        return False
    try:
        return bool(re.search(pattern, text, re.IGNORECASE))
    except re.error:
        return False

def get_law_reference(category: str) -> List[str]:
    """
    获取某类别的相关法律依据
    """
    if category in KEYWORDS_DB:
        return KEYWORDS_DB[category]["法条"]
    return ["暂无明确法条"]

def get_confidence(category: str) -> float:
    """
    获取规则引擎对该类别的置信度基准
    """
    if category in KEYWORDS_DB:
        return KEYWORDS_DB[category]["置信度"]
    return 0.5

def fusion_result(api_result: dict, rule_category: Optional[str]) -> dict:
    """
    双引擎融合：API结果 + 规则引擎结果
    
    融合策略：
    1. 如果API和规则一致 -> 高置信度
    2. 如果API和规则不一致 -> 取API（优先语义理解），但标记"建议复核"
    3. 如果规则有但API无 -> 补充API盲区
    4. 如果都没有 -> 普通投诉
    
    参数:
        api_result: DeepSeek API返回结果 {"type": "类别", "confidence": 0.8, ...}
        rule_category: 规则引擎匹配结果（如"公益诉讼"）或None
        
    返回:
        dict: 融合后的最终结果
    """
    api_type = api_result.get("type", "普通投诉")
    api_conf = api_result.get("confidence", 0.0)
    
    # 情况1：双引擎一致（增强置信度）
    if rule_category and rule_category == api_type:
        final_conf = min(api_conf + 0.15, 0.95)  # 置信度+15%，上限95%
        return {
            "type": api_type,
            "confidence": final_conf,
            "law": api_result.get("law", get_law_reference(api_type)[0]),
            "reason": api_result.get("reason", "规则与AI双重验证"),
            "suggestion": api_result.get("suggestion", "建议优先处理"),
            "method": "双引擎融合（高可信）"
        }
    
    # 情况2：规则有，API无（API漏检，规则兜底）
    elif rule_category and api_type == "普通投诉":
        return {
            "type": rule_category,
            "confidence": get_confidence(rule_category),
            "law": get_law_reference(rule_category)[0],
            "reason": "基于关键词规则匹配发现线索",
            "suggestion": "建议人工复核后确认",
            "method": "规则引擎兜底"
        }
    
    # 情况3：API有，规则无（AI发现隐性线索）
    elif api_type != "普通投诉" and not rule_category:
        return {
            "type": api_type,
            "confidence": api_conf,
            "law": api_result.get("law", "相关法律规定"),
            "reason": api_result.get("reason", "AI语义分析识别"),
            "suggestion": api_result.get("suggestion", "建议审查"),
            "method": "AI语义分析"
        }
    
    # 情况4：不一致（冲突，需人工复核）
    elif rule_category and api_type != rule_category:
        return {
            "type": api_type,  # 优先AI判断
            "confidence": api_conf * 0.8,  # 置信度打折
            "law": api_result.get("law", "待核实"),
            "reason": f"AI判断为{api_type}，但规则匹配{rule_category}，存在分歧",
            "suggestion": "⚠️ 建议人工复核分类准确性",
            "method": "双引擎分歧（需复核）"
        }
    
    # 情况5：都无（普通投诉）
    else:
        return {
            "type": "普通投诉",
            "confidence": 0.1,
            "law": "不涉及检察机关监督职能",
            "reason": "未识别出涉检线索特征",
            "suggestion": "按普通信访事项分流处理",
            "method": "无匹配"
        }

def batch_keyword_match(texts: List[str]) -> List[Optional[str]]:
    """
    批量关键词匹配（用于Excel批量处理）
    """
    return [keyword_match(t) for t in texts]

# 测试代码
if __name__ == "__main__":
    test_cases = [
        "工厂废水排到河里，河水变黑了",
        "公司拖欠我三个月工资不给",
        "有人诈骗了我5万块钱",
        "路边停车被贴条了，觉得不合理"
    ]
    
    print("=== 规则引擎测试 ===")
    for text in test_cases:
        category = keyword_match(text)
        conf = get_confidence(category) if category else 0.0
        print(f"文本: {text[:20]}... -> 类别: {category}, 置信度: {conf:.2f}")