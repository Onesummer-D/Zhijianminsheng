# 智检民声 —— 12345涉检线索智能筛查系统

[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Gradio](https://img.shields.io/badge/Gradio-5.x-orange.svg)](https://gradio.app/)

---

## 项目背景与技术挑战

12345政务服务热线包含大量非结构化自然语言投诉文本，由于用户表达具有口语化、多义性和场景复杂等特点，传统关键词匹配方法容易产生误报与漏报。

本项目关注三个核心技术挑战：

1. 如何在有限计算资源下实现高准确率文本分类；
2. 如何保证AI决策结果的可解释性，使业务人员理解分类依据；
3. 如何融合规则知识与大模型语义能力，避免LLM幻觉影响业务判断。

---

## 系统演示

### Gradio首页界面

<img src="./assets/demo_main.png" width="800">

### 单条查询筛查结果展示

<img src="./assets/demo_result.png" width="800">

<img src="./assets/demo_result1.png" width="800">

<img src="./assets/demo_result2.png" width="800">

### 批量筛查与结果导出

<img src="./assets/demo_batch.png" width="800">

<img src="./assets/demo_batch1.png" width="800">

<img src="./assets/demo_batch2.png" width="800">

---

## 核心功能

| 功能模块 | 说明 |
|---------|------|
| 单条查询 | 输入单条 12345 工单，实时返回类别、置信度、法条、相似案例、点位、要素提取 |
| 批量筛查 | 上传 Excel 批量分析，支持进度条、导出结果、筛查台账 |
| 法条关联 | 自动匹配《刑法》《民法典》《行政诉讼法》等相关法条 |
| 点位识别 | 多层清洗正则提取"区-镇-村"地址结构 |
| 相似案例 | TF-IDF + Min-Max 归一化，返回 60%-100% 相似度案例 |
| 数据脱敏 | 自动遮蔽姓名、手机号、身份证号、银行卡号、门牌号 |
| 审计日志 | 每次查询自动记录，支持后续溯源分析 |

---

## 技术架构

<img src="./assets/architecture1.png" width="800">

<img src="./assets/architecture2.png" width="800">

---
## 核心设计与技术决策

### 1. “规则引擎 + LLM语义复核”的双引擎架构

考虑到12345工单分类具有明确业务规则，同时存在大量模糊表达，本项目没有直接采用端到端LLM分类，而设计：

- 规则引擎负责高置信度快速筛查；

- LLM负责复杂语义理解与边界案例（中低置信度样本）复核。

该设计在保证准确率的同时降低API调用成本。

### 2. 可解释规则体系设计

传统深度模型虽然具有较强语义能力，但难以解释分类原因。因此设计“双层级权重计分+排除词保护门”机制：

- 核心定性词 (+3)

- 特征词 (+1)

- 排除词触发软过滤

使系统能够输出：“为什么判断为该类别”。

---

## 快速开始

### 1. 环境要求

- Python 3.8+
- pip

### 2. 安装依赖

```bash
pip install gradio pandas openpyxl jieba scikit-learn requests
```

### 3. 配置 API Key

```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

### 4. 启动服务

```bash
python app.py
```

---

## 项目目录

```
zhijianminsheng/
├── app.py                      
├── single_query_v2.py          
├── extract_elements.py         
├── rule_engine_keywords.py     
├── api_client.py               
├── case_rag.py                 
├── similarity_matcher.py      
├── convert_excel.py           
├── data/
│   └── legal_basis_v2.json     
├── 关键词库.xlsx                
├── 典型案例库.xlsx              
├── 法条关联表 完整版.xlsx        
└── logs/                       
```

---

## 核心算法说明

### 1. 双层级权重计分算法

| 层级 | 权重 | 示例 |
|------|------|------|
| 核心定性词 | +3 | "挪用资金""恶意欠薪""偷排污水" |
| 特征词 | +1 | "拖欠工资""罚款太重""垃圾倾倒" |

**置信度分级**：>=6 分（高）、3-5 分（中）、<3 分（低）

### 2. 融合决策策略

```
if 规则引擎高分（>=6 且分差>=3）:
    直接返回规则结果
elif 规则引擎中低分或存在交叉:
    调用 DeepSeek API 语义增强
else:
    判定为普通投诉（排除词保护门阻断API）
```

---

## 模型失效分析与改进

测试过程中发现部分情况下LLM语义复核会覆盖规则引擎已经正确判断的结果。例如：

规则引擎：
> 高置信度判断为公益诉讼

LLM：
> 根据上下文误判为普通投诉

针对该问题，设计冲突仲裁机制：当规则结果与LLM结果不一致时，不直接覆盖，而标记样本为“类别冲突”，进入人工复核流程。该分析推动系统从简单调用LLM向可信AI方向优化。

---

## 开源协议

MIT License
