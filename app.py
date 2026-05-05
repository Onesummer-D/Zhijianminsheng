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
import json
import time
import threading

# ========== 轻量级审计日志 ==========
LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)
_log_lock = threading.Lock()

def log_audit(action_type, input_text, result_dict, duration_ms=None, client_ip="unknown"):
    """追加写入 JSONL，失败不影响主流程"""
    try:
        now = datetime.now()
        log_file = os.path.join(LOG_DIR, f"audit_{now.strftime('%Y-%m-%d')}.jsonl")
        snippet = input_text[:200] + "..." if len(input_text) > 200 else input_text
        
        # 兼容 app.py 里两种字段命名
        main_cat = (result_dict.get("主要类别") or result_dict.get("category") or "unknown")
        conf = (result_dict.get("置信度等级") or result_dict.get("置信度") or result_dict.get("confidence") or "unknown")
        score = (result_dict.get("得分") or result_dict.get("score") or result_dict.get("net_score") or 0)
        
        entry = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action_type,
            "client_ip": client_ip,
            "input_snippet": snippet,
            "main_category": main_cat,
            "confidence": conf,
            "score": score,
            "duration_ms": duration_ms,
        }
        with _log_lock:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[AUDIT ERROR] {e}")
# ====================================
sys.path.insert(0, '/root/zhijianminsheng')

# ==================== 从 single_query_v2 导入完整分析能力 ====================
from single_query_v2 import (
    analyze_real,
    get_laws_for_category,
    get_similar_cases,
    LEGAL_BASIS,
    MATCHER,
    sort_laws_by_match
)
print("✅ 已导入 single_query_v2 完整分析模块")

from extract_elements import auto_extract, format_elements

