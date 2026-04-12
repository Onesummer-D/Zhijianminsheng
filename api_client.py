"""
API调用模块 - 由B同学负责实现DeepSeek调用
当前为Mock版本，B拿到Key后替换真实调用
"""

import json
import requests  # B需要安装: pip install requests

def classify_complaint(text: str) -> dict:
    """
    调用DeepSeek API对投诉文本进行涉检线索分类
    
    参数:
        text: 投诉文本字符串
        
    返回:
        dict: {
            "type": "线索类型（刑事犯罪/公益诉讼/民事支持起诉/行政执法监督）",
            "confidence": 置信度(0-1),
            "law": "相关法律依据",
            "reason": "分析理由",
            "suggestion": "处置建议"
        }
    
    TODO: B同学在此处实现真实DeepSeek API调用
    当前返回Mock数据用于界面测试
    """
    
    # 临时Mock逻辑（B后续替换为真实API）
    text = str(text).lower() if text else ""
    
    if any(kw in text for kw in ["污染", "环境", "废水", "排污", "生态"]):
        return {
            "type": "公益诉讼",
            "confidence": 0.85,
            "law": "《环境保护法》第58条",
            "reason": "涉及环境污染或生态破坏线索",
            "suggestion": "建议移送公益诉讼检察部门审查"
        }
    elif any(kw in text for kw in ["欠薪", "拖欠工资", "克扣报酬", "劳务纠纷"]):
        return {
            "type": "民事支持起诉",
            "confidence": 0.82,
            "law": "《劳动合同法》第30条",
            "reason": "用人单位拖欠劳动报酬",
            "suggestion": "建议民事检察部门支持起诉"
        }
    elif any(kw in text for kw in ["诈骗", "盗窃", "故意伤害", "非法集资"]):
        return {
            "type": "刑事犯罪",
            "confidence": 0.88,
            "law": "《刑法》相关条款",
            "reason": "涉嫌刑事犯罪，需进一步侦查",
            "suggestion": "建议移送刑事检察部门"
        }
    elif any(kw in text for kw in ["执法不公", "滥用职权", "程序违法"]):
        return {
            "type": "行政执法监督",
            "confidence": 0.75,
            "law": "《行政处罚法》相关条款",
            "reason": "行政执法行为可能存在违法",
            "suggestion": "建议行政检察部门监督"
        }
    else:
        return {
            "type": "普通投诉",
            "confidence": 0.15,
            "law": "不涉及检察机关监督职能",
            "reason": "暂未识别出涉检线索",
            "suggestion": "建议按普通信访事项处理"
        }

def test_api_connection(api_key: str) -> bool:
    """
    测试DeepSeek API连接（B同学实现）
    
    参数:
        api_key: DeepSeek API密钥
        
    返回:
        bool: 连接成功返回True，否则False
    """
    # TODO: B同学实现真实测试
    # 示例代码（B参考）：
    # headers = {"Authorization": f"Bearer {api_key}"}
    # response = requests.get("https://api.deepseek.com/v1/models", headers=headers)
    # return response.status_code == 200
    
    return True  # 临时返回True

# 如果直接运行此文件，进行简单测试
if __name__ == "__main__":
    test_text = "公司拖欠员工工资三个月"
    result = classify_complaint(test_text)
    print("测试结果:", json.dumps(result, ensure_ascii=False, indent=2))