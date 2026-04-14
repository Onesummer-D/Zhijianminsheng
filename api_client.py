import os
import time
import requests
import json
import re
from typing import Dict, Optional

class DeepSeekClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API Key 未设置")
        
        self.base_url = "https://api.deepseek.com"
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _clean_json_response(self, content: str) -> str:
        """清洗Markdown代码块，提取纯JSON"""
        # 去掉 ```json 或 ``` 包裹
        if content.strip().startswith("```"):
            # 提取 ``` 和 ``` 之间的内容
            match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return content.strip()
    
    def analyze_complaint(self, text: str, max_retries: int = 3) -> Dict:
        prompt = f"""你是一个专业的检察院案件筛查助手。请分析以下12345投诉文本，判断其是否涉及检察监督线索。

投诉内容：{text}

请严格按照以下JSON格式返回（不要包含其他内容）：
{{
    "is_relevant": true/false,
    "category": "刑事犯罪/公益诉讼/民事支持起诉/行政执法监督/不涉及",
    "confidence": 85,
    "legal_basis": "相关法律条款",
    "reasoning": "简要判断理由",
    "risk_level": "高/中/低"
}}"""

        messages = [
            {"role": "system", "content": "你是一个专业的检察院案件筛查助手，擅长从12345投诉中识别涉检线索。"},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                try:
                    # 清洗Markdown格式后解析
                    clean_content = self._clean_json_response(content)
                    parsed = json.loads(clean_content)
                    return {
                        'is_relevant': parsed.get('is_relevant', False),
                        'category': parsed.get('category', '不涉及'),
                        'confidence': parsed.get('confidence', 0),
                        'legal_basis': parsed.get('legal_basis', ''),
                        'reasoning': parsed.get('reasoning', ''),
                        'risk_level': parsed.get('risk_level', '低'),
                        'raw_response': content
                    }
                except json.JSONDecodeError as e:
                    return {
                        'is_relevant': False,
                        'category': '解析失败',
                        'confidence': 0,
                        'error': f'JSON解析失败: {str(e)}',
                        'raw_response': content
                    }
                    
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    return {'error': 'API请求超时', 'is_relevant': False}
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    return {'error': f'API请求失败: {str(e)}', 'is_relevant': False}
                time.sleep(2 ** attempt)
        
        return {'error': '未知错误', 'is_relevant': False}

if __name__ == "__main__":
    client = DeepSeekClient()
    
    test_text = "工厂拖欠农民工工资三个月不给"
    print(f"测试投诉：{test_text}")
    result = client.analyze_complaint(test_text)
    print(f"分析结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
