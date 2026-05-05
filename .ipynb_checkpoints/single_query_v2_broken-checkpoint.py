
import gradio as gr
import re
import os
import sys
import pandas as pd
from typing import Dict, List, Tuple, Optional

# 导入规则引擎（由convert_excel.py自动生成）
import rule_engine_keywords as rule

# ========== 1. 点位提取函数（修复版） ==========
def extract_location(text: str) -> str:
    """从文本中提取地址/点位信息"""
    if not text or len(text) < 5:
        return "—"

    # 清洗前缀干扰词（角色称谓+介词）
    clean_text = text
    prefix_patterns = [
        r'我在', r'我们在', r'我在', r'我们在', r'在',
        r'老板', r'包工头', r'负责人', r'公司', r'工厂', r'工地',
        r'村委会', r'居委会'
    ]
    for prefix in prefix_patterns:
        clean_text = re.sub(f'^{prefix}', '', clean_text)
        clean_text = re.sub(f'[，,。]\s*{prefix}', '，', clean_text)

    # 清洗干扰词
    clean_text = re.sub(r'村委会|居委会|附近|旁边|周边', '', clean_text)

    # 模式A：区+镇/街道+村（最完整）
    pattern_a = r'([一-龥]{2,4}区)([一-龥]{2,6}(?:镇|街道|乡))([一-龥]{2,6}(?:村|社区|小区|路|街))'
    match = re.search(pattern_a, clean_text)
    if match:
        addr = match.group(1) + match.group(2) + match.group(3)
        return addr if len(addr) >= 4 else "—"

    # 模式B：镇/街道+村（无区）
    pattern_b = r'([一-龥]{2,6}(?:镇|街道|乡))([一-龥]{2,6}(?:村|社区|小区|路|街))'
    match = re.search(pattern_b, clean_text)
    if match:
        addr = match.group(1) + match.group(2)
        return addr if len(addr) >= 4 else "—"

    # 兜底：区+镇/街道
    pattern_fallback = r'([一-龥]{2,4}区)([一-龥]{2,6}(?:镇|街道|乡))'
    match = re.search(pattern_fallback, clean_text)
    if match:
        addr = match.group(1) + match.group(2)
        return addr if len(addr) >= 4 else "—"

    return "—"

# ========== 2. 法条查询函数（多标签合并版） ==========
def get_laws_for_categories(categories: List[str]) -> Dict:
    """支持多类别法条查询，去重合并"""
    result = {"default": [], "extended": []}
    seen = set()

    for cat in categories:
        if not cat or "非涉检" in cat or "—" in cat:
            continue
        law_data = rule.LEGAL_BASIS.get(cat, {"default": [], "extended": []})
        for key in ["default", "extended"]:
            for item in law_data.get(key, []):
                item_id = item.get('编号', item.get('title', str(item)))
                if item_id not in seen:
                    seen.add(item_id)
                    result[key].append(item)
    return result

def get_laws_html(categories: List[str]) -> str:
    """生成多类别法条HTML（保持UI标准）"""
    law_data = get_laws_for_categories(categories if isinstance(categories, list) else [categories])

    html_parts = []

    # 默认法条
    defaults = law_data.get("default", [])
    if defaults:
        for i, law in enumerate(defaults[:3], 1):  # 最多显示3条
            title = law.get('title', '未知法条')
            content = law.get('content', '')
            html_parts.append(f"""
                <div style="margin-bottom:12px; padding:10px; background:#f8f9fa; border-radius:6px; border-left:3px solid #2c7be5;">
                    <div style="font-weight:600; color:#2c7be5; margin-bottom:6px; font-size:16px;">
                        {i}. {title}
                    </div>
                    <div style="color:#444; line-height:1.6; font-size:15px;">
                        {content[:120]}{'...' if len(content) > 120 else ''}
                    </div>
                </div>
            """)

    # 扩展法条（折叠）
    extended = law_data.get("extended", [])
    if extended:
        ext_html = []
        for law in extended[:2]:  # 最多2条扩展
            title = law.get('title', '未知')
            content = law.get('content', '')
            ext_html.append(f"<div style='margin:6px 0; font-size:14px; color:#666;'>• {title}：{content[:80]}...</div>")

        html_parts.append(f"""
            <details style="margin-top:10px;">
                <summary style="color:#666; cursor:pointer; font-size:14px;">查看更多关联法条（{len(extended)}条）</summary>
                <div style="margin-top:8px; padding:8px; background:#f5f5f5; border-radius:4px;">
                    {''.join(ext_html)}
                </div>
            </details>
        """)

    if not html_parts:
        return '<div style="color:#999; font-size:15px;">—</div>'

    return f'<div class="law-container" style="margin-top:-12px;">{"" .join(html_parts)}</div>'

