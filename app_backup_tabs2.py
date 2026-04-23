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
from collections import Counter
from case_rag import find_similar_case
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

/* ========== 去掉File组件橘色框 ========== */
.clean-file .file-preview,
.clean-file .file-display {
    background: transparent !important;
    border: 1px solid #e0e0e0 !important;
    box-shadow: none !important;
}
.clean-file {
    border: 1px dashed #ccc !important;
    background: #fafafa !important;
}

/* ========== 隐藏 Tabs 导航栏（多选择器覆盖所有 Gradio 版本） ========== */
.hidden-tabs > .tab-nav,
.hidden-tabs > .tabs-nav,
.hidden-tabs [role="tablist"],
.hidden-tabs .tabmenu,
.hidden-tabs .tab-buttons,
.hidden-tabs > div:first-child:has(>button) {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
}
.hidden-tabs {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
.hidden-tabs .tabitem {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
}"""

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
            sim_score = f
            "{raw_sim}%" if isinstance(raw_sim, (int, float)) else "85%"
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

# ========== 批量筛查辅助函数（修复版） ==========
HISTORY_DIR = "./history"
os.makedirs(HISTORY_DIR, exist_ok=True)

def desensitize_text(text):
    """数据脱敏：展示层调用"""
    import re
    text = re.sub(r'(\d{3})\d{4}(\d{4})', r'\1****\2', text)
    text = re.sub(r'(\d{6})\d{8}(\d{4})', r'\1********\2', text)
    text = re.sub(r'([一-龥]{1})([一-龥]{1,2})(?![一-龥])', lambda m: m.group(1)+'*'*len(m.group(2)), text)
    return text

def analyze_batch_rule_only(text):
    """纯规则引擎分析（批量筛查专用，B无卡可跑）"""
    import sys
    if 'rule_engine_keywords' in sys.modules:
        del sys.modules['rule_engine_keywords']
    import rule_engine_keywords as rule
    
    # 【修复】兼容 classify_single 返回 dict 或 str
    main_cat = None
    try:
        raw = rule.classify_single(text)
        if isinstance(raw, dict):
            main_cat = raw.get("category") or raw.get("cat") or raw.get("class")
        elif isinstance(raw, str):
            main_cat = raw
    except AttributeError:
        pass
    
    # 备用：手动遍历
    if not main_cat:
        scores = {}
        for cat in ['刑事犯罪', '公益诉讼', '民事支持起诉', '行政执法监督']:
            try:
                r = rule.calculate_confidence(text, cat)
                scores[cat] = r.get("score", 0)
            except:
                scores[cat] = 0
        if scores and max(scores.values()) > 0:
            main_cat = max(scores, key=scores.get)
    
    # 【修复】确保是字符串
    if isinstance(main_cat, dict):
        main_cat = str(main_cat)
    
    if not main_cat:
        return {
            "主要类别": "非涉检", "次要类别": "无", "置信度等级": "低",
            "建议操作": "无需检察介入", "核心定性词": "无", "点位": "—",
            "命中核心词": "无", "命中特征词": "无", "相似案例": "—", "关联法条": "—", "得分": 0
        }
    
    conf = rule.calculate_confidence(text, main_cat)
    score = conf.get("score", 0)
    level = conf.get("level", "低")
    core = conf.get("matched_core", [])
    feat = conf.get("matched_feature", [])
    
    # 次要类别
    second_cat = None
    all_scores = {}
    for cat in ['刑事犯罪', '公益诉讼', '民事支持起诉', '行政执法监督']:
        if cat != main_cat:
            try:
                r = rule.calculate_confidence(text, cat)
                all_scores[cat] = r.get("score", 0)
            except:
                all_scores[cat] = 0
    if all_scores:
        best_sec = max(all_scores, key=all_scores.get)
        if all_scores[best_sec] >= 4:
            second_cat = best_sec
    
    # 点位
    try:
        from single_query_v2 import extract_location
        loc = extract_location(text)
    except:
        loc = "—"
    
    # 伪RAG
    sim_case, sim_law = find_similar_case(text, main_cat, second_cat)
    
    if score >= 6:
        suggestion = "🟢 建议优先处理"
        conf_level = f"🟢 高（{score}分）"
    elif score >= 3:
        suggestion = "🟡 建议人工复核"
        conf_level = f"🟡 中（{score}分）"
    else:
        suggestion = "🔴 需人工复核"
        conf_level = f"🔴 低（{score}分）"
    
    return {
        "主要类别": main_cat,
        "次要类别": second_cat or "无",
        "置信度等级": conf_level,
        "建议操作": suggestion,
        "核心定性词": "、".join(core) if core else "无",
        "点位": loc if loc else "⚠️ 点位缺失",
        "命中核心词": "、".join(core) if core else "无",
        "命中特征词": "、".join(feat) if feat else "无",
        "相似案例": sim_case,
        "关联法条": sim_law,
        "得分": score
    }

def load_history(filename):
    cols = ["工单编号", "主要类别", "置信度", "点位"]
    if not filename:
        return pd.DataFrame(columns=cols)
    path = os.path.join(HISTORY_DIR, filename)
    if os.path.exists(path):
        df = pd.read_excel(path)
        for c in cols:
            if c not in df.columns:
                df[c] = "—"
        return df[cols]
    return pd.DataFrame(columns=cols)

def export_df(full_df):
    if full_df is None or len(full_df) == 0:
        return None
    path = f"批量筛查导出_{datetime.now().strftime('%H%M%S')}.xlsx"
    full_df.to_excel(path, index=False)
    return path


# ========== 批量筛查 UI（修复版） ==========
def build_batch_screening():
    with gr.Column():
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("## 📁 批量工单筛查")
            with gr.Column(scale=1):
                gr.Markdown("## 📜 筛查台账")
        
        with gr.Row():
            with gr.Column(scale=3):
                batch_file = gr.File(
                    label="上传Excel（需含'工单内容'或'主要内容'列）", 
                    file_types=[".xlsx"],
                    elem_classes=["clean-file"]
                )
                
                with gr.Row():
                    only_loc_chk = gr.Checkbox(label="🔍 只看含点位工单", value=False)
                    use_api_chk = gr.Checkbox(label="🤖 启用DeepSeek API复核（演示模式）", value=False)
                
                analyze_btn = gr.Button("🚀 开始批量筛查", variant="primary")
                status_txt = gr.Textbox(label="执行状态", interactive=False)
                
                with gr.Row():
                    export_btn = gr.Button("📥 导出当前结果Excel")
                    export_file = gr.File(label="下载导出文件", interactive=False)
            
            with gr.Column(scale=1):
                history_dd = gr.Dropdown(label="选择历史记录", choices=[], interactive=True, value=None)
                with gr.Row():
                    load_hist_btn = gr.Button("加载选中记录", scale=1)
                    refresh_hist_btn = gr.Button("🔄 刷新", scale=1)
                hist_preview = gr.DataFrame(
                    label="历史记录预览",
                    interactive=False,
                    headers=["工单编号", "主要类别", "置信度"],
                    value=[]
                )
        
        gr.Markdown("---")
        gr.Markdown("### 📊 筛查结果列表")
        
        result_table = gr.DataFrame(
            label="结果列表",
            headers=["工单编号", "工单内容", "主要类别", "次要类别", "置信度", "点位标记", "重复次数", "命中核心词", "相似案例", "关联法条"],
            interactive=False,
            value=[]
        )
        
        full_data_state = gr.DataFrame(visible=False)
        
        def run_batch(file_obj, only_with_location, use_api):
            empty_cols = ["工单编号", "工单内容", "主要类别", "次要类别", "置信度", "点位标记", "重复次数", "命中核心词", "相似案例", "关联法条"]
            
            if file_obj is None:
                return pd.DataFrame(columns=empty_cols), "请先上传Excel", None, gr.update(choices=[]), pd.DataFrame()
            
            try:
                df = pd.read_excel(file_obj.name if hasattr(file_obj, 'name') else file_obj)
            except Exception as e:
                return pd.DataFrame(columns=empty_cols), f"读取失败: {e}", None, gr.update(choices=[]), pd.DataFrame()
            
            content_col = None
            for c in ['工单内容', '主要内容', '诉求内容', '问题描述']:
                if c in df.columns:
                    content_col = c
                    break
            if not content_col:
                content_col = df.columns[0]
            
            results = []
            for idx, row in df.iterrows():
                text = str(row.get(content_col, ''))
                if not text or text == 'nan':
                    continue
                
                if use_api:
                    from single_query_v2 import analyze_real
                    r = analyze_real(text)
                    res = {
                        "工单编号": row.get('工单编号', f'NO.{idx+1:03d}'),
                        "工单内容": desensitize_text(text[:60] + "..." if len(text) > 60 else text),
                        "主要类别": r.get("主要类别", "非涉检"),
                        "次要类别": r.get("次要类别", "无"),
                        "置信度": r.get("置信度等级", "—"),
                        "得分": 0,
                        "点位": r.get("点位", "—"),
                        "命中核心词": r.get("核心定性词", "无"),
                        "命中特征词": "无",
                        "是否涉检": "否" if "非涉检" in r.get("主要类别", "") else "是",
                        "相似案例": r.get("相似案例", {}).get("title", "—") if isinstance(r.get("相似案例"), dict) else "—",
                        "关联法条": "—"
                    }
                else:
                    r = analyze_batch_rule_only(text)
                    res = {
                        "工单编号": row.get('工单编号', f'NO.{idx+1:03d}'),
                        "工单内容": desensitize_text(text[:60] + "..." if len(text) > 60 else text),
                        "主要类别": r["主要类别"],
                        "次要类别": r["次要类别"],
                        "置信度": r["置信度等级"],
                        "得分": r["得分"],
                        "点位": r["点位"],
                        "命中核心词": r["命中核心词"],
                        "命中特征词": r["命中特征词"],
                        "是否涉检": "是" if r["主要类别"] != "非涉检" else "否",
                        "相似案例": r["相似案例"],
                        "关联法条": r["关联法条"]
                    }
                results.append(res)
            
            result_df = pd.DataFrame(results)
            
            # 重复点位聚合
            if not result_df.empty:
                valid_locs = result_df['点位'].apply(lambda x: x not in ["—", "⚠️ 点位缺失", "None", ""])
                if valid_locs.any():
                    loc_counts = Counter(result_df.loc[valid_locs, '点位'].tolist())
                    result_df['重复次数'] = result_df['点位'].apply(
                        lambda x: loc_counts.get(x, 1) if x not in ["—", "⚠️ 点位缺失", "None", ""] else 1
                    )
                    result_df['点位标记'] = result_df.apply(
                        lambda r: f"🔴 {r['点位']} (同地址{r['重复次数']}条)" if r['重复次数'] > 1 and r['点位'] not in ["—", "⚠️ 点位缺失", "None", ""] else r['点位'],
                        axis=1
                    )
                else:
                    result_df['重复次数'] = 1
                    result_df['点位标记'] = result_df['点位']
            else:
                result_df = pd.DataFrame(columns=[
                    "工单编号", "工单内容", "主要类别", "次要类别", "置信度", "点位", "重复次数", "点位标记",
                    "命中核心词", "命中特征词", "是否涉检", "相似案例", "关联法条", "得分"
                ])
            
            # 点位筛选
            display_df = result_df.copy()
            if only_with_location and not display_df.empty:
                display_df = display_df[display_df['点位'].isin(["—", "⚠️ 点位缺失", "None", ""]) == False]
            
            # 保存历史台账
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_path = os.path.join(HISTORY_DIR, f"筛查结果_{timestamp}.xlsx")
            if not result_df.empty:
                result_df.to_excel(history_path, index=False)
            
            history_files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith('.xlsx')], reverse=True)
            
            stats = f"✅ 完成：{len(result_df)}条（涉检{sum(result_df['是否涉检']=='是') if not result_df.empty else 0}条）"
            if only_with_location:
                stats += f" | 当前显示含点位：{len(display_df)}条"
            
            # 构造展示表
            if display_df.empty:
                show_df = pd.DataFrame(columns=empty_cols)
            else:
                show_df = display_df[["工单编号", "工单内容", "主要类别", "次要类别", "置信度", "点位标记", "重复次数", "命中核心词", "相似案例", "关联法条"]].copy()
            
            return show_df, stats, None, gr.update(choices=history_files, value=history_files[0] if history_files else None), result_df
        
        # 事件绑定
        analyze_btn.click(
            fn=run_batch,
            inputs=[batch_file, only_loc_chk, use_api_chk],
            outputs=[result_table, status_txt, export_file, history_dd, full_data_state]
        )
        
        export_btn.click(
            fn=export_df,
            inputs=full_data_state,
            outputs=export_file
        )
        
        load_hist_btn.click(
            fn=load_history,
            inputs=history_dd,
            outputs=hist_preview
        )
        
        def refresh_hist():
            files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith('.xlsx')], reverse=True)
            return gr.update(choices=files, value=files[0] if files else None)
        
        refresh_hist_btn.click(
            fn=refresh_hist,
            outputs=history_dd
        )


# ============================================================
# 主程序入口（Tabs 页面切换版）
# ============================================================
with gr.Blocks(css=CUSTOM_CSS, title="智检民声 - 12345涉检线索智能筛查系统") as demo:

    with gr.Tabs(elem_classes=["hidden-tabs"]) as tabs:

        # --- Tab 0: 首页 ---
        with gr.TabItem("首页", id=0):
            with gr.Column(elem_classes="home-wrap"):
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

        # --- Tab 1: 单条查询 ---
        with gr.TabItem("单条", id=1):
            with gr.Row():
                with gr.Column(scale=1):
                    btn_back_1 = gr.Button("← 返回首页", size="sm", elem_classes="nav-back")
                with gr.Column(scale=6):
                    gr.Markdown("")
            build_single_query()

        # --- Tab 2: 批量筛查 ---
        with gr.TabItem("批量", id=2):
            with gr.Row():
                with gr.Column(scale=1):
                    btn_back_2 = gr.Button("← 返回首页", size="sm", elem_classes="nav-back")
                with gr.Column(scale=6):
                    gr.Markdown("")
            build_batch_screening()

    # --- 页面切换事件 ---
    def go_home():
        return gr.Tabs.update(selected=0)

    def go_single():
        return gr.Tabs.update(selected=1)

    def go_batch():
        return gr.Tabs.update(selected=2)

    btn_to_single.click(go_single, outputs=tabs)
    btn_to_batch.click(go_batch, outputs=tabs)
    btn_back_1.click(go_home, outputs=tabs)
    btn_back_2.click(go_home, outputs=tabs)


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=6009, share=False)