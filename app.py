import gradio as gr
import pandas as pd
import json

# Mock数据（假数据，用于今晚截图展示）
def mock_classify(text):
    """临时Mock函数，模拟API返回"""
    if not text:
        return {
            "type": "无法识别",
            "confidence": 0,
            "law": "无",
            "reason": "文本为空",
            "suggestion": "请输入投诉内容"
        }
    
    # 简单关键词匹配做演示
    text = str(text).lower()
    if any(kw in text for kw in ["污染", "环境", "废水", "生态"]):
        return {
            "type": "公益诉讼",
            "confidence": 0.85,
            "law": "环境保护法第58条",
            "reason": "涉及环境污染线索",
            "suggestion": "建议移送公益诉讼部门"
        }
    elif any(kw in text for kw in ["欠薪", "工资", "拖欠", "克扣"]):
        return {
            "type": "民事支持起诉",
            "confidence": 0.82,
            "law": "劳动合同法第30条",
            "reason": "涉及劳动者权益保护",
            "suggestion": "建议支持起诉"
        }
    elif any(kw in text for kw in ["诈骗", "盗窃", "伤害"]):
        return {
            "type": "刑事犯罪",
            "confidence": 0.88,
            "law": "刑法相关条款",
            "reason": "涉嫌刑事犯罪",
            "suggestion": "建议移送刑事检察部门"
        }
    else:
        return {
            "type": "普通投诉",
            "confidence": 0.3,
            "law": "不涉及检察监督",
            "reason": "暂未发现涉检线索",
            "suggestion": "建议按普通信访处理"
        }

def batch_process(file):
    """批量处理Excel（Mock版）"""
    if file is None:
        return pd.DataFrame({"提示": ["请先上传Excel文件"]})
    
    try:
        df = pd.read_excel(file.name)
        results = []
        
        # 只处理前5行用于预览
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            content = str(row.get("投诉内容", row.get("content", "")))
            mock_res = mock_classify(content)
            
            results.append({
                "序号": i+1,
                "投诉内容": content[:50] + "..." if len(content) > 50 else content,
                "线索类型": mock_res["type"],
                "风险等级": "高" if mock_res["confidence"] > 0.8 else "中" if mock_res["confidence"] > 0.5 else "低",
                "置信度": f"{mock_res['confidence']:.0%}",
                "法律依据": mock_res["law"]
            })
        
        return pd.DataFrame(results)
    except Exception as e:
        return pd.DataFrame({"错误": [f"文件解析失败: {str(e)}"]})

def single_query(text):
    """单条查询（Mock版）"""
    if not text or text.strip() == "":
        return "⚠️ **请输入投诉内容**"
    
    result = mock_classify(text)
    
    return f"""
### 📋 分析结果

| 项目 | 内容 |
|:---|:---|
| **线索类型** | {result['type']} |
| **置信度** | {result['confidence']:.0%} |
| **风险等级** | {"🔴 高" if result['confidence'] > 0.8 else "🟡 中" if result['confidence'] > 0.5 else "🟢 低"} |
| **法律依据** | {result['law']} |
| **分析理由** | {result['reason']} |
| **处置建议** | {result['suggestion']} |
"""

# Gradio界面
with gr.Blocks(title="智检民声 - 12345涉检线索筛查", css="""
    .gradio-container {background-color: #f5f5f5;}
    h1 {color: #2c3e50; text-align: center;}
    .tab {font-weight: bold;}
""") as demo:
    
    gr.Markdown("# 智检民声")
    gr.Markdown("### 12345涉检线索智能筛查与溯源系统")
    gr.Markdown("---")
    
    with gr.Tab("📁 批量筛查"):
        gr.Markdown("**上传12345投诉数据Excel文件（需包含'投诉内容'列）**")
        
        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(
                    label="上传Excel", 
                    file_types=[".xlsx", ".xls"],
                    elem_classes="file-upload"
                )
                btn_batch = gr.Button("🚀 开始筛查", variant="primary", size="lg")
            
            with gr.Column(scale=2):
                output_table = gr.DataFrame(
                    label="筛查结果预览（前5条）",
                    interactive=False,
                    wrap=True
                )
        
        btn_batch.click(batch_process, inputs=file_input, outputs=output_table)
        
        gr.Markdown("---")
        gr.Markdown("💡 **提示**：完整结果可导出为Excel，支持下载台账")
    
    with gr.Tab("🔍 单条查询"):
        gr.Markdown("**输入单条投诉文本进行实时分析**")
        
        with gr.Row():
            with gr.Column(scale=1):
                text_input = gr.Textbox(
                    label="投诉内容",
                    placeholder="请粘贴12345投诉原文...",
                    lines=8,
                    max_lines=12
                )
                btn_single = gr.Button("🔎 分析", variant="primary", size="lg")
                btn_clear = gr.Button("🔄 清空")
            
            with gr.Column(scale=1):
                result_card = gr.Markdown(label="分析结果")
        
        btn_single.click(single_query, inputs=text_input, outputs=result_card)
        btn_clear.click(lambda: "", outputs=text_input)
    
    with gr.Tab("📊 统计看板"):
        gr.Markdown("**系统概览（Mock数据）**")
        
        with gr.Row():
            gr.Number(label="今日处理", value=128, interactive=False)
            gr.Number(label="涉检线索", value=23, interactive=False)
            gr.Number(label="公益诉讼", value=8, interactive=False)
            gr.Number(label="刑事犯罪", value=5, interactive=False)
        
        gr.BarPlot(
            value={"labels": ["公益诉讼", "民事支持起诉", "刑事犯罪", "行政执法监督", "普通投诉"], 
                   "values": [8, 5, 5, 5, 105]},
            label="线索类型分布",
            interactive=False
        )

if __name__ == "__main__":
    # 启动Gradio，端口6006，允许外部访问
    demo.launch(
        server_name="0.0.0.0",
        server_port=6006,
        share=False,
        show_error=True
    )