# ========== 3. 相似案例匹配（简化版） ==========
def get_similar_cases(category: str, text: str) -> str:
    """基于类别的相似案例提示"""
    if not category or "非涉检" in category or "—" in category:
        return "—"

    cases_db = {
        "刑事犯罪": [
            "【拒不支付劳动报酬案】房山区某建筑工地包工头逃匿，拖欠农民工工资，经检察机关介入后追回欠薪并追究刑事责任",
            "【非法采矿案】某镇村民盗采砂石破坏生态，检察机关提起刑事附带民事公益诉讼"
        ],
        "公益诉讼": [
            "【环境污染案】某村养殖场排污导致河水变黑，检察机关发出诉前检察建议督促整改",
            "【食药安全案】某小吃街多家商户使用地沟油，检察机关提起公益诉讼"
        ],
        "民事支持起诉": [
            "【农民工讨薪案】某工地20余名农民工被拖欠工资，检察机关支持起诉追回80万元",
            "【赡养费纠纷】老人子女拒不赡养，检察机关支持起诉并协调社区介入"
        ],
        "行政执法监督": [
            "【小过重罚监督】某小商贩首次轻微违法被高额罚款，检察机关建议适用首违不罚",
            "【行政不作为】村民多次投诉违建无果，检察机关督促行政机关履职"
        ]
    }

    cases = cases_db.get(category, [])
    if not cases:
        return "—"

    case_html = []
    for case in cases[:2]:
        case_html.append(f"""
            <div style="margin-bottom:10px; padding:10px; background:#f0f7ff; border-radius:6px; border-left:3px solid #4dabf7; font-size:14px; color:#444;">
                {case}
            </div>
        """)

    return ''.join(case_html)

