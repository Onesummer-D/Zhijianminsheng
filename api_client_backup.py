#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek API 客户端 - 优化完整版
包含：字段修复、房山特色、日志记录、详细降级策略
"""

import os
import time
import requests
import json
import re
import logging
from typing import Dict, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class DeepSeekClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API Key 未设置，请设置环境变量 DEEPSEEK_API_KEY")

        self.base_url = "https://api.deepseek.com"
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)
        self.logger.info("DeepSeek客户端初始化完成")

    def _clean_json_response(self, content: str) -> str:
        """清理API返回的JSON字符串"""
        if content.strip().startswith("```"):
            match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return content.strip()

    def analyze_complaint(self, text: str, max_retries: int = 3) -> Dict:
        """
        基础单标签分析（兼容性保留）
        """
        prompt = f"""你是一个专业的检察院案件筛查助手。请分析以下12345投诉文本：

投诉内容：{text}

请严格按照以下JSON格式返回：
{{
    "is_relevant": true/false,
    "category": "刑事犯罪/公益诉讼/民事支持起诉/行政执法监督/不涉及",
    "confidence": 85,
    "legal_basis": "相关法律条款",
    "reasoning": "简要判断理由",
    "risk_level": "高/中/低"
}}"""

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是检察分类专家，只输出JSON。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }

        for attempt in range(max_retries):
            try:
                self.logger.info(f"调用DeepSeek基础分析 (尝试 {attempt+1}/{max_retries})")
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']

                clean_content = self._clean_json_response(content)
                parsed = json.loads(clean_content)

                risk_level = parsed.get('risk_level', '低')
                self.logger.info(f"基础分析完成: {parsed.get('category', '未知')} ({risk_level})")

                return {
                    'type': parsed.get('category', '不涉及'),
                    'category': parsed.get('category', '不涉及'),
                    'confidence': risk_level,
                    'score': 8 if risk_level == "高" else (5 if risk_level == "中" else 2),
                    'is_procuratorial': parsed.get('is_relevant', False),
                    'matched': [parsed.get('legal_basis', '')] if parsed.get('legal_basis') else [],
                    'reasoning': parsed.get('reasoning', 'AI分析'),  # 修复：使用reasoning
                    'method': 'DeepSeek API'
                }

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON解析失败: {e}")
                if attempt == max_retries - 1:
                    return {'type': '解析失败', 'is_procuratorial': False, 'method': 'API', 'reasoning': 'JSON解析错误'}
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                self.logger.error(f"请求失败: {e}")
                if attempt == max_retries - 1:
                    return {'type': '请求失败', 'is_procuratorial': False, 'method': 'API', 'reasoning': f'网络错误: {str(e)[:30]}'}
                time.sleep(2 ** attempt)

        return {'type': '未知错误', 'is_procuratorial': False, 'method': 'API', 'reasoning': '达到最大重试次数'}

    def analyze_multi_label(self, text: str, rule_primary: str, rule_secondaries: list, all_scores: dict) -> dict:
        """
        多标签语义精修：识别规则引擎遗漏的隐性法律关系
        【房山区特色】重点关注建筑工地、非法采砂、养殖排污、违建执法
        """
        # 构建当前规则引擎结果描述
        current_status = f"主要类别：{rule_primary}（{all_scores.get(rule_primary, 0)}分）"
        if rule_secondaries:
            sec_desc = ", ".join([f"{s['category']}({s['score']}分)" for s in rule_secondaries])
            current_status += f"，次要类别：{sec_desc}"
        else:
            current_status += "，次要类别：无"

        self.logger.info(f"开始多标签精修分析: {current_status}")

        prompt = f"""作为资深检察官，分析以下12345工单的多标签分类。

【房山区特色重点关注】
- 建筑工地农民工讨薪（房山在建项目多，注意"逃匿"证据）
- 非法采砂/挖山/盗采砂石（房山山区资源保护）
- 养殖场排污/畜禽粪便（房山农业区环境污染）
- 违建拆除执法监督（房山城乡结合部执法问题）
- 小过重罚/首违不罚（房山小商贩执法监督）

当前规则引擎初步判断：{current_status}
各类别得分：{all_scores}

工单内容：{text}

