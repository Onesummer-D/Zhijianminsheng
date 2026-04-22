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
        if content.strip().startswith("```"):
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return content.strip()

    def analyze_complaint(self, text: str, max_retries: int = 3) -> Dict:
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
                    'reasoning': parsed.get('reasoning', 'AI分析'),
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
        current_status = f"主要类别：{rule_primary}（{all_scores.get(rule_primary, 0)}分）"
        if rule_secondaries:
            sec_desc = ", ".join([f"{s['category']}({s['score']}分)" for s in rule_secondaries])
            current_status += f"，次要类别：{sec_desc}"
        else:
            current_status += "，次要类别：无"

        self.logger.info(f"开始多标签精修分析: {current_status}")

        system_prompt = """你是一位北京市房山区人民检察院的涉检线索分类专家，严格依据《中华人民共和国刑事诉讼法》《中华人民共和国民事诉讼法》《中华人民共和国行政诉讼法》及四大检察法定职责进行判断。

【铁律 - 禁止臆想】
- 仅根据文本中已经明确发生的事实进行分类，严禁推测、假设、联想未来可能性。
- 严禁因为"如果执法部门不作为""若诉后行政机关不履职"等假设性场景添加类别。
- 严禁将公民"向行政机关投诉举报"直接等同于"行政执法监督"。
- 严禁将"可能构成犯罪"直接等同于"已经构成犯罪"。刑事犯罪的认定必须有明确的刑法条文支撑，且文本事实已达到入罪标准。

【四大检察法定边界 - 严格遵循】

1. 刑事犯罪（刑事检察）- 【极高门槛】
   - 适用条件：行为已经触犯《中华人民共和国刑法》，且文本中已有事实表明达到入罪标准，需要追究刑事责任。
   - 【关键原则】不能仅凭"严重""恶劣""必须严惩"等情绪词推定刑事犯罪。必须有具体罪名对应的客观要件。
   - 常见罪名与严格入罪标准：
     * 高空抛物罪（刑法第291条之二）：从建筑物抛掷物品，情节严重。如"从12楼扔垃圾袋砸坏汽车"可直接认定。
     * 污染环境罪（刑法第338条）：排放、倾倒、处置有毒物质或其他有害物质，严重污染环境。
       【门槛】仅凭"发黄的水""难闻"不能直接认定，必须文本明确提及"有毒物质""危险废物""重金属超标"或"造成严重后果"。一般的生活垃圾倾倒、建筑垃圾堆放，如无有毒有害物质描述，不构成此罪。
     * 非法采矿罪（刑法第343条）：未取得采矿许可证擅自采矿。如"偷偷挖山卖石头""盗采砂石"且规模较大。
     * 非法占用农用地罪（刑法第342条）：非法占用耕地、林地等，数量较大，造成大量毁坏。
     * 拒不支付劳动报酬罪（刑法第276条之一）：【必须有行政前置程序】"以转移财产、逃匿等方法逃避支付劳动报酬，或有能力支付而不支付，数额较大，经政府有关部门责令支付仍不支付的"。
       【关键】仅描述"拖欠工资""不给钱"不构成此罪，必须文本明确提及"经劳动监察责令支付仍不支付"或"逃匿/转移财产"。
     * 故意伤害罪/寻衅滋事罪：必须有实际的暴力威胁或伤害行为，如"打断腿""找人收拾""拿棍子威胁"。
     * 故意损毁文物罪（刑法第324条）：【严格区分】仅适用于"国家保护的珍贵文物"或"全国重点文物保护单位、省级文物保护单位"。
       【关键区分】如果文本仅提及"历史建筑""老宅子""登记在册的历史建筑"，未明确说明是"文物保护单位"，则不构成故意损毁文物罪，应归入公益诉讼（文物保护）或普通行政违法。
   - 【禁止】严禁因为"涉及多个类别"就把刑事犯罪强行提升为主要类别。主要类别应根据文本事实最突出的法律关系确定。

2. 公益诉讼
   - 适用条件：损害国家利益或社会公共利益（生态环境、食品药品安全、国有财产保护、英烈权益保护、文物保护等），且依法应由检察机关提起公益诉讼。
   - 常见场景：
     * 非法排污（但尚未达到刑事立案标准）
     * 垃圾填埋、建筑垃圾堆放（一般环境污染）
     * 破坏文物/历史建筑（非文物保护单位，或尚未达到刑事立案标准）
     * 危害食品安全等
   - 注意：如果破坏环境/文物的行为同时明确达到刑事立案标准（如已确认为有毒物质、已确认为文物保护单位且严重损毁），刑事犯罪可作为主要或次要类别。

3. 民事支持起诉（民事检察）
   - 适用条件：弱势群体（农民工、老年人、残疾人等）因自身诉讼能力较弱，难以通过民事诉讼维护权益，需要检察机关支持起诉。
   - 常见场景：农民工讨薪、赡养费纠纷、人身损害赔偿等。
   - 注意：讨薪类案件，如仅有欠薪事实，主要类别应为民事支持起诉。暴力威胁可作为次要类别（刑事犯罪），但处理方式不是"先刑后民"，而是"刑民并行"或"行政前置+刑民并行"。

4. 行政执法监督（行政检察）- 【严格门槛】
   - 适用条件：必须是行政机关已经作出的具体行政行为违法，或行政机关经投诉举报后负有法定监管职责而明确拒不履行/违法履行，且该行为侵犯了公民合法权益或损害了公共利益。
   - 常见场景：
     * 行政处罚程序违法（如不出示证件、不告知权利）
     * 行政机关经明确投诉后仍不作为（如多次向环保局举报排污，环保局明确拒绝调查）
     * 同案不同罚、小过重罚、首违不罚等执法不公
   - 【反例 - 以下情形绝对不属于行政执法监督】：
     * 公民向市场监管局/环保局/城管局"投诉举报"要求履行职责（这是公民启动行政程序的权利，不等于行政执法监督案件）。
     * 文物被拆除后要求"文物部门和城管介入"（这是要求行政机关启动执法程序，不等于行政执法监督）。
     * 垃圾堆积"希望政府清理"（这是市政服务诉求）。
     * 行政机关尚未作出行政行为，仅处于"应当管但还没管"的状态。
     * KTV噪音"希望环保部门来测测噪音"（这是投诉举报，如环保部门已明确拒绝处理，才构成行政执法监督）。

【处理方式说明】
- 处理方式应根据实际法律关系确定，严禁机械套用"先刑后民""先刑后公"。
- 拒不支付劳动报酬类：应标注"行政前置 → 刑民并行"（先向劳动监察投诉，同时可申请民事支持起诉）。
- 一般环境污染类：应标注"行政调查优先"（先由环保部门调查，涉嫌犯罪的再移送）。
- 只有明确达到刑事立案标准且无行政前置要求的，才可标注"刑事优先"。

【输出格式要求】
- primary_category：唯一主要类别，必须是"刑事犯罪""公益诉讼""民事支持起诉""行政执法监督"四者之一。
- secondary_categories：最多2个次要类别，且每个必须有文本事实支撑，严禁基于假设添加。
- reasoning：简要说明判定依据，必须引用文本中的具体事实，特别是为什么排除某些类别。
- handling_suggestion：根据实际法律关系给出合理建议（如"分案处理""并案处理""行政前置+刑民并行""行政调查优先"等），严禁机械套用"先刑后民"。
"""

        user_prompt = f"""请对以下12345工单进行涉检线索分类。

【工单内容】
{text}

【规则引擎初步结果】
{current_status}
各类别得分：{all_scores}

【房山区特色重点关注】
- 建筑工地农民工讨薪（注意"逃匿/经责令支付仍不支付"的刑事门槛）
- 非法采砂/挖山/盗采砂石（房山山区资源保护，注意是否达到刑事立案标准）
- 养殖场排污/畜禽粪便（房山农业区环境污染，注意是否涉及有毒物质）
- 违建拆除执法监督（房山城乡结合部执法问题，注意是否经投诉后行政机关仍不作为）
- 小过重罚/首违不罚（房山小商贩执法监督）
- 历史建筑/文物破坏（房山历史文化名城保护，注意区分"历史建筑"与"文物保护单位"）

【要求】
1. 基于文本事实，判断上述规则引擎结果是否正确。
2. 如果规则引擎将"历史建筑拆除"错误认定为"刑事犯罪"（故意损毁文物罪），请纠正：只有"全国重点文物保护单位、省级文物保护单位"才适用刑法第324条，一般"历史建筑"应归入公益诉讼或行政违法。
3. 如果规则引擎将一般环境污染（生活垃圾、建筑垃圾堆放）错误认定为"刑事犯罪"（污染环境罪），请纠正：必须文本明确提及"有毒物质""危险废物""重金属超标"才构成刑事犯罪。
4. 如果规则引擎将"拖欠工资"错误认定为"刑事犯罪"（拒不支付劳动报酬罪），请纠正：必须文本明确提及"经政府有关部门责令支付仍不支付"或"逃匿/转移财产"才构成此罪。
5. 如果规则引擎错误地将"投诉举报""要求政府清理""希望文物部门介入"等判定为"行政执法监督"，请删除并纠正。
6. 返回JSON格式：
{{
    "primary_category": "主要类别",
    "secondary_categories": ["次要类别1", "次要类别2"],
    "is_cross_case": true/false,
    "cross_type": "刑民交叉/行刑公交叉/无",
    "handling_suggestion": "分案处理/并案处理/行政前置+刑民并行/行政调查优先/刑事优先",
    "amount_assessment": "数额较大/数额巨大/无",
    "key_elements": ["明确识别的关键要素"],
    "reasoning": "简要说明，特别是为什么排除某些类别",
    "confidence": 85
}}
"""

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
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
                'reasoning': parsed.get('reasoning', '语义分析'),
                'confidence': parsed.get('confidence', 80),
                'is_procuratorial': True
            }

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"多标签API分析失败: {error_msg}")

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
    client = DeepSeekClient()
    return client.analyze_complaint(text)


if __name__ == "__main__":
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