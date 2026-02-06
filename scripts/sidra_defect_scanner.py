import sys
import os
import requests
import pandas as pd
import re
from datetime import datetime

# 路径处理，确保能导入 config
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from config.settings_template import GITHUB_TOKEN, SIDRA_CONFIG


class SolidityDefectAnalyzer:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = SIDRA_CONFIG['owner']
        self.repo = SIDRA_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # --- 1. 绝对黑名单 (Veto Keywords) ---
        # 只要标题出现这些，无论正文写什么，直接剔除
        # 针对你的要求：typo, comment, doc, fuzz, test
        self.veto_keywords = [
            r'\btypo\b', r'\bcomment\b', r'\bdoc(s)?\b', r'\bdocumentation\b',
            r'\bfuzz\b', r'\btest(s)?\b', r'\btesting\b', r'\bbenchmark\b',
            r'\bchore\b', r'\blint\b', r'\bstyle\b', r'\bformat\b',
            r'\bci\b', r'\bworkflow\b', r'\bbump\b', r'\bversion\b',
            r'\brelease\b', r'\bmerge\b', r'\bignore\b', r'\bexample\b'
        ]

        # --- 2. Tier 1: 强修复关键词 (High Weight) ---
        # 明确表明这是一个修复动作
        self.tier1_keywords = [
            'fix', 'fixed', 'fixes', 'fixing',
            'patch', 'patched',
            'resolve', 'resolved',
            'bug', 'bugs',
            'vulnerability', 'exploit', 'hack',
            'prevent', 'prevention',  # e.g., prevent reentrancy
            'hotfix', 'critical',
            'restore', 'revert'  # revert changes
        ]

        # --- 3. Tier 2: 缺陷症状与Solidity逻辑 (Medium Weight) ---
        # 描述了问题，或者进行了通常与修复相关的操作
        self.tier2_keywords = [
            'incorrect', 'correct', 'correction',  # 修正
            'wrong', 'fail', 'failure', 'failed', 'error',  # 错误症状
            'crash', 'panic', 'stuck', 'broken',
            'validate', 'validation', 'check', 'require',  # 增加校验通常是为了修Bug
            'gas', 'optimize', 'optimization',  # 智能合约中，Gas优化通常被视为代码改进/修复
            'leak', 'overflow', 'underflow',
            'permission', 'access', 'auth',  # 权限问题
            'modifier', 'event', 'emit'  # 漏写事件或修饰符
        ]

        # --- 4. Tier 3: 弱关键词 (Low Weight - 仅在正文有效) ---
        # 用于在正文中捞回标题写得很烂的PR
        self.tier3_keywords = [
            'issue', 'problem', 'change', 'update', 'modify', 'logic'
        ]

    def fetch_prs(self):
        """分页获取所有已合并PR"""
        print(f"🚀 开始扫描 {self.owner}/{self.repo} ...")
        merged_prs = []
        page = 1

        while True:
            print(f"   正在抓取第 {page} 页 (按更新时间倒序)...")
            params = {
                'state': 'closed',
                'per_page': 100,
                'page': page,
                'sort': 'updated',
                'direction': 'desc'
            }
            try:
                resp = requests.get(f"{self.base_url}/pulls", headers=self.headers, params=params, timeout=15)
                if resp.status_code != 200:
                    print(f"⚠️ API Error: {resp.status_code}")
                    break

                items = resp.json()
                if not items:
                    break

                for item in items:
                    if item.get('merged_at'):  # 只看合并的
                        merged_prs.append(item)

                if len(items) < 100:
                    break
                page += 1
            except Exception as e:
                print(f"❌ 网络错误: {e}")
                break

        print(f"📥 共获取 {len(merged_prs)} 个已合并 PR。开始深度分析...")
        return merged_prs

    def analyze_pr(self, pr):
        """
        核心分析逻辑
        返回: (score, reasons_list, is_vetoed)
        """
        title = pr['title']
        body = pr.get('body', '') or ''
        labels = [l['name'].lower() for l in pr.get('labels', [])]

        title_lower = title.lower()
        body_lower = body.lower()

        score = 0
        reasons = []

        # --- Step 1: 绝对否决 (Veto) ---
        # 检查标题是否包含测试、文档等关键词
        for pattern in self.veto_keywords:
            if re.search(pattern, title_lower):
                return 0, [f"VETO: Title matches {pattern}"], True

        # --- Step 2: 标题分析 (高权重) ---
        # Tier 1: 强修复 (+10分)
        for kw in self.tier1_keywords:
            # 使用单词边界，防止 'prefix' 匹配 'fix'
            if re.search(r'\b' + kw + r'\b', title_lower):
                score += 10
                reasons.append(f"Title(Tier1): {kw}")
                # 命中一个强关键词后，不再重复计算同级关键词，防止刷分
                break

                # Tier 2: 逻辑/症状 (+5分)
        for kw in self.tier2_keywords:
            if re.search(r'\b' + kw + r'\b', title_lower):
                score += 5
                reasons.append(f"Title(Tier2): {kw}")
                break

        # --- Step 3: 正文补救 (Body Fallback) ---
        # 只有当标题分数较低 (<10) 时，我们才去正文里使劲找，避免噪音
        # 正文权重要低，因为正文可能是在引用 issue 描述
        if score < 10:
            body_score = 0
            # 查找 "Fixes #123" 这种强模式 (+5分)
            if re.search(r'(fix|close|resolve)(e?s)?\s+#\d+', body_lower):
                body_score += 5
                reasons.append("Body: References Issue ID")

            # 在正文前500字符内查找 Tier 1 关键词 (权重打折: +2分)
            # 限制前500字符是为了避开 PR 模板底部的无关信息
            intro_body = body_lower[:500]
            for kw in self.tier1_keywords:
                if re.search(r'\b' + kw + r'\b', intro_body):
                    body_score += 2
                    reasons.append(f"Body(Intro): {kw}")
                    break

            score += body_score

        # --- Step 4: 标签加成 (Labels) ---
        # 标签通常是人工确认过的，信度高
        bug_labels = ['bug', 'defect', 'security', 'high', 'critical', 'invalid']
        for label in labels:
            if any(bl in label for bl in bug_labels):
                score += 10
                reasons.append(f"Label: {label}")

        # --- Step 5: Solidity/Sidra 上下文加成 ---
        # 确保我们筛选的是合约代码相关的，而不是脚本
        contract_keywords = [
            'contract', 'token', 'erc20', 'erc721', 'mint', 'burn',
            'transfer', 'wallet', 'sidra', 'chain', 'validator'
        ]
        context_hits = [k for k in contract_keywords if k in title_lower]
        if context_hits and score > 0:
            # 只有在已经判定为疑似Bug的情况下，上下文才加分
            score += 2
            reasons.append(f"Context: {context_hits[0]}")

        return score, reasons, False

    def run(self):
        all_prs = self.fetch_prs()
        candidates = []

        veto_count = 0
        low_score_count = 0

        for pr in all_prs:
            score, reasons, is_vetoed = self.analyze_pr(pr)

            if is_vetoed:
                veto_count += 1
                continue

            # 阈值筛选
            if score >= SIDRA_CONFIG['min_score_threshold']:
                # 简单的置信度分级
                confidence = "High" if score >= 15 else ("Medium" if score >= 10 else "Low")

                candidates.append({
                    'PR Number': pr['number'],
                    'Score': score,
                    'Confidence': confidence,
                    'Title': pr['title'],
                    'Reasons': " | ".join(reasons),
                    'Merged At': pr['merged_at'],
                    'URL': pr['html_url'],
                    'Body Snippet': pr['body'][:100].replace('\n', ' ') if pr['body'] else ""
                })
            else:
                low_score_count += 1

        # 排序：分数高 -> 时间新
        candidates.sort(key=lambda x: (x['Score'], x['Merged At']), reverse=True)

        # 导出
        self.export(candidates, len(all_prs), veto_count, low_score_count)

    def export(self, candidates, total, vetoed, low_score):
        if not candidates:
            print("❌ 未找到符合条件的PR。")
            return

        df = pd.DataFrame(candidates)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sidra_defects_{timestamp}.xlsx"
        output_path = os.path.join(SIDRA_CONFIG['excel_output'], filename)

        # 确保目录存在
        os.makedirs(SIDRA_CONFIG['excel_output'], exist_ok=True)

        df.to_excel(output_path, index=False)

        print("\n" + "=" * 40)
        print(f"📊 筛选报告 - {self.repo}")
        print(f"   - 总PR数: {total}")
        print(f"   - 🚫 否决(测试/文档等): {vetoed}")
        print(f"   - 📉 低分(无关特性等): {low_score}")
        print(f"   - ✅ 最终入选: {len(candidates)}")
        print(f"   - 💾 结果已保存: {output_path}")
        print("=" * 40)
        print("💡 提示：请重点查看 'High' 和 'Medium' 置信度的条目。")
        print("   'Low' 置信度的条目通常是正文中提到了fix，但标题不明确，需人工二次确认。")


if __name__ == "__main__":
    analyzer = SolidityDefectAnalyzer()
    analyzer.run()