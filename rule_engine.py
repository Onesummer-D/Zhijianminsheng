"""
规则引擎模块 - 双层级权重 + 双引擎融合
"""

import json
import os
from typing import Optional, Dict, List

# ========== 加载关键词库（从Python文件或JSON） ==========
# 方案1：如果用了convert_excel.py生成，就导入
try:
    from rule_engine_keywords import KEYWORDS_DB, calculate_confidence, keyword_match
except ImportError:
    # 备用：空库，防止报错
    KEYWORDS_DB = {}
    def calculate_confidence(text, category): return {"score":0, "confidence":"低"}
    def keyword_match(text): return None

# ========== 加载法条库 ==========
def load_legal_basis():
    """加载法条关联表JSON"""
    path = os.path.join(os.path.dirname(__file__), 'data', 'legal_basis.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

LEGAL_BASIS = load_legal_basis()

# ========== 获取法条（用于界面显示） ==========
def get_laws_for_category(category: str) -> dict:
    """
    返回某类别的法条（分default和extended）
    如果法条库未生成，返回模拟数据
    """
    if category in LEGAL_BASIS:
        return LEGAL_BASIS[category]
    
    # 备用模拟数据（防止文件不存在时报错）
    return {
        "default": [
            {"编号": "《刑法》第276条之一", "内容": "拒不支付劳动报酬罪", "场景": "恶意欠薪"},
            {"编号": "《劳动合同法》第30条", "内容": "用人单位应当按时足额支付劳动报酬", "场景": "拖欠工资"},
            {"编号": "《保障农民工工资支付条例》第10条", "内容": "农民工工资应以货币形式按时足额支付", "场景": "农民工讨薪"}
        ],
        "extended": [
            {"编号": "《劳动法》第50条", "内容": "工资应当以货币形式按月支付", "场景": "工资支付"},
            {"编号": "《信访工作条例》第31条", "内容": "信访事项处理", "场景": "信访"}
        ]
    }

# ========== 双引擎融合（保留你原来的逻辑，适配新数据结构） ==========
def fusion_result(api_result: dict, rule_category: Optional[str], rule_conf_detail: dict = None) -> dict:
    """
    双引擎融合：DeepSeek API + 规则引擎
    
    参数:
        api_result: {"type": "类别", "confidence": 0.8, ...}
        rule_category: 规则匹配到的类别名（如"民事支持起诉"）
        rule_conf_detail: calculate_confidence返回的详细结果（含score, confidence高/中/低）
    """
    api_type = api_result.get("type", "普通投诉")
    api_conf = api_result.get("confidence", 0.0)
    
    # 规则置信度转数值
    rule_conf_str = rule_conf_detail.get("confidence", "低") if rule_conf_detail else "低"
    conf_map = {"高": 0.85, "中": 0.60, "低": 0.35}
    rule_conf_value = conf_map.get(rule_conf_str, 0.35) if rule_category else 0
    
    # 情况1：双引擎一致且高置信度
    if rule_category and rule_category == api_type and rule_conf_str == "高":
        return {
            "type": api_type,
            "confidence": "高",
            "confidence_score": max(api_conf, rule_conf_value),
            "law": get_laws_for_category(api_type),
            "method": "双引擎融合（高可信）",
            "reason": f"规则与AI双重验证，命中核心词：{rule_conf_detail.get('matched_core', [])}",
            "suggestion": "建议优先处理"
        }
    
    # 情况2：规则有，API无（兜底）
    elif rule_category and api_type == "普通投诉":
        return {
            "type": rule_category,
            "confidence": rule_conf_str,  # 直接返回高/中/低
            "confidence_score": rule_conf_value,
            "law": get_laws_for_category(rule_category),
            "method": "规则引擎兜底",
            "reason": f"基于关键词规则匹配发现线索，得分：{rule_conf_detail.get('score', 0)}",
            "suggestion": "建议人工复核后确认",
            "matched_keywords": rule_conf_detail.get("matched_core", []) + rule_conf_detail.get("matched_feature", [])
        }
    
    # 情况3：API有，规则无（AI发现隐性线索）
    elif api_type != "普通投诉" and not rule_category:
        return {
            "type": api_type,
            "confidence": "中" if api_conf > 0.7 else "低",
            "confidence_score": api_conf,
            "law": get_laws_for_category(api_type),
            "method": "AI语义分析",
            "reason": api_result.get("reason", "AI语义分析识别出涉检线索"),
            "suggestion": "建议审查"
        }
    
    # 情况4：不一致（冲突）
    elif rule_category and api_type != rule_category:
        return {
            "type": api_type,  # 优先AI
            "confidence": "中",  # 置信度打折
            "confidence_score": api_conf * 0.8,
            "law": get_laws_for_category(api_type),
            "method": "双引擎分歧（需复核）",
            "reason": f"AI判断为{api_type}，但规则匹配{rule_category}",
            "suggestion": "⚠️ 建议人工复核分类准确性"
        }
    
    # 情况5：都无
    else:
        return {
            "type": "普通投诉",
            "confidence": "低",
            "confidence_score": 0.1,
            "law": {"default": [], "extended": []},
            "method": "无匹配",
            "reason": "未识别出涉检线索特征",
            "suggestion": "按普通信访事项分流处理"
        }

# 测试
if __name__ == "__main__":
    # 测试法条加载
    print("法条库加载测试：", list(LEGAL_BASIS.keys())[:3] if LEGAL_BASIS else "使用模拟数据")
    
    # 测试融合
    api_mock = {"type": "民事支持起诉", "confidence": 0.8}
    rule_cat = "民事支持起诉"
    rule_detail = {"score": 7, "confidence": "高", "matched_core": ["恶意欠薪"]}
    result = fusion_result(api_mock, rule_cat, rule_detail)
    print("融合结果：", result["type"], result["confidence"], result["method"])