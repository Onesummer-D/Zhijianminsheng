import gradio as gr
import json
import os
import re
from typing import Dict, List, Optional

# ========== 加载规则引擎 ==========
try:
    from rule_engine_keywords import KEYWORDS_DB, calculate_confidence, keyword_match
    RULE_ENGINE_READY = True
    print("✅ 成功加载关键词库")
except ImportError as e:
    print(f"⚠️ 规则引擎导入失败: {e}")
    RULE_ENGINE_READY = False
    def keyword_match(text): return None
    def calculate_confidence(text, cat): return {"score": 0, "confidence": "低", "matched_core": [], "matched_feature": []}
    KEYWORDS_DB = {}

# ========== 加载法条库 ==========
def load_legal_basis():
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'data', 'legal_basis.json'),
        os.path.join(os.getcwd(), 'data', 'legal_basis.json'),
        '/root/zhijianminsheng/data/legal_basis.json',
        './data/legal_basis.json'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ 成功加载法条库: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    print("⚠️ 法条库文件不存在，使用模拟数据")
    return {}

LEGAL_BASIS = load_legal_basis()

def get_laws_for_category(category: str) -> dict:
    if category in LEGAL_BASIS:
        return LEGAL_BASIS[category]
    
    return {
        "default": [
            {"编号": "《刑法》第276条之一", "内容": "拒不支付劳动报酬罪", "场景": "恶意欠薪"},
            {"编号": "《劳动合同法》第30条", "内容": "用人单位应当按时足额支付劳动报酬", "场景": "拖欠工资"},
        ],
        "extended": []
    }

