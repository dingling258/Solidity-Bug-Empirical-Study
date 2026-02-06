import sys
import os
import requests
import pandas as pd
import re
from datetime import datetime

# 路径处理：确保能导入 config
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from config.settings_template import GITHUB_TOKEN, THIRDWEB_CONFIG


class ThirdwebDefectAnalyzer:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = THIRDWEB_CONFIG['owner']
        self.repo = THIRDWEB_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # --- 1. 绝对黑名单 (Veto Keywords) ---
        # Thirdweb 仓库中包含大量示例和测试代码，需严格过滤
        self.veto_keywords = [
            r'\btypo\b', r'\bcomment\b', r'\bdoc(s)?\b', r'\bdocumentation\b',
            r'\bfuzz\b', r'\btest(s)?\b', r'\btesting\b', r'\bbenchmark\b',
            r'\bchore\b', r'\blint\b', r'\bstyle\b', r'\bformat\b',
            r'\bci\b', r'\bworkflow\b', r'\bbump\b', r'\bversion\b',
            r'\brelease\b', r'\bmerge\b', r'\bexample\b', r'\bsample\b',
            r'\blicense\b', r'\breadme\b', r'\bmakefile\b', r'\bscript\b'
        ]

        # --- 2. Tier 1: 强修复关键词 (标题 - 高权重 +10) ---
        self.tier1_keywords = [
            'fix', 'fixed', 'fixes', 'fixing',
            'patch', 'patched',
            'resolve', 'resolved',
            'bug', 'bugs',
            'vulnerability', 'exploit', 'hack',
            'prevent', 'prevention',
            'hotfix', 'critical',
            'restore', 'revert'
        ]

        # --- 3. Tier 2: 缺陷症状与合约逻辑 (标题 - 中权重 +5) ---
        self.tier2_keywords = [
            'incorrect', 'correct', 'correction',
            'wrong', 'fail', 'failure', 'failed', 'error',
            'crash', 'panic', 'stuck', 'broken',
            'validate', 'validation', 'check', 'require', 'assert',
            'gas', 'optimize', 'optimization',  # Gas 优化
            'leak', 'overflow', 'underflow',
            'permission', 'access', 'auth', 'role',  # 权限控制
            'modifier', 'event', 'emit',
            'unsafe', 'unchecked', 'reentrancy'
        ]

        # --- 4. Tier 3: 弱关键词 (正文 - 低权重 +2) ---
        self.tier3_keywords = [
            'issue', 'problem', 'change', 'update', 'modify', 'logic', 'address'
        ]

        # --- 5. Thirdweb 上下文关键词 (微量加分 +2) ---
        # 针对 Thirdweb 的特有功能模块
        self.context_keywords = [
            # 核心架构
            'factory', 'registry', 'router', 'platform', 'extension', 'plugin',
            'proxy', 'implementation', 'upgrade', 'clone',
            # 业务功能
            'drop', 'marketplace', 'edition', 'pack', 'split', 'vote', 'multiwrap',
            'token', 'nft', 'erc721', 'erc1155', 'erc20',
            # 具体机制
            'claim', 'mint', 'signature', 'sig', 'lazy', 'reveal', 'metadata',
            'royalty', 'royalties', 'primary', 'secondary', 'sale',
            'merkle', 'proof', 'allowlist', 'snapshot'
        ]

    def fetch_all_merged_prs(self):
        """获取所有已合并PR"""
        print(f"🚀 开始扫描 {self.owner}/{self.repo} ...")
        all_merged_prs = []
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
                resp = requests.get(f"{self.base_url}/pulls", headers=self.headers, params=params, timeout=30)
                if resp.status_code != 200:
                    print(f"⚠️ API Error: {resp.status_code}")
                    break

                items = resp.json()
                if not items:
                    break

                for item in items:
                    if item.get('merged_at'):  # 只保留已合并的
                        pr_data = {
                            'number': item['number'],
                            'title': item['title'],
                            'body': item.get('body', '') or '',
                            'state': item['state'],
                            'merged_at': item['merged_at'],
                            'created_at': item['created_at'],
                            'user': item['user']['login'],
                            'url': item['html_url'],
                            'labels': [l['name'] for l in item.get('labels', [])]
                        }
                        all_merged_prs.append(pr_data)

                if len(items) < 100:
                    break
                page += 1
            except Exception as e:
                print(f"❌ 网络错误: {e}")
                break

        print(f"📥 共获取 {len(all_merged_prs)} 个已合并 PR。")
        return all_merged_prs

    def analyze_pr(self, pr):
        """
        核心筛选逻辑：分层加权
        """
        title = pr['title']
        body = pr['body']
        labels = [l.lower() for l in pr['labels']]

        title_lower = title.lower()
        body_lower = body.lower()

        score = 0
        reasons = []

        # --- Step 1: 绝对否决 (Veto) ---
        for pattern in self.veto_keywords:
            if re.search(pattern, title_lower):
                return 0, [f"VETO: Title matches {pattern}"], True

        # --- Step 2: 标题分析 (高权重) ---
        # Tier 1: 强修复 (+10)
        for kw in self.tier1_keywords:
            if re.search(r'\b' + kw + r'\b', title_lower):
                score += 10
                reasons.append(f"Title(Tier1): {kw}")
                break

                # Tier 2: 逻辑/症状 (+5)
        for kw in self.tier2_keywords:
            if re.search(r'\b' + kw + r'\b', title_lower):
                score += 5
                reasons.append(f"Title(Tier2): {kw}")
                break

        # --- Step 3: 正文补救 (Body Fallback) ---
        # 仅当标题分数不足 10 分时启用
        if score < 10:
            # 查找 Issue 引用 (+5)
            if re.search(r'(fix|close|resolve)(e?s)?\s+#\d+', body_lower):
                score += 5
                reasons.append("Body: References Issue ID")

            # 正文前500字符查找强关键词 (+2)
            intro_body = body_lower[:500]
            for kw in self.tier1_keywords:
                if re.search(r'\b' + kw + r'\b', intro_body):
                    score += 2
                    reasons.append(f"Body(Intro): {kw}")
                    break

        # --- Step 4: 标签加成 (Labels) ---
        bug_labels = ['bug', 'defect', 'security', 'high', 'critical', 'invalid']
        for label in labels:
            if any(bl in label for bl in bug_labels):
                score += 10
                reasons.append(f"Label: {label}")

        # --- Step 5: 上下文加成 (Context) ---
        # 仅在已有基础分(>0)的情况下加分，确认修改发生在核心业务逻辑中
        context_hits = [k for k in self.context_keywords if k in title_lower]
        if context_hits and score > 0:
            score += 2
            reasons.append(f"Context: {context_hits[0]}")

        return score, reasons, False

    def run(self):
        # 1. 获取数据
        all_prs = self.fetch_all_merged_prs()

        defect_candidates = []
        veto_count = 0
        low_score_count = 0

        # 2. 分析
        print("🕵️ 正在应用加权筛选逻辑...")
        for pr in all_prs:
            score, reasons, is_vetoed = self.analyze_pr(pr)

            # 记录分析结果到原始对象
            pr['analysis_score'] = score
            pr['analysis_reasons'] = " | ".join(reasons)
            pr['is_vetoed'] = is_vetoed

            if is_vetoed:
                veto_count += 1
                continue

            if score >= THIRDWEB_CONFIG['min_score_threshold']:
                confidence = "High" if score >= 15 else ("Medium" if score >= 10 else "Low")

                candidate = {
                    'PR Number': pr['number'],
                    'Score': score,
                    'Confidence': confidence,
                    'Title': pr['title'],
                    'Reasons': pr['analysis_reasons'],
                    'Merged At': pr['merged_at'],
                    'URL': pr['url'],
                    'User': pr['user'],
                    'Body Snippet': pr['body'][:200].replace('\n', ' ')
                }
                defect_candidates.append(candidate)
            else:
                low_score_count += 1

        # 排序：分数高在前，时间新在前
        defect_candidates.sort(key=lambda x: (x['Score'], x['Merged At']), reverse=True)

        # 3. 导出
        self.export(all_prs, defect_candidates, veto_count, low_score_count)

    def export(self, all_prs, candidates, vetoed, low_score):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"thirdweb_defects_{timestamp}.xlsx"
        output_path = os.path.join(THIRDWEB_CONFIG['excel_output'], filename)

        os.makedirs(THIRDWEB_CONFIG['excel_output'], exist_ok=True)

        print(f"💾 正在导出 Excel 到 {output_path} ...")

        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Sheet 1: 缺陷候选
                if candidates:
                    df_candidates = pd.DataFrame(candidates)
                    df_candidates.to_excel(writer, sheet_name='Defect_Candidates', index=False)
                else:
                    pd.DataFrame(["无符合条件的PR"]).to_excel(writer, sheet_name='Defect_Candidates')

                # Sheet 2: 所有已合并PR
                df_all = pd.DataFrame(all_prs)
                cols = ['number', 'title', 'analysis_score', 'is_vetoed', 'merged_at', 'user', 'url', 'labels',
                        'analysis_reasons']
                existing_cols = [c for c in cols if c in df_all.columns]
                df_all = df_all[existing_cols]
                df_all.to_excel(writer, sheet_name='All_Merged_PRs', index=False)

                # Sheet 3: 统计
                stats_data = [
                    ['项目', 'thirdweb-dev/contracts'],
                    ['总已合并PR', len(all_prs)],
                    ['🚫 被否决 (Test/Doc/Example)', vetoed],
                    ['📉 低分 (Feature/Refactor)', low_score],
                    ['✅ 疑似缺陷 (Candidates)', len(candidates)],
                    ['筛选阈值', THIRDWEB_CONFIG['min_score_threshold']]
                ]
                pd.DataFrame(stats_data, columns=['Metric', 'Value']).to_excel(writer, sheet_name='Statistics',
                                                                               index=False)

            print("✅ 导出完成！")
            print(f"   - 缺陷候选: {len(candidates)} 条")
            print(f"   - 全量PR: {len(all_prs)} 条")

        except Exception as e:
            print(f"❌ 导出失败: {e}")


if __name__ == "__main__":
    analyzer = ThirdwebDefectAnalyzer()
    analyzer.run()