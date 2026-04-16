import gradio as gr
import json
import os

# ========== 加载规则引擎 ==========
try:
    from rule_engine_keywords import KEYWORDS_DB, calculate_confidence, keyword_match
    from rule_engine import fusion_result, get_laws_for_category
    RULE_ENGINE_READY = True
except ImportError:
    print("⚠️ 规则引擎未生成，使用模拟模式")
    RULE_ENGINE_READY = False
    # 模拟函数
    def keyword_match(text): return "民事支持起诉" if "薪" in text else None
    def calculate_confidence(text, cat): return {"score": 5, "confidence": "中", "matched_core": ["欠薪"], "matched_feature": []}
    def fusion_result(api, cat, detail): return {"type": cat or "普通投诉", "confidence": detail.get("confidence", "低"), "law": {"default": [], "extended": []}}
    def get_laws_for_category(cat): return {"default": [], "extended": []}

# ========== 模拟典型案例库（等D交付后替换） ==========
TYPICAL_CASES = [
    {"title": "周某等82人欠薪案", "similarity": "87%", "category": "民事支持起诉"},
    {"title": "某建筑公司恶意欠薪案", "similarity": "82%", "category": "民事支持起诉"},
    {"title": "某工厂拖欠农民工工资案", "similarity": "78%", "category": "民事支持起诉"},
]

def analyze_real(text):
    """真实分析逻辑（双引擎）"""
    if not text:
        return {
            "主要类别": "", "次要类别": "", "置信度": "", 
            "点位": "", "top_case": "", "top_sim": "", 
            "other_cases": [], "has_more": False,
            "laws": {"default": [], "extended": []}
        }
    
    # 1. 规则引擎匹配
    rule_cat = keyword_match(text)
    rule_detail = calculate_confidence(text, rule_cat) if rule_cat else {"confidence": "低", "score": 0}
    
    # 2. 模拟DeepSeek API结果（后续接入真实API）
    api_result = {"type": rule_cat or "普通投诉", "confidence": 0.8 if rule_cat else 0.1}
    
    # 3. 双引擎融合
    fusion = fusion_result(api_result, rule_cat, rule_detail)
    
    # 4. 提取点位（简单正则，后续优化）
    import re
    location_match = re.search(r'([^\s]{2,10}(?:镇|街道|路|号|工地|小区))', text)
    location = location_match.group(1) if location_match else "⚠️点位缺失"
    
    # 5. 匹配相似案例
    matched_cases = [c for c in TYPICAL_CASES if c["category"] == fusion["type"]]
    if not matched_cases:
        matched_cases = TYPICAL_CASES  # 默认展示
    
    top_case = matched_cases[0] if matched_cases else {"title": "暂无匹配", "similarity": "-"}
    other_cases = matched_cases[1:] if len(matched_cases) > 1 else []
    
    # 6. 法条（从rule_engine加载）
    laws = fusion.get("law", {"default": [], "extended": []})
    
    return {
        "主要类别": fusion["type"],
        "次要类别": "",  # 暂时留空
        "置信度": fusion["confidence"],  # 高/中/低
        "点位": location,
        "top_case": top_case["title"],
        "top_sim": top_case["similarity"],
        "other_cases": other_cases,
        "has_more": len(other_cases) > 0,
        "laws": laws
    }

