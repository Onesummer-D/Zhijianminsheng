#!/usr/bin/env python3
import os
# 使用已设置的环境变量
from api_client import analyze_with_deepseek

result = analyze_with_deepseek("老板拖欠农民工工资半年，在房山区长阳镇")
print("API返回:", result)
print("is_procuratorial:", result.get("is_procuratorial"))
print("category:", result.get("category"))