# ========== 4. 主分析函数（分差算法+智能触发） ==========
def analyze_real(text: str) -> Dict:
    """双引擎分析：规则引擎+DeepSeek API（智能触发版）"""
    if not text or len(text.strip()) < 5:
        return {
            "主要类别": "—", "次要类别": "—", "置信度等级": "—",
            "建议操作": "—", "双引擎判定详情": "输入过短", 
            "点位信息": "—", "关联法条": "—", "相似案例": "—"
        }

    text = text.strip()
    location = extract_location(text)

    # 1. 规则引擎分析
    all_scores = {}
    matched_keywords = []

    for cat in ["刑事犯罪", "公益诉讼", "民事支持起诉", "行政执法监督"]:
        result = rule.calculate_confidence(text, cat)
        score = result.get("score", 0)
        all_scores[cat] = score
        if result.get("matched_keywords"):
            matched_keywords.extend([f"{kw}({cat})" for kw in result["matched_keywords"][:2]])

    # 2. 排序找主类别和次高类别
    sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    rule_primary, rule_score = sorted_scores[0]
    second_cat, second_score = sorted_scores[1] if len(sorted_scores) > 1 else (None, 0)

    # 计算分差
    score_gap = rule_score - second_score

    # 3. 判断是否为涉检线索
    if rule_score == 0:
        return {
            "主要类别": "非涉检线索（普通投诉）",
            "次要类别": "—",
            "置信度等级": "⚪ 非涉检",
            "建议操作": "建议常规处理",
            "双引擎判定详情": f"规则引擎未命中（得分: {all_scores}）\n判定为普通投诉，不涉检察监督范围",
            "点位信息": "—",
            "关联法条": "—",
            "相似案例": "—"
        }

    # 4. 智能触发策略（准确率优先版）
    # 触发DeepSeek的条件（满足任一即触发）：
    # 1. 次高类别 >= 3分（存在潜在交叉）
    # 2. 主类别 < 6分（中低置信度）
    # 3. 分差 < 4分（竞争激烈）
    has_potential_cross = second_score >= 3
    need_deepseek = has_potential_cross or (rule_score < 6) or (score_gap < 4)

    # 快速通道：高置信度(>=6) + 无潜在交叉(<3) + 分差大(>=4)
    if not need_deepseek:
        print(f"⏩ 快速通道：{rule_primary}({rule_score}分)，次高{second_score}分，分差{score_gap}")
        return {
            "主要类别": rule_primary,
            "次要类别": "—",
            "置信度等级": f"🟢 高置信度（{rule_score}分）",
            "建议操作": "🟢 建议优先处理",
            "双引擎判定详情": f"【规则引擎高置信度判定】\n主类别：{rule_primary}（{rule_score}分）\n次高类别：{second_cat or '无'}（{second_score}分）\n分差：{score_gap}分 >= 4分，无交叉风险\n未触发DeepSeek（快速通道）",
            "点位信息": location,
            "关联法条": get_laws_html([rule_primary]),
            "相似案例": get_similar_cases(rule_primary, text)
        }

    # 复核通道：调用DeepSeek API
    print(f"🤖 DeepSeek复核：主{rule_primary}({rule_score}分)，次{second_cat}({second_score}分)，分差{score_gap}")

    api_primary = rule_primary
    api_secondaries = []
    api_reason = "API调用失败，使用规则引擎结果"
    elements = []
    cross_type = "单一类别"
    handling = "常规审查"

    try:
        from api_client import DeepSeekClient
        client = DeepSeekClient()

        # 调用多标签分析
        api_result = client.analyze_multi_label(
            text, 
            rule_primary, 
            [{"category": second_cat, "score": second_score}] if second_score >= 3 else [],
            all_scores
        )

        if api_result:
            api_primary = api_result.get("primary", rule_primary)
            api_secondaries = api_result.get("secondaries", [])
            api_reason = api_result.get("reasoning", "")
            elements = api_result.get("elements", [])
            cross_type = api_result.get("cross_type", "")
            handling = api_result.get("handling", "")
            print(f"✅ DeepSeek返回：主={api_primary}，次={api_secondaries}")

    except Exception as e:
        print(f"⚠️ DeepSeek调用失败: {e}")
        api_result = None

    # 5. 构建次要类别显示
    second_cat_display = "—"
    if api_secondaries:
        sec_parts = []
        for sec in api_secondaries[:2]:  # 最多显示2个次要
            if isinstance(sec, dict):
                sec_name = sec.get("category", "")
                sec_score = sec.get("score", 0)
                if sec_name:
                    sec_parts.append(f"{sec_name}(DeepSeek)")
            elif isinstance(sec, str):
                sec_parts.append(f"{sec}(DeepSeek)")
        if sec_parts:
            second_cat_display = "、".join(sec_parts)
    elif second_score >= 3 and second_cat:
        second_cat_display = f"{second_cat}({second_score}分)"

    # 6. 判断建议操作类型
    is_high_conf = rule_score >= 6
    is_unchanged = (api_primary == rule_primary) and not api_secondaries

    if is_high_conf and is_unchanged:
        suggestion = "🟢 建议优先处理"
        conf_level_final = f"🟢 高置信度（{rule_score}分）"
        warning_suffix = ""
    else:
        # 有修正或多标签
        handling_display = f"（{handling}）" if handling and handling != "常规审查" else ""
        suggestion = f"🟡 建议人工复核 {handling_display}"
        conf_level_final = f"🟡 中置信度（{rule_score}分）+ DeepSeek精修"
        if api_secondaries or (api_primary != rule_primary):
            warning_suffix = " ⚠️【交叉线索】"
            conf_level_final += warning_suffix

    # 7. 收集所有相关类别（主要+次要）用于法条查询
    all_cats = [api_primary]
    if second_cat_display != "—":
        import re
        sec_cats = re.findall(r'([一-龥]+(?:检察|监督|起诉|犯罪))', second_cat_display)
        all_cats.extend(sec_cats)

    # 8. 构建双引擎详情（无截断）
    rule_second_display = second_cat_display if second_cat_display != "—" else "无"
    detail_lines = [
        f"【DeepSeek多标签精修】",
        f"规则引擎初步：{rule_primary}（{rule_score}分）+ {rule_second_display}",
        f"DeepSeek精修：主={api_primary}，次={api_secondaries if api_secondaries else '无'}",
        f"关键要素：{elements}",
        f"法律关系：{cross_type}",
        f"处理方式：{handling}",
        f"推理：{api_reason}"  # 无截断
    ]

    return {
        "主要类别": api_primary,
        "次要类别": second_cat_display,
        "置信度等级": conf_level_final,
        "建议操作": suggestion,
        "双引擎判定详情": "\n".join(detail_lines),
        "点位信息": location,
        "关联法条": get_laws_html(all_cats),
        "相似案例": get_similar_cases(api_primary, text)
    }

