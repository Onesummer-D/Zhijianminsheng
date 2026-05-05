#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
similarity_matcher.py - TF-IDF + 余弦相似度案例匹配引擎
修复：1.支持case_library.json格式 2.加匹配阈值 3.fallback去停用词
"""

import json
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 中文停用字符（fallback过滤用）
STOP_CHARS = set("我们他们的这个那个一个没有就是但是然后因为所以希望政府帮忙反映举报投诉问题情况事情时候现在已经一直多次怎么办怎么处理能不能可以吗房山区北京北京市街道镇村小区社区居民群众来电人反映人投诉人举报人本人自己家里家中附近周围旁边里面外面上面下面有人发现看到听说知道认为觉得非常特别十分很太都也还就才又再给被让把对向从在到为和与或及等的了是有在我他她它你这那什么怎么为什么哪里谁多少")

class CaseSimilarityMatcher:
    def __init__(self, json_path="./data/case_library.json"):
        self.cases_db = {}
        self.vectorizers = {}
        self.tfidf_matrices = {}
        self._loaded = False
        
        if os.path.exists(json_path):
            self.load(json_path)
    
    def load(self, json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # 【修复】兼容两种格式：数组格式(case_library.json) 和 字典格式(similar_cases.json)
        if isinstance(raw_data, list):
            # case_library.json 格式：按 categories 分组
            for case in raw_data:
                cats = case.get("categories", [])
                for cat in cats:
                    if cat not in self.cases_db:
                        self.cases_db[cat] = []
                    # 统一字段名：name->title
                    normalized = {
                        "title": case.get("name", "未知"),
                        "summary": case.get("summary", ""),
                        "laws": case.get("laws", ["—"])
                    }
                    self.cases_db[cat].append(normalized)
        else:
            # similar_cases.json 格式（原格式）
            self.cases_db = raw_data
        
        for cat, cases in self.cases_db.items():
            if len(cases) < 2:
                continue
            
            texts = [c.get("summary", "") + " " + c.get("title", "") for c in cases]
            
            import jieba
            def jieba_tokenizer(text):
                return list(jieba.cut(text))
            
            vectorizer = TfidfVectorizer(
                tokenizer=jieba_tokenizer,
                preprocessor=lambda x: x.lower(),
                max_features=5000,
                ngram_range=(1, 2),
                min_df=1,
                stop_words=None
            )
            try:
                tfidf_matrix = vectorizer.fit_transform(texts)
                self.vectorizers[cat] = vectorizer
                self.tfidf_matrices[cat] = tfidf_matrix
            except Exception as e:
                print(f"⚠️ {cat} 类别TF-IDF构建失败: {e}")
            
        self._loaded = True
        total = sum(len(v) for v in self.cases_db.values())
        print(f"✅ 案例库加载完成：{len(self.cases_db)}个类别，共{total}条案例")
    
    def match(self, text, category, top_k=3):
        """为指定类别找最相似的案例"""
        if not self._loaded:
            return None, []
        
        best, others = self._match_in_category(text, category, top_k)
        
        if not best and category in ["公益诉讼", "民事支持起诉", "行政执法监督", "刑事犯罪"]:
            if "跨类别" in self.cases_db:
                best, others = self._match_in_category(text, "跨类别", top_k)
        
        # 【关键修复】Min-Max归一化 + 质量阈值
        all_results = []
        if best:
            all_results.append(best)
        all_results.extend(others)
        
        if all_results:
            raw_scores = [r["similarity"] for r in all_results]
            max_score = max(raw_scores)
            
            # 【关键】如果最高分低于0.15，说明匹配质量太差，直接不返回
            if max_score < 0.15:
                return None, []
            
            min_score = min(raw_scores)
            score_range = max_score - min_score if max_score > min_score else 0.0
            
            for r in all_results:
                if score_range > 0:
                    mapped = 60 + (r["similarity"] - min_score) / score_range * 40
                else:
                    mapped = 90.0
                r["similarity"] = int(mapped)
        
        return best, others
    
    def _match_in_category(self, text, category, top_k):
        cases = self.cases_db.get(category, [])
        if not cases:
            return None, []
        
        if category not in self.vectorizers:
            return self._fallback_match(text, cases, top_k)
        
        vectorizer = self.vectorizers[category]
        tfidf_matrix = self.tfidf_matrices[category]
        
        input_vec = vectorizer.transform([text])
        similarities = cosine_similarity(input_vec, tfidf_matrix).flatten()
        
        top_indices = similarities.argsort()[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] <= 0.01:
                continue
            case_copy = dict(cases[idx])
            case_copy["similarity"] = float(similarities[idx])
            results.append(case_copy)
        
        if not results:
            return None, []
        
        best = results[0]
        others = results[1:] if len(results) > 1 else []
        return best, others
    
    def _fallback_match(self, text, cases, top_k):
        """案例太少时的fallback：基于字符重叠率（去停用词版）"""
        # 过滤停用字符
        text_set = set(text.lower()) - STOP_CHARS
        
        scores = []
        for c in cases:
            s = c.get("summary", "") + " " + c.get("title", "")
            s_set = set(s.lower()) - STOP_CHARS
            if not s_set:
                scores.append(0)
                continue
            inter = len(text_set & s_set)
            union = len(text_set | s_set)
            scores.append(inter / union if union > 0 else 0)
        
        scores = np.array(scores)
        top_indices = scores.argsort()[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] <= 0.01:
                continue
            case_copy = dict(cases[idx])
            case_copy["similarity"] = float(scores[idx])
            results.append(case_copy)
        
        if not results:
            return None, []
        
        best = results[0]
        others = results[1:] if len(results) > 1 else []
        return best, others

if __name__ == "__main__":
    matcher = CaseSimilarityMatcher()
    text = "我是农民工，老板拖欠工资半年了"
    best, others = matcher.match(text, "民事支持起诉", top_k=3)
    if best:
        print(f"Best: {best['title']} (匹配度: {best['similarity']}%)")
    for o in others:
        print(f"  Other: {o['title']} (匹配度: {o['similarity']}%)")