# ==================== 合并CSS：首页 + 单条查询原版 + 批量 ====================
CUSTOM_CSS = """
/* === 全局干掉Gradio默认focus橘色/蓝色框 === */
*:focus, *:focus-visible, *:active { outline: none !important; box-shadow: none !important; }
.gr-box, .gr-button, .gr-form, .gr-panel, div[role="button"], button, select, input, tr { 
    outline: none !important; box-shadow: none !important; 
}
/* ========================================== */

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

/* ========== 批量筛查：File组件去橘色框 + 隐藏上传提示 ========== */
/* ========== 批量筛查：File组件放大 + 上传后文件名不遮挡 ========== */
.clean-file,
[data-testid="file"] {
    min-height: 100px !important;
    height: auto !important;
    overflow: visible !important;
}

.clean-file .upload-container,
.clean-file > div:first-child,
[data-testid="file"] .upload-container,
[data-testid="file"] > div:first-child {
    min-height: 80px !important;
    padding: 20px 16px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    background: #fafafa !important;
    border: 1px dashed #ccc !important;
    box-shadow: none !important;
    border-radius: 4px !important;
}

.clean-file .upload-container:hover,
[data-testid="file"] .upload-container:hover {
    background: #f5f5f5 !important;
    border-color: #999 !important;
}

.clean-file .upload-text,
.clean-file .file-upload h3,
.clean-file .file-upload p,
.clean-file [class*="upload"] h3,
.clean-file [class*="upload"] p,
[data-testid="file"] .upload-text,
[data-testid="file"] h3,
[data-testid="file"] p {
    display: none !important;
}

/* 已上传文件名区域：独立空间，确保不被虚线框遮挡 */
.clean-file .file-preview,
[data-testid="file"] .file-preview,
[data-testid="file"] .file-info,
[data-testid="file"] .file-name {
    margin-top: 12px !important;
    padding: 10px 12px !important;
    background: #f5f5f5 !important;
    border-radius: 4px !important;
    width: 100% !important;
    box-sizing: border-box !important;
    position: relative !important;
    z-index: 2 !important;
}
/* 强制 Markdown 标题顶部对齐 */
.markdown h2 { margin-top: 0 !important; padding-top: 0 !important; }
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
        start_ts = time.time()
        result = analyze_real(text)
        cat = result["主要类别"]

        # 【新增】直接调用要素提取，不依赖 analyze_real 返回
        elements_data = format_elements(auto_extract(text, cat))

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

            # 【关键修复】用法条匹配度排序，不再直接取前几条
            match_text = text[:80]

            combined_laws = {"default": [], "extended": []}
            seen_ids = set()

            if all_categories:
                primary_cat = all_categories[0]
                secondary_cats = [c for c in all_categories[1:] if c and "非涉检" not in c][:2]

                sec_slots = min(len(secondary_cats) * 2, 2)
                pri_slots = 6 - sec_slots

                p_laws = get_laws_for_category(primary_cat)
                # 【修复】合并 default+extended 统一排序
                all_p_laws = p_laws.get("default", []) + p_laws.get("extended", [])
                all_p_sorted = sort_laws_by_match(all_p_laws, match_text)

                for item in all_p_sorted[:pri_slots]:
                    item_id = item.get('编号', item.get('title', str(item)))
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        combined_laws["default"].append(item)
                for item in all_p_sorted[pri_slots:pri_slots+3]:
                    item_id = item.get('编号', item.get('title', str(item)))
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        combined_laws["extended"].append(item)

                if secondary_cats and sec_slots > 0:
                    per_sec = max(1, sec_slots // len(secondary_cats))
                    for sec_cat in secondary_cats:
                        s_laws = get_laws_for_category(sec_cat)
                        # 【修复】次类别同样合并排序
                        all_s_laws = s_laws.get("default", []) + s_laws.get("extended", [])
                        all_s_sorted = sort_laws_by_match(all_s_laws, match_text)

                        for item in all_s_sorted[:per_sec]:
                            item_id = item.get('编号', item.get('title', str(item)))
                            if item_id not in seen_ids:
                                seen_ids.add(item_id)
                                combined_laws["default"].append(item)
                        for item in all_s_sorted[per_sec:per_sec+2]:
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

        duration = int((time.time() - start_ts) * 1000)
        log_audit("single_query", text, result, duration)

        return [
            text,
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
            result["双引擎详情"],
            elements_data
        ]

    def clear():
        return [
            "",
            "—", "—", "—", "—", "—", "—",
            '<span style="color:#999; font-size:15px;">等待分析...</span>',
            '<span style="color:#999; font-size:15px;">—</span>',
            "—", "—", 
            "<span style='color:#999; font-size:14px;'>等待分析...</span>",
            "等待分析...",
            "—"
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
                    analyze_btn = gr.Button("开始分析", variant="primary", scale=2)
                    clear_btn = gr.Button("清空", scale=1)

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

                with gr.Accordion("📋 要素提取（结构化信息）", open=False):
                    elements_box = gr.Textbox(
                        label="", 
                        interactive=False, 
                        lines=5, 
                        show_label=False,
                        elem_classes=["output-box"]
                    )

                with gr.Accordion("🔧 双引擎判定详情（技术调试）", open=False):
                    detail = gr.Textbox(
                        label="", 
                        interactive=False, 
                        lines=8, 
                        show_label=False,
                        elem_classes=["output-box"]
                    )

        outputs = [
            input_text,
            main_cat, second_cat, conf_level, suggestion, keywords, location,
            laws, ext_laws,
            similar_case, similarity_score, similar_cases_list,
            detail,
            elements_box
        ]

        analyze_btn.click(fn=on_analyze, inputs=input_text, outputs=outputs)
        clear_btn.click(fn=clear, inputs=None, outputs=outputs)

# ========== 批量筛查辅助函数（修复版） ==========
HISTORY_DIR = "./history"
os.makedirs(HISTORY_DIR, exist_ok=True)

def desensitize_text(text):
    """数据脱敏：手机号、身份证号、银行卡号、门牌号、姓名"""
    import re

    # 1. 银行卡号（16-19位，以3-6开头）
    text = re.sub(r'\b([3-6]\d{3})(\d{8,12})(\d{4})\b', r'\1****\3', text)

    # 2. 身份证号（18位）
    text = re.sub(r'(\d{6})\d{8}(\d{4})', r'\1********\2', text)

    # 3. 手机号（11位）
    text = re.sub(r'(\d{3})\d{4}(\d{4})', r'\1****\2', text)

    # 4. 门牌号（详细地址后缀）
    text = re.sub(
        r'(\d+号楼\d+单元\d+室?|\d+栋\d+单元\d+号?|\d+幢\d+室?|\d+弄\d+号|\d+号院\d+排\d+号|\d+号院\d+楼|\d+号院)',
        '***', text
    )

    # 5. 姓名脱敏（安全模式：只匹配"称呼词+姓名"结构）
    compound_surnames = "欧阳|太史|端木|上官|司马|东方|独孤|南宫|夏侯|诸葛|尉迟|皇甫|公孙|慕容|仲孙|长孙|宇文|司徒|鲜于|司空|令狐|公冶|澹台|屠羊|漆雕|乐正|宰父|谷梁|拓跋|夹谷|轩辕|段干|百里|呼延|东郭|南门|梁丘|左丘|东门|西门"

    # 明显非人名用字（简单过滤，避免"我叫他去"被误伤）
    non_name_chars = set("来去说看走听想吃喝睡坐站跑跳拿放打开关上下进出回前后左右大小好坏对错是否有无这那")

    def desensitize_single_name(name):
        if len(name) <= 1:
            return name
        # 过滤：名里包含明显非人名用字，可能是误匹配
        if any(c in non_name_chars for c in name[1:]):
            return name
        # 判断复姓
        for cs in compound_surnames.split('|'):
            if name.startswith(cs):
                return cs + '*' * (len(name) - len(cs))
        # 单姓
        return name[0] + '*' * (len(name) - 1)

    # 模式1: XX叫YYY（我/他/她/老板/包工头/老伴/带班组长...）
    def replace_name1(m):
        return m.group(1) + '叫' + desensitize_single_name(m.group(2))
    text = re.sub(r'(老板|包工头|老伴|真名|带班组长|联系人|来电人|反映人|本人|我|他|她)\s*叫\s*([一-龥]{2,4})', replace_name1, text)

    # 模式2: 姓名/名字:YYY
    def replace_name2(m):
        return m.group(1) + m.group(2) + desensitize_single_name(m.group(3))
    text = re.sub(r'(姓名|名字)(\s*[：:]\s*)([一-龥]{2,4})', replace_name2, text)

    # 模式3: 真名叫YYY / 名为YYY / 名字叫YYY
    def replace_name3(m):
        return m.group(1) + desensitize_single_name(m.group(2))
    text = re.sub(r'(真名\s*叫|名为|名字叫)\s*([一-龥]{2,4})', replace_name3, text)

    return text

# 【新增】基于命中核心词自动选择最匹配法条（从法条编号提取罪名关键词，非硬编码）
def select_best_law(category, core_words_text, all_laws_db):
    """自动从法条库中选择最匹配的法条编号。逻辑：从法条编号提取'XX罪'等关键词，
    与工单命中核心词做匹配，避免总是返回 default 列表的第一条。"""
    if not category or category in ("非涉检", "无") or not core_words_text:
        return "—"

    import re
    laws = all_laws_db.get(category, {})
    items = laws.get("default", []) + laws.get("extended", [])
    if not items:
        return "—"

    text = str(core_words_text)
    best_item = items[0]
    best_score = -1

    for item in items:
        number = item.get("编号", "")
        content = item.get("内容", "")
        if not number:
            continue

        score = 0

        # 1. 从法条编号自动提取"XX罪"关键词（如"诈骗罪"→"诈骗"）
        crime_names = re.findall(r'([\u4e00-\u9fa5]{2,12})罪', number)
        for cname in crime_names:
            if cname in text:
                score += 20  # 完整罪名匹配，最高分
            else:
                # 拆字匹配：如"盗窃"拆成"盗""窃"
                for char in cname:
                    if char in text:
                        score += 3

        # 2. 公益诉讼/行政场景辅助匹配
        if category == "公益诉讼":
            if any(w in content for w in ["环境", "污染", "生态"]):
                if any(w in text for w in ["污染", "臭", "污水", "垃圾", "烧", "刺鼻"]):
                    score += 5
            if any(w in content for w in ["文物", "文化"]):
                if any(w in text for w in ["文物", "拓印", "刻字", "遗址", "塔", "宅"]):
                    score += 5
            if any(w in content for w in ["野生动物", "狩猎", "渔业"]):
                if any(w in text for w in ["鸟", "猎", "捕", "鱼", "电鱼"]):
                    score += 5

        if score > best_score:
            best_score = score
            best_item = item

    return best_item.get("编号", "—")

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

    # 【修复】标签对齐：非涉检统一显示为"无"
    if not main_cat:
        return {
            "主要类别": "无",
            "次要类别": "无",
            "置信度等级": "⚪ 非涉检线索",
            "建议操作": "无需检察介入",
            "核心定性词": "无",
            "点位": "—",
            "命中核心词": "无",
            "命中特征词": "无",
            "相似案例": "—",
            "关联法条": "—",
            "得分": 0,
            "要素提取": "—"
        }

    conf = rule.calculate_confidence(text, main_cat)
    score = conf.get("score", 0)
    level = conf.get("level", "低")
    core = conf.get("matched_core", [])
    feat = conf.get("matched_feature", [])

    # 次要类别
    second_cat = None
    second_score = 0
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
        second_score = all_scores[best_sec]
        if all_scores[best_sec] >= 3:
            second_cat = best_sec

    # 点位
    try:
        from single_query_v2 import extract_location
        loc = extract_location(text)
    except:
        loc = "—"

    # 相似案例：统一使用 TF-IDF 余弦相似度引擎
    best_match, _ = MATCHER.match(text, main_cat, top_k=1)
    sim_case = best_match.get("title", "—") if best_match else "—"

    # 【修复】法条选择：使用 select_best_law（带场景映射）而非 sort_laws_by_match 第一条
    cat_laws = get_laws_for_category(main_cat)
    core_words_text = f"{'、'.join(core)} {'、'.join(feat)}"
    sim_law = select_best_law(main_cat, core_words_text, {main_cat: cat_laws})

    # 要素提取
    elements = auto_extract(text, main_cat)

    # 置信度等级和建议操作
    if score >= 6:
        suggestion = "🟢 建议优先处理"
        conf_level = f"🟢 高置信度（{score}分）"
    elif score >= 3:
        suggestion = "🟡 建议人工复核"
        conf_level = f"🟡 中置信度（{score}分）"
    else:
        suggestion = "🔴 需人工复核"
        conf_level = f"🔴 低置信度（{score}分）"

    # 【修复】快速通道也返回次要类别（与 analyze_real 一致）
    second_display = second_cat if (second_score >= 3 and second_cat) else "无"

    return {
        "主要类别": main_cat,
        "次要类别": second_display,
        "置信度等级": conf_level,
        "建议操作": suggestion,
        "核心定性词": "、".join(core) if core else "无",
        "点位": loc if loc else "⚠️ 点位缺失",
        "命中核心词": "、".join(core) if core else "无",
        "命中特征词": "、".join(feat) if feat else "无",
        "相似案例": sim_case,
        "关联法条": sim_law,
        "要素提取": format_elements(elements),
        "得分": score
    }

def load_history(filename, filter_cat="全部", filter_loc="全部", filter_conf="全部"):
    cols = ["工单编号", "主要类别", "置信度", "点位"]
    if not filename:
        return pd.DataFrame(columns=cols)
    path = os.path.join(HISTORY_DIR, filename)
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)

    df = pd.read_excel(path)
    # 清洗点位列：转字符串、去空格、填NaN
    if "点位" in df.columns:
        df["点位"] = df["点位"].astype(str).str.strip()
        df["点位"] = df["点位"].replace(["nan", "None", "<NA>", ""], "—")
    for c in cols:
        if c not in df.columns:
            df[c] = "—"

    # 类别筛选
    if filter_cat != "全部" and "主要类别" in df.columns:
        df = df[df["主要类别"] == filter_cat]

    # 点位筛选
    if filter_loc != "全部" and "点位" in df.columns:
        invalid_vals = ["—", "⚠️ 点位缺失", "None", "", "nan", "NaN", "<NA>"]
        if filter_loc == "有点位":
            df = df[~df["点位"].isin(invalid_vals)]
        elif filter_loc == "无点位":
            df = df[df["点位"].isin(invalid_vals)]
        elif filter_loc == "同地址聚合":
            # 【关键】只统计有效点位，排除所有无效值
            valid_df = df[~df["点位"].isin(invalid_vals)]
            addr_counts = valid_df["点位"].value_counts()
            dup_addrs = addr_counts[addr_counts > 1].index.tolist()
            df = df[df["点位"].isin(dup_addrs)]

    # 置信度筛选
    if filter_conf != "全部" and "置信度" in df.columns:
        emoji_map = {"高": "🟢", "中": "🟡", "低": "🔴"}
        emoji = emoji_map.get(filter_conf, "")
        if emoji:
            df = df[df["置信度"].astype(str).str.contains(emoji, na=False)]

    return df[cols] if not df.empty else pd.DataFrame(columns=cols)

def export_df(full_df):
    if full_df is None or len(full_df) == 0:
        return None
    path = f"批量筛查导出_{datetime.now().strftime('%H%M%S')}.xlsx"
    full_df.to_excel(path, index=False)
    return path

def merge_duplicate_complaints(df):
    """
    双轨制重复投诉合并：
    1. 有明确点位的：同点位 + 核心词重叠>=2 → 合并
    2. 无点位的：同类别 + 核心词重叠>=2 → 兜底合并
    """
    if len(df) < 2:
        return df

    INVALID_LOCS = ['—', '⚠️ 点位缺失', 'None', '', 'nan']
    merged_rows = []
    skip_indices = set()

    for i in range(len(df)):
        if i in skip_indices:
            continue

        row_i = df.iloc[i]
        loc_i = str(row_i.get('点位', '')).strip()
        main_i = str(row_i.get('主要类别', '')).strip()
        core_i = set(str(row_i.get('命中核心词', '')).replace('、', ' ').split())

        dup_group = [i]
        for j in range(i + 1, len(df)):
            if j in skip_indices:
                continue

            row_j = df.iloc[j]
            loc_j = str(row_j.get('点位', '')).strip()
            main_j = str(row_j.get('主要类别', '')).strip()
            core_j = set(str(row_j.get('命中核心词', '')).replace('、', ' ').split())

            # ========== 轨道A：有明确点位，按点位+核心词合并 ==========
            has_loc_i = loc_i not in INVALID_LOCS
            has_loc_j = loc_j not in INVALID_LOCS

            if has_loc_i and has_loc_j:
                if loc_i == loc_j and len(core_i & core_j) >= 2:
                    dup_group.append(j)
                    skip_indices.add(j)
                    continue

            # ========== 轨道B：至少一方无点位，按类别+核心词兜底 ==========
            if main_i == main_j and main_i not in ['', '无', '—', '非涉检'] and len(core_i & core_j) >= 2:
                dup_group.append(j)
                skip_indices.add(j)
                continue

        main_row = df.iloc[i].copy()
        if len(dup_group) > 1:
            merged_ids = [str(df.iloc[k]['工单编号']) for k in dup_group[1:]]
            orig_content = str(main_row['工单内容'])
            main_row['工单内容'] = orig_content + f"\n\n[已合并重复投诉: {', '.join(merged_ids)}]"
            orig_loc_mark = str(main_row.get('点位标记', main_row.get('点位', '—')))
            if '(内容重复合并' not in orig_loc_mark:
                main_row['点位标记'] = orig_loc_mark + f" (内容重复合并{len(dup_group)}条)"

        merged_rows.append(main_row)

    return pd.DataFrame(merged_rows)

# ========== 批量筛查 UI（修复版） ==========
def build_batch_screening():
    with gr.Column():
        # ========== 标题行 ==========
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 📁 批量工单筛查")
            with gr.Column(scale=1):
                gr.Markdown("## 📜 筛查台账")

        # ========== 左右内容区 ==========
        with gr.Row():
            with gr.Column(scale=1):
                batch_file = gr.File(
                    show_label=False,
                    file_types=[".xlsx"],
                    elem_classes=["clean-file"]
                )

                with gr.Row():
                    only_loc_chk = gr.Checkbox(label="只看含点位工单", value=False, scale=1)
                    use_api_chk = gr.Checkbox(label="启用DeepSeek API复核", value=False, scale=1)
                    merge_dup_chk = gr.Checkbox(label="合并重复投诉", value=False, scale=1)

                # 【关键】按钮紧跟Checkbox，与右栏按钮对齐
                with gr.Row():
                    analyze_btn = gr.Button("开始批量筛查", variant="primary", scale=1)
                    export_btn = gr.Button("导出当前结果Excel", variant="secondary", scale=1)

                status_txt = gr.Textbox(label="执行状态", interactive=False)
                export_file = gr.File(label="下载导出文件", interactive=False)

            with gr.Column(scale=1):
                history_dd = gr.Dropdown(label="选择历史记录", choices=[], interactive=True, value=None)

                with gr.Row():
                    filter_cat = gr.Dropdown(
                        choices=["全部", "刑事犯罪", "公益诉讼", "民事支持起诉", "行政执法监督"], 
                        value="全部", label="类别筛选", scale=1
                    )
                    filter_loc = gr.Dropdown(
                        choices=["全部", "有点位", "无点位", "同地址聚合"], 
                        value="全部", label="点位筛选", scale=1
                    )
                    filter_conf = gr.Dropdown(
                        choices=["全部", "高", "中", "低"], 
                        value="全部", label="置信度筛选", scale=1
                    )

                hist_preview = gr.DataFrame(
                    label="历史记录预览",
                    interactive=False,
                    headers=["工单编号", "主要类别", "置信度"],
                    value=[]
                )

                # 【关键】按钮紧跟历史记录预览，与左栏按钮对齐
                with gr.Row():
                    load_hist_btn = gr.Button("加载选中类别", scale=1)
                    refresh_hist_btn = gr.Button("更新文件列表", scale=1)

        gr.Markdown("---")
        gr.Markdown("### 📊 筛查结果列表")

        result_table = gr.DataFrame(
            label="结果列表",
            headers=["工单编号", "工单内容", "主要类别", "次要类别", "置信度", "点位标记", "重复次数", "命中核心词", "相似案例", "关联法条", "要素提取"],
            interactive=False,
            value=[]
        )

        full_data_state = gr.DataFrame(visible=False)

        def run_batch(file_obj, only_with_location, use_api, merge_dup):
            DISPLAY_COLS = ["工单编号", "工单内容", "主要类别", "次要类别", "置信度", "点位标记", "重复次数", "命中核心词", "相似案例", "关联法条", "要素提取"]
            ALL_COLS = ["工单编号", "工单内容", "主要类别", "次要类别", "置信度", "点位", "重复次数", "点位标记", "命中核心词", "命中特征词", "是否涉检", "相似案例", "关联法条", "得分", "要素提取"]

            if file_obj is None:
                yield pd.DataFrame(columns=DISPLAY_COLS), "请先上传Excel", None, gr.update(choices=[]), pd.DataFrame()
                return

            df = pd.read_excel(file_obj.name if hasattr(file_obj, 'name') else file_obj)

            content_col = None
            for c in ['工单内容', '主要内容', '诉求内容', '问题描述']:
                if c in df.columns:
                    content_col = c
                    break
            if not content_col:
                content_col = df.columns[0]

            results = []
            total = len(df)

            yield pd.DataFrame(columns=DISPLAY_COLS), "⏳ 开始分析...", None, gr.update(choices=[]), pd.DataFrame()

            for idx, row in df.iterrows():
                text = str(row.get(content_col, ''))
                if not text or text == 'nan':
                    continue

                desensitized_text = desensitize_text(text)
                content = desensitized_text[:500] + "..." if len(desensitized_text) > 500 else desensitized_text

                if use_api:
                    rule_r = analyze_batch_rule_only(text)

                    if rule_r["主要类别"] == "无":
                        res = {
                            "工单编号": row.get('工单编号', f'NO.{idx+1:03d}'),
                            "工单内容": content,
                            "主要类别": "无",
                            "次要类别": "无",
                            "置信度": "⚪ 非涉检线索",
                            "得分": 0,
                            "点位": "—",
                            "命中核心词": "无",
                            "命中特征词": "无",
                            "是否涉检": "否",
                            "相似案例": "—",
                            "关联法条": "—",
                            "要素提取": rule_r["要素提取"]
                        }
                    else:
                        r = analyze_real(text)

                        api_cat = r.get("主要类别", "无")
                        api_laws = get_laws_for_category(api_cat)
                        api_sorted = sort_laws_by_match(api_laws.get("default", []) + api_laws.get("extended", []), text)
                        api_law_str = api_sorted[0].get("编号", "—") if api_sorted else "—"

                        res = {
                            "工单编号": row.get('工单编号', f'NO.{idx+1:03d}'),
                            "工单内容": content,
                            "主要类别": r.get("主要类别", "无"),
                            "次要类别": r.get("次要类别", "无"),
                            "置信度": r.get("置信度等级", "—"),
                            "得分": 0,
                            "点位": r.get("点位", "—"),
                            "命中核心词": r.get("核心定性词", "无"),
                            "命中特征词": "无",
                            "是否涉检": "否" if r.get("主要类别", "") == "无" else "是",
                            "相似案例": r.get("相似案例", {}).get("title", "—") if isinstance(r.get("相似案例"), dict) else "—",
                            "关联法条": api_law_str,
                            "要素提取": format_elements(auto_extract(text, r.get("主要类别", "无")))
                        }
                else:
                    r = analyze_batch_rule_only(text)

                    res = {
                        "工单编号": row.get('工单编号', f'NO.{idx+1:03d}'),
                        "工单内容": content,
                        "主要类别": r["主要类别"],
                        "次要类别": r["次要类别"],
                        "置信度": r["置信度等级"],
                        "得分": r["得分"],
                        "点位": r["点位"],
                        "命中核心词": r["命中核心词"],
                        "命中特征词": r["命中特征词"],
                        "是否涉检": "否" if r["主要类别"] == "无" else "是",
                        "相似案例": r["相似案例"],
                        "关联法条": r["关联法条"],
                        "要素提取": r["要素提取"]
                    }
                results.append(res)
                log_audit("batch_item", text, res)

                if (idx + 1) % 5 == 0 or idx == total - 1:
                    pct = int((idx + 1) / total * 100)
                    yield pd.DataFrame(columns=DISPLAY_COLS), f"⏳ 分析中... {pct}% ({idx+1}/{total} 条)", None, gr.update(choices=[]), pd.DataFrame()

            if results:
                result_df = pd.DataFrame(results)
                for col in ALL_COLS:
                    if col not in result_df.columns:
                        result_df[col] = "—"
            else:
                result_df = pd.DataFrame(columns=ALL_COLS)

            if not result_df.empty:
                def _is_valid_loc(x):
                    return x and str(x).strip() not in ["—", "⚠️ 点位缺失", "None", "", "nan"]

                valid_locs = result_df['点位'].apply(_is_valid_loc)
                loc_counts = Counter(result_df.loc[valid_locs, '点位'].tolist())

                def _get_repeat_count(row):
                    loc = str(row['点位']).strip()
                    if _is_valid_loc(loc):
                        return loc_counts.get(loc, 1)
                    return 1

                def _get_loc_mark(row):
                    loc = str(row['点位']).strip()
                    count = row['重复次数']
                    if _is_valid_loc(loc) and count > 1:
                        return f"🔴 {loc} (同地址{count}条)"
                    return loc if _is_valid_loc(loc) else "—"

                result_df['重复次数'] = result_df.apply(_get_repeat_count, axis=1)
                result_df['点位标记'] = result_df.apply(_get_loc_mark, axis=1)

            if merge_dup and not result_df.empty:
                result_df = merge_duplicate_complaints(result_df)

            display_df = result_df.copy()
            if only_with_location and not display_df.empty:
                display_df = display_df[display_df['点位'].isin(["—", "⚠️ 点位缺失", "None", ""]) == False]

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_path = os.path.join(HISTORY_DIR, f"筛查结果_{timestamp}.xlsx")
            if not result_df.empty:
                result_df.to_excel(history_path, index=False)

            history_files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith('.xlsx')], reverse=True)

            stats = f"✅ 完成：{len(result_df)}条（涉检{sum(result_df['是否涉检']=='是') if not result_df.empty else 0}条）"
            if only_with_location:
                stats += f" | 当前显示含点位：{len(display_df)}条"

            if display_df.empty:
                show_df = pd.DataFrame(columns=DISPLAY_COLS)
            else:
                show_df = display_df[DISPLAY_COLS].copy()

            yield show_df, stats, None, gr.update(choices=history_files, value=history_files[0] if history_files else None), result_df

        analyze_btn.click(
            fn=run_batch,
            inputs=[batch_file, only_loc_chk, use_api_chk, merge_dup_chk],
            outputs=[result_table, status_txt, export_file, history_dd, full_data_state]
        )

        export_btn.click(
            fn=export_df,
            inputs=full_data_state,
            outputs=export_file
        )

        load_hist_btn.click(
            fn=load_history,
            inputs=[history_dd, filter_cat, filter_loc, filter_conf],
            outputs=hist_preview
        )

        def refresh_hist():
            files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith('.xlsx')], reverse=True)
            return gr.update(choices=files, value=files[0] if files else None)

        refresh_hist_btn.click(
            fn=refresh_hist,
            outputs=history_dd
        )

# 主程序入口（Column visible 切换版 - 稳定可用）
# ============================================================
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

        gr.HTML("""
<div style="text-align:center; margin-top:150px; color:#64748b; font-size:13px; letter-spacing:2px;">
    智能检索，为民发声
</div>
        """)
    # --- 单条查询页 ---
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
        return [
            gr.update(visible=(page == "home")),
            gr.update(visible=(page == "single")),
            gr.update(visible=(page == "batch"))
        ]

    btn_to_single.click(lambda: switch("single"), None, [page_home, page_single, page_batch])
    btn_to_batch.click( lambda: switch("batch"),  None, [page_home, page_single, page_batch])
    btn_back_1.click(   lambda: switch("home"),   None, [page_home, page_single, page_batch])
    btn_back_2.click(   lambda: switch("home"),   None, [page_home, page_single, page_batch])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=6009, share=False)