# ========== 最终修复版：点位提取（绝对严格） ==========
def extract_location(text):
    """
    严格提取地址：必须清洗所有前缀，精确匹配镇/街道+村/小区结构
    """
    if not text:
        return None
    
    # 第一步：找到第一个镇/街道/村/小区的位置
    # 在"房山区长阳镇"中，"长阳镇"是地址核心
    
    # 策略：从"区"字后开始抓，或者直接从"镇/街道"向前抓2-4字向后抓0-12字
    # 匹配模式：XX区XX镇/街道XX村/小区/路/号
    
    patterns = [
        # 模式1：完整的【区+镇/街道+村/小区】
        r'([\u4e00-\u9fa5]{2,4}区)([\u4e00-\u9fa5]{2,6}(?:镇|街道|乡))([\u4e00-\u9fa5]{2,12}(?:村|社区|小区|家园|花园|公寓|路|街))',
        # 模式2：【镇/街道+村/小区】（前面没有区）
        r'([\u4e00-\u9fa5]{2,6}(?:镇|街道|乡))([\u4e00-\u9fa5]{2,12}(?:村|社区|小区|家园|花园|公寓))',
        # 模式3：【区+镇/街道】（兜底）
        r'([\u4e00-\u9fa5]{2,4}区)([\u4e00-\u9fa5]{2,6}(?:镇|街道|乡))',
        # 模式4：纯【村/小区/路】（兜底）
        r'([\u4e00-\u9fa5]{2,12}(?:村|社区|小区|路|街|号)[^\s，。,.]{0,8})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # 拼接所有捕获组
            addr = ''.join(filter(None, match.groups()))
            # 清理残余
            addr = re.sub(r'^[的是位于在老板住]+', '', addr)
            if len(addr) >= 4:
                return addr
    
    # 终极兜底：如果文本里有"长阳镇碧桂园"这种模式，直接抓
    match = re.search(r'([^\s，。,.]{2,6}镇[^\s，。,.]{2,10}小区)', text)
    if match:
        return match.group(1)
    
    return None

# ========== 双引擎融合 ==========
def fusion_result(api_result: dict, rule_category: Optional[str], rule_conf_detail: dict = None) -> dict:
    api_type = api_result.get("type", "普通投诉")
    
    rule_conf_str = rule_conf_detail.get("confidence", "低") if rule_conf_detail else "低"
    rule_score = rule_conf_detail.get("score", 0) if rule_conf_detail else 0
    matched_core = rule_conf_detail.get("matched_core", []) if rule_conf_detail else []
    
    # 非涉检线索
    if not rule_category:
        return {
            "type": "普通投诉（非涉检）",
            "confidence": "低",
            "confidence_score": 0.1,
            "law": {"default": [], "extended": []},
            "method": "规则引擎过滤",
            "reason": "未匹配任何涉检关键词",
            "suggestion": "❌ 非检察机关管辖范围，建议转交信访/相关部门处理",
            "matched_core": [],
            "matched_feature": [],
            "is_procuratorial": False,
            "score": 0
        }
    
    # 根据分数给出不同建议
    if rule_conf_str == "高":
        suggestion = "✅ 建议优先处理（高置信度）"
    elif rule_conf_str == "中":
        suggestion = "⚠️ 建议人工复核（中置信度）"
    else:
        suggestion = "❓ 建议人工复核（低置信度）"
    
    return {
        "type": rule_category,
        "confidence": rule_conf_str,
        "confidence_score": rule_score,
        "law": get_laws_for_category(rule_category),
        "method": "规则引擎匹配",
        "reason": f"命中核心词：{', '.join(matched_core)}（总分{rule_score}分）" if matched_core else f"基于关键词规则匹配（总分{rule_score}分）",
        "suggestion": suggestion,
        "matched_core": matched_core,
        "matched_feature": rule_conf_detail.get("matched_feature", []) if rule_conf_detail else [],
        "is_procuratorial": True,
        "score": rule_score
    }

# ========== 典型案例库 ==========
TYPICAL_CASES = [
    {"title": "周某等82人欠薪案", "similarity": "87%", "category": "民事支持起诉"},
    {"title": "某建筑公司恶意欠薪案", "similarity": "82%", "category": "民事支持起诉"},
    {"title": "某工厂拖欠农民工工资案", "similarity": "78%", "category": "民事支持起诉"},
    {"title": "某企业非法排污案", "similarity": "85%", "category": "公益诉讼"},
    {"title": "某超市食品安全案", "similarity": "80%", "category": "公益诉讼"},
]

def analyze_real(text):
    """真实分析逻辑（双引擎）"""
    if not text:
        return {
            "主要类别": "", "次要类别": "", "置信度": "", 
            "核心定性词": "", "点位": "", "top_case": "", "top_sim": "", 
            "other_cases": [], "has_more": False, "laws": {"default": [], "extended": []},
            "suggestion": "", "is_procuratorial": False, "score": 0
        }
    
    # 1. 规则引擎匹配
    rule_cat = keyword_match(text)
    rule_detail = calculate_confidence(text, rule_cat) if rule_cat else {"confidence": "低", "score": 0, "matched_core": [], "matched_feature": []}
    
    # 调试输出（看实际匹配到了什么）
    print(f"[DEBUG] 类别: {rule_cat}, 分数: {rule_detail.get('score')}, 核心词: {rule_detail.get('matched_core')}")
    
    # 2. 模拟DeepSeek API结果
    api_result = {"type": rule_cat or "普通投诉", "confidence": 0.8 if rule_cat else 0.1}
    
    # 3. 双引擎融合
    fusion = fusion_result(api_result, rule_cat, rule_detail)
    
    # 4. 点位提取（仅涉检线索）
    if fusion.get("is_procuratorial"):
        location = extract_location(text)
        location_display = location if location else "⚠️ 未识别到具体点位"
        
        # 相似案例（仅涉检）
        matched_cases = [c for c in TYPICAL_CASES if c["category"] == fusion["type"]]
        if not matched_cases:
            matched_cases = TYPICAL_CASES
    else:
        location_display = "—"
        matched_cases = []
    
    top_case = matched_cases[0] if matched_cases else {"title": "—", "similarity": "—"}
    other_cases = matched_cases[1:] if len(matched_cases) > 1 else []
    
    # 核心定性词
    core_words_str = ", ".join(fusion.get("matched_core", [])) if fusion.get("matched_core") else "无"
    
    # 置信度显示（带分数）
    conf_display = f"{fusion['confidence']}（{fusion['score']}分）" if fusion.get('score') else fusion['confidence']
    
    return {
        "主要类别": fusion["type"],
        "次要类别": "",
        "置信度": conf_display,
        "核心定性词": core_words_str,
        "点位": location_display,
        "top_case": top_case["title"],
        "top_sim": top_case["similarity"],
        "other_cases": other_cases,
        "has_more": len(other_cases) > 0,
        "laws": fusion["law"],
        "method": fusion["method"],
        "suggestion": fusion["suggestion"],
        "is_procuratorial": fusion.get("is_procuratorial", False),
        "score": fusion.get("score", 0)
    }

def create_single_query_tab():
    with gr.Tab("单条查询"):
        gr.Markdown("## 🔍 单条工单智能筛查")
        
        with gr.Row():
            # 左侧输入区
            with gr.Column(scale=2):
                gr.Markdown("### 📝 工单内容")
                input_text = gr.TextArea(
                    label="",
                    placeholder="请输入12345工单内容...",
                    lines=6
                )
                analyze_btn = gr.Button("开始分析", variant="primary")
                
                with gr.Row():
                    test_btn = gr.Button("🧪 测试（讨薪）", size="sm")
                    test2_btn = gr.Button("🧪 测试（环保）", size="sm")
                    noise_btn = gr.Button("🔇 非涉检", size="sm")
            
            # 右侧结果区
            with gr.Column(scale=3):
                gr.Markdown("### 📋 识别结果")
                
                with gr.Row():
                    main_cat = gr.Textbox(label="预期主要类别", interactive=False)
                    sub_cat = gr.Textbox(label="预期次要类别", interactive=False)
                
                confidence = gr.Textbox(label="置信度等级", interactive=False)
                core_words_box = gr.Textbox(label="命中核心定性词", interactive=False)
                
                # 法条区
                gr.Markdown("### ⚖️ 关联法条")
                laws_display = gr.HTML(value="")
                
                with gr.Accordion("📚 查看更多法条", open=False, visible=True):
                    extended_laws_display = gr.HTML(value="")
                
                # 点位信息
                gr.Markdown("### 📍 点位信息")
                location = gr.Textbox(label="涉检点位", interactive=False)
                
                # 相似案例
                gr.Markdown("### 🔍 相似案例提示")
                with gr.Row():
                    top_case_title = gr.Textbox(label="最佳匹配案例", interactive=False)
                    top_case_sim = gr.Textbox(label="相似度", interactive=False)
                
                with gr.Accordion("📂 查看更多相似案例", open=False, visible=True):
                    other_cases_display = gr.HTML(value="")
        
        # 绑定分析按钮
        def on_analyze(text):
            result = analyze_real(text)
            
            # 法条显示
            laws = result["laws"]
            if result.get("is_procuratorial") and laws.get("default"):
                default_html = '<div style="font-size:14px; line-height:1.6;">'
                for law in laws["default"][:3]:
                    default_html += f'• <b>{law.get("编号", "")}</b>：{law.get("内容", "")}<br>'
                default_html += '</div>'
                
                extended_html = '<div style="font-size:13px; line-height:1.5;">'
                if laws.get("extended"):
                    for law in laws["extended"]:
                        extended_html += f'• <b>{law.get("编号", "")}</b>：{law.get("内容", "")}<br>'
                else:
                    extended_html += '<span style="color:gray;">无更多法条</span>'
                extended_html += '</div>'
            else:
                default_html = '<span style="color:#999;">非涉检线索，无需关联法条</span>'
                extended_html = '<span style="color:#999;">—</span>'
            
            # 案例显示
            other_html = '<div style="font-size:13px;">'
            if result["other_cases"]:
                for case in result["other_cases"]:
                    other_html += f'• {case["title"]}（{case["similarity"]}）<br>'
            else:
                other_html += '<span style="color:gray;">无更多相似案例</span>'
            other_html += '</div>'
            
            return [
                result["主要类别"],
                result["次要类别"],
                result["置信度"],
                result["核心定性词"],
                default_html,
                extended_html,
                result["点位"],
                result["top_case"],
                result["top_sim"],
                other_html
            ]
        
        analyze_btn.click(
            fn=on_analyze,
            inputs=input_text,
            outputs=[
                main_cat, sub_cat, confidence, core_words_box,
                laws_display, extended_laws_display,
                location,
                top_case_title, top_case_sim,
                other_cases_display
            ]
        )
        
        # 测试按钮
        test_btn.click(
            fn=lambda: "我是农民工，老板在房山区长阳镇碧桂园小区拖欠我们工资半年了，一共欠了8万多，实在没办法了",
            outputs=input_text
        )
        test2_btn.click(
            fn=lambda: "河北镇檀木港村村委会附近有个工厂天天排黑烟，污染环境，河水都变黑了",
            outputs=input_text
        )
        noise_btn.click(
            fn=lambda: "楼上邻居天天半夜12点还在唱歌，音响声音特别大，影响我们休息",
            outputs=input_text
        )

if __name__ == "__main__":
    css = """
    .gradio-textbox > label { font-size: 13px !important; font-weight: 600 !important; color: #555 !important; }
    .gradio-textbox input { font-size: 13px !important; }
    h3 { margin-top: 0 !important; margin-bottom: 8px !important; font-size: 16px !important; }
    .accordion { border: 1px solid #e0e0e0 !important; border-radius: 6px !important; margin-top: 8px !important; }
    """
    
    with gr.Blocks(title="智检民声-单条查询") as demo:
        create_single_query_tab()
    
    demo.launch(
        server_name="0.0.0.0", 
        server_port=6009, 
        css=css
    )