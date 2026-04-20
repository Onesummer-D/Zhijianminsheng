#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智检民声 - 12345涉检线索智能筛查系统
主入口：app.py
架构：DeepSeek风格首页 → 单条查询(完整原版) / 批量筛查
"""

import gradio as gr
import sys
import os
import pandas as pd
from datetime import datetime

sys.path.insert(0, '/root/zhijianminsheng')

# ==================== 从 single_query_v2 导入完整分析能力 ====================
from single_query_v2 import (
    analyze_real,
    get_laws_for_category,
    get_similar_cases,
    LEGAL_BASIS,
    MATCHER
)
print("✅ 已导入 single_query_v2 完整分析模块")

# ==================== 合并CSS：首页 + 单条查询原版 + 批量 ====================
CUSTOM_CSS = """
/* ========== 首页 ========== */
.home-wrap {
    background: linear-gradient(180deg, #d4e9f7 0%, #eef6fc 40%, #ffffff 100%);
    min-height: 90vh;
    padding-top: 180px;
}
.home-title { text-align: center; margin-bottom: 64px; }
.home-title h1 { font-size: 52px; color: #1a1a1a; margin: 0; letter-spacing: -2px; }
.home-title p { font-size: 20px; color: #5f6368; margin-top: 12px; }
.home-cards {
    display: flex;
    justify-content: center;
    gap: 32px;
    max-width: 900px;
    margin: 0 auto;
}
.home-card {
    background: #ffffff;
    border: 1px solid #dadce0;
    border-radius: 16px;
    padding: 40px 36px;
    width: 420px;
    cursor: pointer;
    transition: all 0.3s ease;
}
.home-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    border-color: #999;
    transform: translateY(-3px);
}
.home-card h2 { font-size: 24px; color: #1a1a1a; margin: 0 0 12px 0; }
.home-card-desc {
    font-size: 15px;
    color: #5f6368;
    line-height: 1.7;
    margin-bottom: 24px;
    min-height: 48px;
}

/* ========== 导航按钮 ========== */
.nav-back button {
    font-size: 16px !important;
    padding: 10px 20px !important;
    min-width: 120px !important;
}

/* ========== 单条查询：原版CSS ========== */
.output-box { 
    border: 1px solid #e0e0e0; 
    border-radius: 4px; 
    padding: 10px; 
    background: white;
}
.main-title {
    margin-bottom: 12px !important;
    margin-top: 8px !important;
}
h3 {
    font-size: 20px !important;  
    font-weight: 600 !important;
    margin-bottom: 12px !important;
}
.law-container {
    margin-top: -4px !important;
    padding-top: 0px !important;
}
.law-item {
    margin-bottom: 12px;
    line-height: 1.6;
    margin-top: 0px !important;
}
.law-item:first-child {
    margin-top: 0px !important;
    padding-top: 0px !important;
}
.law-title {
    font-weight: bold;
    font-size: 15px;
    margin-bottom: 4px;
    margin-top: 0px !important;
}
.law-content {
    font-size: 15px;
    color: #333;
    margin-left: 0;
}

/* ========== 批量筛查 ========== */
.batch-hint { color: #666; font-size: 13px; margin-top: 8px; }
.nav-back { margin-bottom: 8px !important; max-width: 140px !important; }
.nav-back button { font-size: 16px !important; padding: 6px 14px !important; }
"""

# ==================== 测试用例 ====================
TEST_CASES = {
    "💰 讨薪案例": "我是农民工，老板在房山区长阳镇碧桂园小区拖欠我们工资半年了，一共欠了8万多，实在没办法了",
    "🏭 环保案例": "河北镇檀木港村村委会附近有个工厂天天排黑烟，污染环境，河水都变黑了，多次反映没人管",
    "🚫 传销案例": "有人在小区搞传销，天天拉人头开会洗脑，还我血汗钱",
    "⚖️ 小过重罚": "市场监管局说我货架摆放不合格，张口就罚五万，小本生意罚不起",
    "💭 假设语境": "如果盗窃罪判几年？假设我偷了东西会怎么处理？做梦梦见被罚款",
    "❌ 非涉检": "邻里纠纷，邻居装修太吵，影响休息，物业不管"
}

# ==================== 5. 单条查询 UI（完全复制 single_query_v2.py 原版） ====================
def build_single_query():
    # --- 内嵌完整的 on_analyze 和 clear（直接复制原版） ---
    def on_analyze(text):
        result = analyze_real(text)
        cat = result["主要类别"]

        # 多类别法条查询 - 按主要:次要 = 2:1 比例分配
        all_categories = result.get("all_categories", [])
        if not all_categories and cat and "非涉检" not in cat:
            all_categories = [cat]
        
        combined_laws = {"default": [], "extended": []}
        seen_ids = set()
        
        if all_categories:
            primary_cat = all_categories[0]
            secondary_cats = [c for c in all_categories[1:] if c and "非涉检" not in c][:2]
            
            sec_slots = min(len(secondary_cats) * 2, 2)
            pri_slots = 6 - sec_slots
            
            p_laws = get_laws_for_category(primary_cat)
            for item in p_laws.get("default", [])[:pri_slots]:
                item_id = item.get('编号', item.get('title', str(item)))
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    combined_laws["default"].append(item)
            for item in p_laws.get("extended", [])[:2]:
                item_id = item.get('编号', item.get('title', str(item)))
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    combined_laws["extended"].append(item)
            
            if secondary_cats and sec_slots > 0:
                per_sec = max(1, sec_slots // len(secondary_cats))
                for sec_cat in secondary_cats:
                    s_laws = get_laws_for_category(sec_cat)
                    for item in s_laws.get("default", [])[:per_sec]:
                        item_id = item.get('编号', item.get('title', str(item)))
                        if item_id not in seen_ids:
                            seen_ids.add(item_id)
                            combined_laws["default"].append(item)
                    for item in s_laws.get("extended", [])[:1]:
                        item_id = item.get('编号', item.get('title', str(item)))
                        if item_id not in seen_ids:
                            seen_ids.add(item_id)
                            combined_laws["extended"].append(item)
        
        # 法条显示
        if "非涉检" not in cat and "失败" not in cat and "—" not in cat and all_categories:
            law_html = '<div class="law-container" style="margin-top:-12px;padding-top:0px;">'
            if combined_laws.get("default"):
                for i, l in enumerate(combined_laws["default"][:3], 1):
                    content = l.get('内容', '')
                    number = l.get('编号', '')
                    law_html += f'<div class="law-item" style="margin-top:0px;margin-bottom:12px;"><div class="law-title" style="margin-top:0px;">{i}. {number}</div><div class="law-content">{content}</div></div>'
            law_html += "</div>"
            
            ext_html = '<div class="law-container" style="margin-top:0px;padding-top:0px;">'
            if combined_laws.get("extended"):
                for l in combined_laws["extended"][:3]:
                    content = l.get('内容', '')
                    number = l.get('编号', '')
                    ext_html += f'<div class="law-item" style="margin-top:0px;margin-bottom:10px;"><div class="law-title" style="margin-top:0px;font-size:14px;">{number}</div><div class="law-content" style="font-size:14px;">{content}</div></div>'
            ext_html += "</div>"
        else:
            law_html = '<span style="color:#999; font-size:15px;">非涉检线索，无需关联法条</span>'
            ext_html = '<span style="color:#999; font-size:15px;">—</span>'
        
        # 相似案例
        best = result.get("相似案例")
        if best:
            case_name = best.get("title", best.get("案例标题", "—"))
            raw_sim = best.get('similarity', best.get('匹配度', 0))
            sim_score = f"{raw_sim}%" if isinstance(raw_sim, (int, float)) else "85%"
        else:
            case_name = "—"
            sim_score = "—"
        
        others = result.get("相似案例列表", [])
        if others:
            cases_html = """
            <table style='width:100%;font-size:14px;border-collapse:collapse;'>
                <thead>
                    <tr style='border-bottom:1px solid #999;'>
                        <th style='text-align:left;padding:8px 4px;font-weight:600;color:#333;'>案例</th>
                        <th style='text-align:center;padding:8px 4px;font-weight:600;color:#333;width:80px;'>匹配度</th>
                    </tr>
                </thead>
                <tbody>
            """
            for c in others:
                title = c.get('title', c.get('案例标题', '未知'))
                sim_val = c.get('similarity', 0)
                sim_str = f"{sim_val}%" if isinstance(sim_val, (int, float)) else "80%"
                
                if isinstance(sim_val, (int, float)):
                    if sim_val >= 90:
                        color = "#2e7d32"
                    elif sim_val >= 80:
                        color = "#1565c0"
                    else:
                        color = "#757575"
                else:
                    color = "#757575"
                
                cases_html += f"""
                    <tr style='border-bottom:1px solid #eee;transition:background 0.2s;' onmouseover="this.style.background='#fafafa'" onmouseout="this.style.background='white'">
                        <td style='padding:8px 4px;color:#333;'>{title}</td>
                        <td style='padding:8px 4px;text-align:center;font-weight:600;color:{color};'>{sim_str}</td>
                    </tr>
                """
            cases_html += "</tbody></table>"
        else:
            cases_html = "<span style='color:#999; font-size:14px;'>暂无其他相似案例</span>"
        
        return [
            result["主要类别"], 
            result["次要类别"], 
            result["置信度等级"],
            result["建议操作"], 
            result["核心定性词"], 
            result["点位"],
            law_html, 
            ext_html,
            case_name, 
            sim_score, 
            cases_html, 
            result["双引擎详情"]
        ]
    
    def clear():
        return [
            "—", "—", "—", "—", "—", "—",
            '<span style="color:#999; font-size:15px;">等待分析...</span>',
            '<span style="color:#999; font-size:15px;">—</span>',
            "—", "—", 
            "<span style='color:#999; font-size:14px;'>等待分析...</span>",
            "等待分析..."
        ]

    # --- UI组件（完全复制原版布局） ---
    with gr.Column():
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📝 工单内容")
                input_text = gr.TextArea(
                    label="",
                    placeholder="请输入12345工单内容（如：我是农民工，老板拖欠工资半年...）", 
                    lines=6, 
                    show_label=False
                )
                
                with gr.Row():
                    analyze_btn = gr.Button("🔍 开始分析", variant="primary", scale=2)
                    clear_btn = gr.Button("🔄 清空", scale=1)
                
                gr.Markdown("### 🧪 快速测试")
                with gr.Row():
                    t1 = gr.Button("💰 讨薪案例", size="sm")
                    t2 = gr.Button("🏭 环保案例", size="sm")
                    t3 = gr.Button("🚫 传销案例", size="sm")
                    t4 = gr.Button("⚖️ 小过重罚", size="sm")
                
                with gr.Row():
                    t5 = gr.Button("💭 假设语境", size="sm")
                    t6 = gr.Button("🔇 非涉检", size="sm")
            
            with gr.Column(scale=2):
                gr.Markdown("### 📋 识别结果")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        main_cat = gr.Textbox(
                            label="预期主要类别", 
                            interactive=False,
                            elem_classes=["output-box"]
                        )
                    with gr.Column(scale=1):
                        second_cat = gr.Textbox(
                            label="预期次要类别", 
                            interactive=False, 
                            value="—",
                            elem_classes=["output-box"]
                        )
                
                with gr.Row():
                    with gr.Column(scale=1):
                        conf_level = gr.Textbox(
                            label="置信度等级", 
                            interactive=False,
                            elem_classes=["output-box"]
                        )
                    with gr.Column(scale=1):
                        suggestion = gr.Textbox(
                            label="处理建议", 
                            interactive=False,
                            elem_classes=["output-box"]
                        )
                
                keywords = gr.Textbox(
                    label="🎯 命中核心定性词", 
                    interactive=False, 
                    lines=2,
                    elem_classes=["output-box"]
                )
                
                gr.Markdown("### 📍 点位信息")
                location = gr.Textbox(
                    label="涉检点位/地理位置", 
                    interactive=False, 
                    value="—",
                    elem_classes=["output-box"]
                )
                
                gr.Markdown("### ⚖️ 关联法条")
                laws = gr.HTML(label="", show_label=False, elem_classes=["law-container"])
                
                with gr.Accordion("📚 查看更多法条", open=False):
                    ext_laws = gr.HTML(label="", show_label=False)
                
                gr.Markdown("### 🔍 相似案例提示")
                with gr.Row():
                    with gr.Column(scale=3):
                        similar_case = gr.Textbox(
                            label="最佳匹配案例", 
                            interactive=False, 
                            value="—",
                            elem_classes=["output-box"]
                        )
                    with gr.Column(scale=1):
                        similarity_score = gr.Textbox(
                            label="匹配度", 
                            interactive=False, 
                            value="—",
                            elem_classes=["output-box"]
                        )
                
                with gr.Accordion("📂 查看更多相似案例（Top 3）", open=False):
                    similar_cases_list = gr.HTML(label="", show_label=False)
                
                with gr.Accordion("🔧 双引擎判定详情（技术调试）", open=False):
                    detail = gr.Textbox(
                        label="", 
                        interactive=False, 
                        lines=8, 
                        show_label=False,
                        elem_classes=["output-box"]
                    )
        
        outputs = [
            main_cat, second_cat, conf_level, suggestion, keywords, location,
            laws, ext_laws,
            similar_case, similarity_score, similar_cases_list,
            detail
        ]
        
        analyze_btn.click(fn=on_analyze, inputs=input_text, outputs=outputs)
        clear_btn.click(fn=clear, inputs=None, outputs=outputs)
        
        test_cases = {
            t1: "我是农民工，老板在房山区长阳镇碧桂园小区拖欠我们工资半年了，一共欠了8万多，实在没办法了",
            t2: "河北镇檀木港村村委会附近有个工厂天天排黑烟，污染环境，河水都变黑了，多次反映没人管",
            t3: "有人在小区搞传销，天天拉人头开会洗脑，还我血汗钱",
            t4: "市场监管局说我货架摆放不合格，张口就罚五万，小本生意罚不起",
            t5: "如果盗窃罪判几年？假设我偷了东西会怎么处理？做梦梦见被罚款",
            t6: "邻里纠纷，邻居装修太吵，影响休息，物业不管"
        }
        
        for btn, txt in test_cases.items():
            btn.click(fn=lambda x=txt: x, outputs=input_text)
            btn.click(fn=on_analyze, inputs=input_text, outputs=outputs)


# ==================== 6. 批量筛查 UI ====================
def build_batch_screening():
    with gr.Column():
        gr.Markdown('<div style="text-align:center; font-size:24px; font-weight:bold; margin-bottom:12px;">📊 智检民声 - 批量线索筛查</div>')
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📁 上传工单Excel")
                up_file = gr.File(label="选择文件", file_types=[".xlsx", ".xls"])
                btn_start = gr.Button("🚀 开始批量分析", variant="primary")
                gr.Markdown("""
                <div class="batch-hint">
                支持格式：.xlsx / .xls<br>
                智能识别列：工单内容 / 主要内容 / 诉求内容 / 问题描述<br>
                建议：单次 ≤ 200 条，避免API超时
                </div>
                """)

            with gr.Column(scale=2):
                gr.Markdown("### ⏳ 分析状态")
                status_txt = gr.Textbox(label="状态", value="等待上传...", interactive=False)
                prog = gr.Slider(label="进度", minimum=0, maximum=100, value=0, interactive=False)

        gr.Markdown("### 📋 筛查结果预览（前50条）")
        out_table = gr.Dataframe(
            headers=["序号", "工单内容", "主要类别", "次要类别", "置信度", "点位", "建议"],
            wrap=True
        )

        with gr.Row():
            btn_export = gr.Button("💾 导出完整结果Excel", variant="secondary")
            out_download = gr.File(label="下载文件", interactive=False)

    def run_batch(fileobj):
        if fileobj is None:
            return pd.DataFrame(), "请先上传Excel文件", 0, None
        try:
            df = pd.read_excel(fileobj.name if hasattr(fileobj, "name") else fileobj)
            content_col = None
            candidates = ["工单内容", "主要内容", "诉求内容", "内容", "问题描述", "text", "content"]
            for c in candidates:
                if c in df.columns:
                    content_col = c
                    break
            if content_col is None:
                content_col = df.columns[0]

            total = len(df)
            display_rows = []
            full_rows = []

            for idx, row in df.iterrows():
                text = str(row[content_col]) if pd.notna(row[content_col]) else ""
                r = analyze_real(text)
                
                display_rows.append({
                    "序号": idx + 1,
                    "工单内容": text[:80] + "..." if len(text) > 80 else text,
                    "主要类别": r.get("主要类别", "—"),
                    "次要类别": r.get("次要类别", "—"),
                    "置信度": r.get("置信度等级", "—"),
                    "点位": r.get("点位", "—"),
                    "建议": r.get("建议操作", "—"),
                })
                
                full_row = dict(row)
                full_row["AI主要类别"] = r.get("主要类别", "—")
                full_row["AI次要类别"] = r.get("次要类别", "—")
                full_row["AI置信度"] = r.get("置信度等级", "—")
                full_row["AI点位"] = r.get("点位", "—")
                full_row["AI建议"] = r.get("建议操作", "—")
                full_row["AI关键词"] = r.get("核心定性词", "—")
                full_rows.append(full_row)

            ts = datetime.now().strftime("%m%d_%H%M%S")
            out_path = f"/tmp/batch_result_{ts}.xlsx"
            pd.DataFrame(full_rows).to_excel(out_path, index=False)
            return pd.DataFrame(display_rows), f"✅ 完成！共分析 {total} 条线索", 100, out_path
        except Exception as e:
            return pd.DataFrame(), f"❌ 错误: {str(e)}", 0, None

    btn_start.click(run_batch, inputs=up_file, outputs=[out_table, status_txt, prog, out_download])

    def reuse_download(fileobj):
        if fileobj and isinstance(fileobj, str) and os.path.exists(fileobj):
            return fileobj
        return None

    btn_export.click(reuse_download, inputs=out_download, outputs=out_download)


# ==================== 7. 主程序 ====================
with gr.Blocks(css=CUSTOM_CSS, title="智检民声 - 12345涉检线索智能筛查系统") as demo:

    # --- 首页 ---
    with gr.Column(visible=True, elem_classes="home-wrap") as page_home:
        gr.Markdown("""
        <div class="home-title">
            <h1>智检民声</h1>
            <p>12345涉检线索智能筛查系统</p>
        </div>
        """)
        with gr.Row(elem_classes="home-cards"):
            with gr.Column(elem_classes="home-card"):
                gr.Markdown("""
                <h2>📊 批量筛查</h2>
                <div class="home-card-desc">
                上传Excel工单表格，系统自动批量识别涉检线索、分类标注、提取点位，一键导出筛查报告。
                </div>
                """)
                btn_to_batch = gr.Button("进入批量筛查 →", variant="primary")
            with gr.Column(elem_classes="home-card"):
                gr.Markdown("""
                <h2>🔍 单条查询</h2>
                <div class="home-card-desc">
                输入单条12345工单内容，实时分析线索类别、置信度等级、关联法条及相似案例匹配。
                </div>
                """)
                btn_to_single = gr.Button("进入单条查询 →", variant="primary")

    # --- 单条查询页（完整原版） ---
    with gr.Column(visible=False) as page_single:
        with gr.Row():
            with gr.Column(scale=1):
                btn_back_1 = gr.Button("← 返回首页", size="sm", elem_classes="nav-back")
            with gr.Column(scale=6):
                gr.Markdown("")
        build_single_query()

    # --- 批量筛查页 ---
    with gr.Column(visible=False) as page_batch:
        with gr.Row():
            with gr.Column(scale=1):
                btn_back_2 = gr.Button("← 返回首页", size="sm", elem_classes="nav-back")
            with gr.Column(scale=6):
                gr.Markdown("")
        build_batch_screening()

    # --- 页面切换 ---
    def switch(page):
        return [gr.update(visible=(p == page)) for p in ["home", "single", "batch"]]

    btn_to_single.click(lambda: switch("single"), None, [page_home, page_single, page_batch])
    btn_to_batch.click( lambda: switch("batch"),  None, [page_home, page_single, page_batch])
    btn_back_1.click(   lambda: switch("home"),   None, [page_home, page_single, page_batch])
    btn_back_2.click(   lambda: switch("home"),   None, [page_home, page_single, page_batch])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=6009, share=False)
