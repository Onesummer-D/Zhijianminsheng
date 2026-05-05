import pandas as pd
import json
import os

def infer_categories(row):
    raw_type = str(row.get('线索类型', ''))
    laws = str(row.get('对应法条', ''))
    summary = str(row.get('案情摘要', ''))
    categories = set()
    
    if '公益诉讼' in raw_type:
        categories.add('公益诉讼')
    if '民事支持起诉' in raw_type or (('民事' in raw_type or '支持起诉' in summary) and '公益诉讼' not in raw_type):
        categories.add('民事支持起诉')
    if '行政执法监督' in raw_type or ('行政' in raw_type and '执法' in raw_type):
        categories.add('行政执法监督')
    if '刑事犯罪' in raw_type:
        categories.add('刑事犯罪')
    
    if any(k in laws for k in ['刑法', '第234条', '第260条', '第264条', '第266条', '第271条', '第276条', '第293条', '第307条', '第324条', '第338条', '第343条', '第347条']):
        categories.add('刑事犯罪')
    if any(k in laws for k in ['环境保护法', '第1229条', '第1234条', '第1232条', '第58条', '野生动物保护法', '生态', '修复']):
        categories.add('公益诉讼')
    if any(k in laws for k in ['民事诉讼法', '劳动合同法', '民法典', '第807条', '第579条', '第577条', '第1067条']):
        categories.add('民事支持起诉')
    if any(k in laws for k in ['行政处罚法', '行政诉讼法', '土地管理法', '安全生产法', '第70条', '第72条']):
        categories.add('行政执法监督')
    
    if not categories or raw_type == '跨类别':
        if any(w in summary for w in ['欠薪', '工资', '拖欠', '劳动报酬', '工伤', '赡养', '装修', '预付卡']):
            categories.add('民事支持起诉')
        if any(w in summary for w in ['污染', '环境', '生态', '采矿', '文物', '食品安全', '垃圾']):
            categories.add('公益诉讼')
        if any(w in summary for w in ['罚款', '处罚', '强拆', '不作为', '推诿', '城管', '工伤认定', '免罚']):
            categories.add('行政执法监督')
        if any(w in summary for w in ['盗窃', '诈骗', '故意伤害', '寻衅滋事', '高空抛物', '毒品', '虐待', '走私']):
            categories.add('刑事犯罪')
    
    return list(categories)

def convert():
    excel_path = './典型案例库.xlsx'
    if not os.path.exists(excel_path):
        print(f"❌ 找不到文件: {excel_path}")
        print("请把 典型案例库.xlsx 上传到 ~/zhijianminsheng/ 目录")
        return
    
    df = pd.read_excel(excel_path, sheet_name=0)
    records = []
    
    for _, row in df.iterrows():
        name = str(row.get('案例名称', '')).strip()
        if not name or name == 'nan' or name == '案例名称':
            continue
            
        cats = infer_categories(row)
        if not cats:
            continue
        
        records.append({
            "name": name,
            "categories": cats,
            "summary": str(row.get('案情摘要', '')).strip(),
            "laws": [l.strip() for l in str(row.get('对应法条', '')).split('；') if l.strip()],
            "source": str(row.get('来源', '')).strip()
        })
    
    os.makedirs('data', exist_ok=True)
    with open('data/case_library.json', 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 转换完成：{len(records)}条案例 → data/case_library.json")
    for cat in ['刑事犯罪', '公益诉讼', '民事支持起诉', '行政执法监督']:
        cnt = sum(1 for r in records if cat in r['categories'])
        print(f"   {cat}: {cnt}条")

if __name__ == '__main__':
    convert()