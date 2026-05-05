#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_cases.py - 典型案例库Excel → similar_cases.json
"""

import pandas as pd
import json
import os

def clean_text(text):
    if not text or pd.isna(text):
        return ""
    return str(text).strip()

def convert_cases(excel_path="典型案例库.xlsx", output_dir="data"):
    if not os.path.exists(excel_path):
        print(f"❌ 找不到 {excel_path}")
        return False
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "similar_cases.json")
    
    xls = pd.ExcelFile(excel_path)
    cases_db = {}
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=0)
        if df.empty:
            continue
        
        # 标准化列名
        df.columns = [str(c).strip() for c in df.columns]
        
        # 找线索类型列
        type_col = None
        for col in df.columns:
            if "线索" in col or "类型" in col:
                type_col = col
                break
        
        if not type_col:
            continue
        
        for _, row in df.iterrows():
            cat = clean_text(row.get(type_col, ''))
            if not cat or cat in [type_col, '线索类型']:
                continue
            
            # 基层治理案例暂不纳入涉检匹配（四大检察无关）
            if cat == '基层治理':
                continue
            
            name = clean_text(row.get('案例名称', ''))
            summary = clean_text(row.get('案情摘要', ''))
            laws = clean_text(row.get('对应法条', ''))
            source = clean_text(row.get('来源', ''))
            
            if not name and not summary:
                continue
            
            case_item = {
                "title": name if name else summary[:30] + "...",
                "category": cat,
                "summary": summary,
                "laws": laws,
                "source": source,
                "similarity": 0.0
            }
            
            if cat not in cases_db:
                cases_db[cat] = []
            cases_db[cat].append(case_item)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cases_db, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 转换完成：{output_path}")
    for cat, cases in cases_db.items():
        print(f"  {cat}: {len(cases)}条")
    
    return True

if __name__ == "__main__":
    convert_cases()