# ========== 5. Gradio界面（严格按UI标准） ==========
with gr.Blocks(css="""
    .main-title { text-align: center; margin-bottom: 12px; font-size: 28px; font-weight: bold; color: #2c3e50; }
    .output-box { background: #f8f9fa; padding: 12px; border-radius: 8px; min-height: 40px; font-size: 16px; }
    .law-container { margin-top: -12px; }
    h3 { font-size: 20px !important; margin: 16px 0 12px 0 !important; }
    .left-panel { padding-right: 20px; }
    .right-panel { padding-left: 20px; }
""") as demo:

    gr.HTML('<div class="main-title">🔍 智检民声 - 12345涉检线索智能筛查系统</div>')

    with gr.Row():
        # 左侧输入区
        with gr.Column(scale=1, elem_classes=["left-panel"]):
            gr.Markdown("### 📝 工单内容输入")
            input_text = gr.Textbox(
                label="",
                placeholder="请输入12345工单内容...",
                lines=8,
                elem_classes=["output-box"]
            )
            analyze_btn = gr.Button("🔍 智能分析", variant="primary", size="lg")

            gr.Markdown("### 🔧 双引擎判定详情（技术调试）")
            detail_box = gr.Textbox(
                label="",
                interactive=False,
                lines=12,  # 从8改为12，无截断
                show_label=False,
                elem_classes=["output-box"]
            )

        # 右侧结果区
        with gr.Column(scale=1, elem_classes=["right-panel"]):
            # 识别结果模块
            gr.Markdown("### 📋 识别结果")
            with gr.Group():
                primary_cat = gr.Textbox(label="预期主要类别", interactive=False, elem_classes=["output-box"])
                secondary_cat = gr.Textbox(label="预期次要类别", interactive=False, elem_classes=["output-box"])
                conf_level = gr.Textbox(label="置信度等级", interactive=False, elem_classes=["output-box"])
                suggestion = gr.Textbox(label="建议操作", interactive=False, elem_classes=["output-box"])

            # 点位信息模块
            gr.Markdown("### 📍 点位信息")
            location_box = gr.Textbox(label="", interactive=False, elem_classes=["output-box"])

            # 关联法条模块
            gr.Markdown("### ⚖️ 关联法条")
            law_box = gr.HTML(label="", elem_classes=["law-container"])

            # 相似案例模块
            gr.Markdown("### 🔍 相似案例提示")
            similar_box = gr.HTML(label="", elem_classes=["output-box"])

    # 绑定事件
    def on_analyze(text):
        result = analyze_real(text)
        return [
            result["主要类别"],
            result["次要类别"],
            result["置信度等级"],
            result["建议操作"],
            result["点位信息"],
            result["关联法条"],
            result["相似案例"],
            result["双引擎判定详情"]
        ]

    analyze_btn.click(
        fn=on_analyze,
        inputs=input_text,
        outputs=[primary_cat, secondary_cat, conf_level, suggestion, location_box, law_box, similar_box, detail_box]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=6009, share=False)