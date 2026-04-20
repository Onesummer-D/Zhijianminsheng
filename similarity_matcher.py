#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
similarity_matcher.py - TF-IDF + 余弦相似度案例匹配引擎
采用Min-Max归一化：将本次查询的原始余弦相似度映射到60%-100%展示区间
"""

import json
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class CaseSimilarityMatcher:
    def __init__(self, json_path="./data/similar_cases.json"):
        self.cases_db = {}
        self.vectorizers = {}
        self.tfidf_matrices = {}
        self._loaded = False
        
        if os.path.exists(json_path):
            self.load(json_path)
    
    def load(self, json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.cases_db = json.load(f)
        
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
            tfidf_matrix = vectorizer.fit_transform(texts)
            self.vectorizers[cat] = vectorizer
            self.tfidf_matrices[cat] = tfidf_matrix
            
        self._loaded = True
        total = sum(len(v) for v in self.cases_db.values())
        print(f"✅ 案例库加载完成：{len(self.cases_db)}个类别，共{total}条案例")
    
    def match(self, text, category, top_k=3):
        """为指定类别找最相似的案例"""
        if not self._loaded:
            return None, []
        
        # 主类别匹配
        best, others = self._match_in_category(text, category, top_k)
        
        # 如果主类别没匹配到，尝试跨类别案例库
        if not best and category in ["公益诉讼", "民事支持起诉", "行政执法监督", "刑事犯罪"]:
            if "跨类别" in self.cases_db:
                best, others = self._match_in_category(text, "跨类别", top_k)
        
        # 【Min-Max归一化】将本次查询的原始余弦相似度映射到60%-100%
        all_results = []
        if best:
            all_results.append(best)
        all_results.extend(others)
        
        if all_results:
            raw_scores = [r["similarity"] for r in all_results]
            min_score = min(raw_scores)
            max_score = max(raw_scores)
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
        """案例太少时的fallback：基于字符重叠率"""
        text_set = set(text.lower())
        scores = []
        for c in cases:
            s = c.get("summary", "") + " " + c.get("title", "")
            s_set = set(s.lower())
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
