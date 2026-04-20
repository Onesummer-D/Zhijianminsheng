#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_excel.py - 自动清理关键词库里的危险排除词
用法：python clean_excel.py
"""

import pandas as pd

# 定义需要删除的【危险排除词】（会误杀真实案件）
DANGEROUS_WORDS = {
    # 第一人称（必须删，会杀掉所有真实工单）
    "我", "我们", "本人", "来电人", "我是", "我在", "我的", "我自己",
    
    # 情绪表达（弱势群体讨薪/家暴常用语）
    "心里", "想死的心都有", "心里滴血", "精神崩溃", "心态炸了", "心在流血", 
    "灵魂被掏空", "精神被绑架", "被生活强奸", "被社会毒打", "被现实暴击",
    
    # 时间跨度（环境污染/职务犯罪常有）
    "二十年前", "三十年前", "小时候", "当年", "那时候", "老一辈", 
    "早就去世了", "历史遗留", "陈年旧事",
    
    # 司法程序词（如果存在，会杀掉检察监督案源）
    "已经起诉到法院了", "行政诉讼立案了", "等开庭", "二审中", "再审申请了", 
    "申请执行了", "执行局在办", "复议中", "信访答复了"
}

def clean_excluded_words(cell_value):
    """清理单元格里的危险排除词"""
    if pd.isna(cell_value) or str(cell_value).strip() == '':
        return ''
    
    # 统一分隔符，分割成列表
    text = str(cell_value)
    text = text.replace('，', '、').replace(',', '、').replace('\n', '、')
    words = [w.strip() for w in text.split('、') if w.strip()]
    
    # 过滤掉危险词
    cleaned = [w for w in words if w not in DANGEROUS_WORDS]
    
    # 重新用顿号连接
    return '、'.join(cleaned)

def main():
    excel_path = "关键词库.xlsx"
    
    print(f"🧹 开始清理 {excel_path} 中的危险排除词...")
    
    # 读取Excel
    df = pd.read_excel(excel_path, header=0)
    df.columns = [str(col).strip() for col in df.columns]
    
    # 找到排除词列（兼容可能的列名）
    exclude_col = None
    for col in df.columns:
        if '排除' in col or '降噪' in col:
            exclude_col = col
            break
    
    if not exclude_col:
        print("❌ 未找到排除词列（列名需包含'排除'或'降噪'）")
        return
    
    print(f"✅ 找到排除词列：{exclude_col}")
    
    # 统计清理前
    total_before = 0
    for cell in df[exclude_col]:
        if pd.notna(cell):
            total_before += len(str(cell).split('、'))
    
    # 清理每一行
    df[exclude_col] = df[exclude_col].apply(clean_excluded_words)
    
    # 统计清理后
    total_after = 0
    for cell in df[exclude_col]:
        if pd.notna(cell):
            total_after += len(str(cell).split('、')) if str(cell) else 0
    
    deleted = total_before - total_after
    
    # 保存回Excel（覆盖原文件，先备份）
    import shutil
    backup_path = excel_path.replace('.xlsx', '_backup.xlsx')
    shutil.copy(excel_path, backup_path)
    print(f"💾 已备份原文件到：{backup_path}")
    
    df.to_excel(excel_path, index=False)
    
    print(f"✅ 清理完成！")
    print(f"   原排除词总数：{total_before}")
    print(f"   删除危险词：{deleted} 个")
    print(f"   剩余排除词：{total_after} 个")
    print(f"\n🔄 接下来运行：python convert_excel.py")

if __name__ == "__main__":
    main()