【重要约束】只有在文本**明确提到**以下刑事要素时，才识别为刑事犯罪：
- 逃匿/跑路/找不到人/关机失联（拒不支付劳动报酬罪）
- 暴力威胁/伤害/打断腿/动刀子（故意伤害/寻衅滋事罪）
- 非法采矿/严重污染/破坏生态（非法采矿罪/污染环境罪）
- 诈骗/传销/非法集资/杀猪盘（诈骗罪/组织传销罪）

**禁止过度推断**：如果文本仅描述"拖欠工资"而没有"逃匿"证据，不要强行认定为刑事犯罪。

请进行语义分析：
1. **显性线索识别**：文本明确提到的法律关系
2. **主次类别精修**（必须选1个主要，0-2个次要）：
   - 主要类别
   - 次要类别（按证据充分性排序）

3. **处理建议**（根据主要类别动态调整）：
   - 若主要类别=民事支持起诉 → 建议"先刑后民"（如有刑事）或"并案处理"
   - 若主要类别=公益诉讼 → 建议"先刑后公"（如有刑事）或"公益优先"
   - 若主要类别=刑事犯罪 → 建议"刑事优先"
   - 若主要类别=行政执法监督 → 建议"行政整改"

4. **交叉判断**：列出所有涉及的类别（如"刑民交叉"、"行刑公交叉"等）

严格按JSON格式返回：
{{
    "primary_category": "主要类别",
    "secondary_categories": ["次要类别1", "次要类别2"],
    "is_cross_case": true/false,
    "cross_type": "刑民交叉/行刑公交叉/行政执法监督与公益交叉/无",
    "handling_suggestion": "分案处理/并案处理/先刑后民/先刑后公/刑事优先/公益优先",
    "amount_assessment": "数额较大/数额巨大/无",
    "key_elements": ["明确识别的关键要素"],
    "reasoning": "简要说明，特别是为什么排除某些类别",
    "confidence": 85
}}"""

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是检察业务专家，擅长从口语化投诉中识别多重法律关系。只输出JSON。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}
        }

        try:
            self.logger.info("调用DeepSeek多标签分析API...")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']

            clean_content = self._clean_json_response(content)
            parsed = json.loads(clean_content)

            self.logger.info(f"多标签分析完成: 主={parsed.get('primary_category')}, 次={parsed.get('secondary_categories')}")

            return {
                'primary': parsed.get('primary_category', rule_primary),
                'secondaries': parsed.get('secondary_categories', []),
                'is_cross': parsed.get('is_cross_case', False),
                'cross_type': parsed.get('cross_type', '无'),
                'handling': parsed.get('handling_suggestion', '并案处理'),
                'amount': parsed.get('amount_assessment', '无'),
                'elements': parsed.get('key_elements', []),
                'reasoning': parsed.get('reasoning', '语义分析'),  # 修复：使用reasoning匹配前端
                'confidence': parsed.get('confidence', 80),
                'is_procuratorial': True
            }

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"多标签API分析失败: {error_msg}")

            # 优化降级：返回带详细错误信息的规则引擎结果
            secondary_names = [s['category'] for s in rule_secondaries] if rule_secondaries else []

            return {
                'primary': rule_primary,
                'secondaries': secondary_names,
                'is_cross': len(rule_secondaries) > 0,
                'cross_type': f'API错误: {error_msg[:20]}',
                'handling': f'规则引擎判定: {rule_primary}',
                'amount': '无',
                'elements': [f'API异常: {error_msg[:30]}'],
                'reasoning': f'API调用失败({error_msg[:25]})，降级使用规则引擎结果。建议检查网络或API余额。',
                'confidence': 60,
                'is_procuratorial': True
            }

def analyze_with_deepseek(text: str) -> Dict:
    """便捷函数：快速分析"""
    client = DeepSeekClient()
    return client.analyze_complaint(text)

# 测试代码
if __name__ == "__main__":
    # 测试用例
    test_text = "房山区长阳镇某工地，包工头拖欠我们20多个农民工工资80多万，现在人跑了电话关机。"

    client = DeepSeekClient()

    print("=== 测试基础分析 ===")
    result = client.analyze_complaint(test_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n=== 测试多标签分析 ===")
    all_scores = {
        "刑事犯罪": 6,
        "民事支持起诉": 15,
        "公益诉讼": 0,
        "行政执法监督": 0
    }
    result2 = client.analyze_multi_label(
        test_text, 
        "民事支持起诉", 
        [{"category": "刑事犯罪", "score": 6}],
        all_scores
    )
    print(json.dumps(result2, ensure_ascii=False, indent=2))