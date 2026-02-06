import sys
import os
import requests
import pandas as pd
import re
from datetime import datetime

# 确保引入配置
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings_template import GITHUB_TOKEN, SEAPORT_CONFIG


class SeaportCollector:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = SEAPORT_CONFIG['owner']
        self.repo = SEAPORT_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # 1. 强力黑名单 (噪音词汇) - 只要标题出现这些，直接扔掉
        self.noise_keywords = [
            'typo', 'bump', 'chore', 'doc', 'docs', 'documentation',
            'lint', 'format', 'style', 'ci', 'cd', 'workflow',
            'test', 'tests', 'testing', 'coverage', 'benchmark',
            'refactor', 'rename', 'move', 'clean', 'nit',
            'release', 'version', 'merge', 'ignore', 'license'
        ]

        # 2. 核心修复动词 (必须出现在标题或正文开头)
        self.fix_verbs = [
            'fix', 'fixed', 'fixes', 'fixing',
            'resolve', 'resolved', 'resolves',
            'patch', 'patched',
            'correct', 'correction',
            'prevent', 'avoid', 'handle',  # handle edge case
            'revert', 'restore'
        ]

        # 3. Seaport 核心业务词汇 (用于确认是业务逻辑bug，而不是工具bug)
        self.seaport_context = [
            # 核心逻辑
            'order', 'offer', 'consideration', 'fulfillment', 'match',
            'validate', 'validation', 'status', 'hash', 'eip712',
            'signature', 'digest', 'nonce', 'counter', 'zone',
            'conduit', 'transfer', 'spend', 'amount', 'recipient',
            'criteria', 'root', 'proof', 'merkle',

            # 底层/汇编 (Seaport 特色)
            'assembly', 'yul', 'mstore', 'mload', 'sload', 'sstore',
            'memory', 'calldata', 'stack', 'overflow', 'underflow',
            'revert', 'panic', 'gas', 'limit', 'offset', 'pointer',
            'encode', 'decode', 'mask', 'bit'
        ]

    def collect_all_merged_prs(self):
        """收集所有已合并的PR"""
        print(f"📥 [Seaport] 正在抓取 {self.owner}/{self.repo} ...")

        merged_prs = []
        page = 1

        while True:
            print(f"   正在扫描第 {page} 页...")
            # GitHub API 默认按 created 排序，我们按 updated 倒序，保证拿到最近的状态
            prs = self.make_request(f"{self.base_url}/pulls", {
                'state': 'closed',
                'per_page': 100,
                'page': page,
                'sort': 'updated',
                'direction': 'desc'
            })

            if not prs:
                break

            for pr in prs:
                # 必须是已合并的
                if pr.get('merged_at'):
                    merged_prs.append({
                        'number': pr['number'],
                        'title': pr['title'],
                        'body': pr.get('body', '') or '',
                        'user': pr['user']['login'],
                        'merged_at': pr['merged_at'],
                        'url': pr['html_url'],
                        'labels': [l['name'] for l in pr.get('labels', [])],
                        'additions': pr.get('additions', 0),
                        'deletions': pr.get('deletions', 0),
                        'changed_files': pr.get('changed_files', 0)
                    })

            if len(prs) < 100:
                break
            page += 1

        print(f"✅ 共获取 {len(merged_prs)} 个已合并 PR")
        return merged_prs

    def is_noise(self, pr):
        """判断是否为噪音PR (测试、文档、版本更新、Typo)"""
        title_lower = pr['title'].lower()
        labels = [l.lower() for l in pr['labels']]

        # 1. 检查标题中的黑名单关键词
        # 使用单词边界匹配，避免误杀 (例如 'context' 包含 'test'，但不应被杀)
        for noise in self.noise_keywords:
            # 正则：单词边界 + 关键词
            if re.search(r'\b' + re.escape(noise) + r'\b', title_lower):
                return True, f"Title contains '{noise}'"

        # 2. 检查标签黑名单
        noise_labels = ['documentation', 'dependencies', 'wontfix', 'invalid', 'question', 'duplicate']
        if any(nl in labels for nl in noise_labels):
            return True, "Label filter"

        # 3. 检查Conventional Commits前缀 (如 test: chore: docs:)
        if re.match(r'^(chore|docs|test|ci|build|style|refactor)(\(.*\))?:', title_lower):
            return True, "Conventional commit prefix"

        return False, ""

    def calculate_bug_score(self, pr):
        """
        计算PR是缺陷修复的置信度分数
        返回: (score, reasons_list)
        """
        score = 0
        reasons = []
        title_lower = pr['title'].lower()
        body_lower = pr['body'].lower()

        # --- 规则 1: 标题包含强力修复动词 (权重最高) ---
        # 匹配 "fix bug", "fixes issue", "fix validation" 等
        for verb in self.fix_verbs:
            if re.search(r'\b' + verb + r'\b', title_lower):
                score += 10
                reasons.append(f"Title verb: {verb}")
                break  # 命中一个动词即可

        # --- 规则 2: 标题包含 Seaport 核心上下文 (确保是业务逻辑) ---
        context_hits = []
        for ctx in self.seaport_context:
            if ctx in title_lower:
                context_hits.append(ctx)

        if context_hits:
            # 如果既有 fix 动词，又有上下文，分数暴涨
            if score >= 10:
                score += 5 * len(context_hits)
                reasons.append(f"Context: {','.join(context_hits)}")
            else:
                # 只有上下文没有 fix 动词，可能是功能添加，分数加得少
                score += 1

        # --- 规则 3: 标签筛选 ---
        bug_labels = ['bug', 'security', 'exploit', 'vulnerability', 'high risk', 'critical']
        for label in pr['labels']:
            if any(bl in label.lower() for bl in bug_labels):
                score += 15
                reasons.append(f"Label: {label}")

        # --- 规则 4: 正文引用 Issue (Fixes #123) ---
        # 这种通常是真正的修复
        if re.search(r'(fix|close|resolve)(e?s)?\s+#\d+', body_lower) or re.search(
                r'(fix|close|resolve)(e?s)?\s+https://github.com', body_lower):
            score += 5
            reasons.append("References Issue")

        # --- 规则 5: 纯汇编/Gas优化修复特判 ---
        # Seaport 很多 bug 是 "Fix memory expansion" 这种
        if 'gas' in title_lower and ('fix' in title_lower or 'correct' in title_lower or 'leak' in title_lower):
            score += 8
            reasons.append("Gas/Assembly Fix")

        return score, reasons

    def filter_and_analyze(self, merged_prs):
        """执行筛选和分析"""
        print("🔍 正在进行深度筛选 (剔除 Typo/Test/Chore)...")

        candidates = []
        skipped_count = 0

        for pr in merged_prs:
            # 1. 第一轮：噪音过滤
            is_noise, reason = self.is_noise(pr)
            if is_noise:
                skipped_count += 1
                continue

            # 2. 第二轮：评分
            score, reasons = self.calculate_bug_score(pr)

            # 3. 阈值截断
            # 只有分数 >= 10 的才被认为是“缺陷相关”
            # 这意味着必须在标题中有 fix 动词，或者有 bug 标签
            if score >= 10:
                confidence = 'High' if score >= 20 else 'Medium'

                # 提取具体的 Bug 关键词用于分类
                keywords = [k for k in self.seaport_context if k in pr['title'].lower()]

                candidates.append({
                    'number': pr['number'],
                    'title': pr['title'],
                    'score': score,
                    'confidence': confidence,
                    'reasons': ", ".join(reasons),
                    'keywords': ", ".join(keywords[:5]),
                    'url': pr['url'],
                    'merged_at': pr['merged_at'],
                    'body': pr['body'][:200].replace('\n', ' ') + '...'  # 截取部分正文
                })

        # 按分数倒序排列，分数高的在最前面
        candidates.sort(key=lambda x: x['score'], reverse=True)

        print(f"📉 过滤统计:")
        print(f"   - 原始 PR 数: {len(merged_prs)}")
        print(f"   - 噪音剔除数: {skipped_count} (Typo, Tests, Docs, Bumps)")
        print(f"   - 疑似缺陷数: {len(candidates)}")

        return candidates

    def export_to_excel(self, candidates):
        if not candidates:
            print("❌ 没有找到符合条件的缺陷修复 PR")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(SEAPORT_CONFIG['excel_output'], f"seaport_strict_bugs_{timestamp}.xlsx")

        df = pd.DataFrame(candidates)

        # 重新排序列，把重要的放在前面
        cols = ['number', 'score', 'confidence', 'title', 'keywords', 'reasons', 'url', 'merged_at']
        df = df[cols]

        try:
            df.to_excel(output_path, index=False)
            print(f"✅ 结果已导出: {output_path}")
            print("   (请打开 Excel 查看 Score 较高的条目，Top 20 应该是真正的代码逻辑修复)")
        except Exception as e:
            print(f"❌ 导出失败: {e}")

    def make_request(self, url, params=None):
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 403:
                print("⚠️ API Rate Limit Exceeded")
            return []
        except Exception as e:
            print(f"Error: {e}")
            return []

    def run(self):
        # 1. 获取
        all_prs = self.collect_all_merged_prs()
        # 2. 严格筛选
        bug_prs = self.filter_and_analyze(all_prs)
        # 3. 导出
        self.export_to_excel(bug_prs)


if __name__ == "__main__":
    collector = SeaportCollector()
    collector.run()