def create_single_query_tab():
    with gr.Tab("单条查询"):
        gr.Markdown("## 🔍 单条工单智能筛查")
        
        with gr.Row():
            # 左侧：工单输入
            with gr.Column(scale=2):
                gr.Markdown("### 📝 工单内容")
                input_text = gr.TextArea(
                    label="",
                    placeholder="请输入12345工单内容...",
                    lines=5
                )
                analyze_btn = gr.Button("开始分析", variant="primary")
            
            # 右侧：识别结果
            with gr.Column(scale=3):
                gr.Markdown("### 📋 识别结果")
                
                with gr.Row():
                    main_cat = gr.Textbox(label="预期主要类别", interactive=False)
                    sub_cat = gr.Textbox(label="预期次要类别", interactive=False)
                
                confidence = gr.Textbox(label="置信度等级", interactive=False)
                
                # 法条区（动态渲染）
                def render_laws(laws_data):
                    default_laws = laws_data.get("default", [])
                    if not default_laws:
                        return "暂无关联法条"
                    
                    html = '<div style="font-size:15px; line-height:1.8;">'
                    for law in default_laws[:3]:
                        html += f'• {law.get("编号", "")} {law.get("内容", "")[:20]}...<br>'
                    html += '</div>'
                    return html
                
                gr.Markdown("### ⚖️ 关联法条")
                laws_display = gr.HTML(value="")
                
                # 折叠更多法条
                with gr.Accordion("📚 查看更多法条", open=False, visible=False) as more_laws_acc:
                    extended_laws_display = gr.HTML(value="")
                
                gr.Markdown("<br>")
                
                # 点位信息
                gr.Markdown("### 📍 点位信息")
                location = gr.Textbox(label="涉检点位", interactive=False)
                
                gr.Markdown("<br>")
                
                # 相似案例（最佳匹配+折叠）
                gr.Markdown("### 🔍 相似案例提示")
                with gr.Row():
                    top_case_title = gr.Textbox(label="最佳匹配案例", interactive=False)
                    top_case_sim = gr.Textbox(label="相似度", interactive=False)
                
                with gr.Accordion("📂 查看更多相似案例", open=False, visible=False) as more_cases_acc:
                    other_cases_display = gr.HTML(value="")
        
        # 绑定分析按钮
        def on_analyze(text):
            result = analyze_real(text)
            
            # 准备法条显示
            laws = result["laws"]
            default_html = '<div style="font-size:15px; line-height:1.8;">'
            for law in laws.get("default", []):
                default_html += f'• <b>{law.get("编号", "")}</b>：{law.get("内容", "")}<br>'
            default_html += '</div>'
            
            extended_html = '<div style="font-size:14px; line-height:1.6;">'
            for law in laws.get("extended", []):
                extended_html += f'• <b>{law.get("编号", "")}</b>：{law.get("内容", "")}<br>'
            extended_html += '</div>'
            
            # 准备案例显示
            other_html = '<div style="font-size:14px; line-height:1.6;">'
            for case in result["other_cases"]:
                other_html += f'• {case["title"]}（相似度：{case["similarity"]}）<br>'
            other_html += '</div>'
            
            # 控制折叠栏可见性
            has_more_laws = len(laws.get("extended", [])) > 0
            has_more_cases = result["has_more"]
            
            return [
                result["主要类别"],
                result["次要类别"],
                result["置信度"],
                default_html,
                gr.update(visible=has_more_laws, value=extended_html),
                result["点位"],
                result["top_case"],
                result["top_sim"],
                gr.update(visible=has_more_cases, value=other_html)
            ]
        
        analyze_btn.click(
            fn=on_analyze,
            inputs=input_text,
            outputs=[
                main_cat, sub_cat, confidence,
                laws_display, extended_laws_display,
                location,
                top_case_title, top_case_sim,
                other_cases_display
            ]
        )

if __name__ == "__main__":
    css = """
    .gradio-textbox > label { font-size: 14px !important; font-weight: 600 !important; color: #555 !important; }
    .gradio-textbox input { font-size: 14px !important; }
    h3 { margin-top: 0 !important; margin-bottom: 8px !important; font-size: 17px !important; }
    .accordion { border: 1px solid #e0e0e0 !important; border-radius: 6px !important; margin-top: 8px !important; }
    """
    
    with gr.Blocks(title="智检民声-单条查询", css=css) as demo:
        create_single_query_tab()
    demo.launch(server_name="0.0.0.0", server_port=6009, share=True)