import sys
import os

# 确保可以导入上级目录的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import pandas as pd
import json
import re
from datetime import datetime
# 引入新增的 SOLMATE_CONFIG
from config.settings_template import GITHUB_TOKEN, SOLMATE_CONFIG


class SolmateCollector:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = SOLMATE_CONFIG['owner']
        self.repo = SOLMATE_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # 1. 通用 Bug 关键词 (保持不变)
        self.general_bug_keywords = [
            'bug', 'fix', 'repair', 'defect', 'vulnerability', 'issue',
            'error', 'problem', 'incorrect', 'wrong', 'fail', 'crash',
            'security', 'exploit', 'attack', 'overflow', 'underflow',
            'reentrancy', 'gas', 'optimization', 'revert', 'panic'
        ]

        # 2. Solmate 特定关键词 (针对 Gas 优化库定制)
        self.solmate_keywords = [
            # 核心数学库
            'math', 'fixedpoint', 'wad', 'ray', 'mulwad', 'divwad',
            'unsafe', 'overflow', 'underflow', 'rounding', 'precision',
            'signed', 'unsigned', 'arithmetic', 'sqrt', 'rpow',

            # Token 标准实现
            'erc20', 'erc721', 'erc1155', 'erc4626', 'vault', 'asset',
            'share', 'deposit', 'withdraw', 'mint', 'redeem', 'permit',
            'approval', 'allowance', 'transfer', 'safetransfer',

            # 认证与安全
            'auth', 'owned', 'authority', 'role', 'permission', 'access',
            'reentrancyguard', 'lock', 'modifier', 'owner',

            # 工具库
            'utils', 'libstring', 'sstore2', 'merkleproof', 'signature',
            'ecdsa', 'create3', 'bytes32', 'string', 'address',

            # 底层优化与汇编 (Solmate 的核心特征)
            'assembly', 'yul', 'mload', 'mstore', 'sload', 'sstore',
            'calldataload', 'delegatecall', 'staticcall', 'inline',
            'unchecked', 'gas', 'limit', 'memory', 'storage', 'slot'
        ]

        # 合并所有关键词
        self.bug_keywords = self.general_bug_keywords + self.solmate_keywords
        self.merged_prs = []

    def collect_all_merged_prs(self):
        """收集所有已合并的PR"""
        print("📥 正在收集 Solmate 所有已合并的PR...")
        print(f"🔗 仓库: {self.owner}/{self.repo}")

        merged_prs = []
        page = 1
        total_collected = 0

        while True:
            print(f"   正在获取第 {page} 页...")

            prs = self.make_request(f"{self.base_url}/pulls", {
                'state': 'closed',
                'per_page': 100,
                'page': page,
                'sort': 'updated',
                'direction': 'desc'
            })

            if not prs:
                break

            page_merged_count = 0
            for pr in prs:
                if pr.get('merged_at') is not None:
                    merged_prs.append({
                        'project_name': 'Solmate',
                        'project_type': 'Library',
                        'project_domain': 'Gas Optimized Solidity Library',
                        'number': pr['number'],
                        'title': pr['title'],
                        'body': pr.get('body', '') or '',
                        'state': pr['state'],
                        'merged_at': pr['merged_at'],
                        'created_at': pr['created_at'],
                        'user': pr['user']['login'],
                        'url': pr['html_url'],
                        'labels': [label['name'] for label in pr.get('labels', [])],
                        'commits': pr.get('commits', 0),
                        'additions': pr.get('additions', 0),
                        'deletions': pr.get('deletions', 0),
                        'changed_files': pr.get('changed_files', 0),
                        'assignees': [assignee['login'] for assignee in pr.get('assignees', [])],
                        'milestone': pr.get('milestone', {}).get('title', '') if pr.get('milestone') else '',
                    })
                    page_merged_count += 1

            total_collected += page_merged_count
            print(f"   第 {page} 页找到 {page_merged_count} 个合并的PR (总计: {total_collected})")

            if page_merged_count == 0:
                break
            page += 1

        print(f"✅ 总共收集到 {len(merged_prs)} 个已合并的PR")
        return merged_prs

    def analyze_merged_prs(self, merged_prs):
        """分析已合并的PR"""
        print("📊 分析 Solmate 已合并的PR...")

        total_prs = len(merged_prs)
        dates = [pr['merged_at'][:10] for pr in merged_prs]
        date_counts = pd.Series(dates).value_counts().sort_index()
        users = [pr['user'] for pr in merged_prs]
        user_counts = pd.Series(users).value_counts()

        all_labels = []
        for pr in merged_prs:
            all_labels.extend(pr['labels'])
        label_counts = pd.Series(all_labels).value_counts()

        total_additions = sum(pr['additions'] for pr in merged_prs)
        total_deletions = sum(pr['deletions'] for pr in merged_prs)
        total_files = sum(pr['changed_files'] for pr in merged_prs)

        # Solmate 特定领域分类
        math_keywords = ['math', 'fixedpoint', 'wad', 'ray', 'overflow', 'rounding']
        token_keywords = ['erc20', 'erc721', 'erc1155', 'erc4626', 'transfer', 'approval']
        auth_keywords = ['auth', 'owned', 'authority', 'permission']
        gas_keywords = ['gas', 'assembly', 'yul', 'optimize', 'unchecked', 'inline']
        utils_keywords = ['utils', 'libstring', 'merkle', 'signature', 'create3']

        math_prs = [pr for pr in merged_prs if
                    any(k in pr['title'].lower() or k in pr['body'].lower() for k in math_keywords)]
        token_prs = [pr for pr in merged_prs if
                     any(k in pr['title'].lower() or k in pr['body'].lower() for k in token_keywords)]
        auth_prs = [pr for pr in merged_prs if
                    any(k in pr['title'].lower() or k in pr['body'].lower() for k in auth_keywords)]
        gas_prs = [pr for pr in merged_prs if
                   any(k in pr['title'].lower() or k in pr['body'].lower() for k in gas_keywords)]
        utils_prs = [pr for pr in merged_prs if
                     any(k in pr['title'].lower() or k in pr['body'].lower() for k in utils_keywords)]

        print(f"📈 Solmate 统计结果:")
        print(f"   - 总合并PR数: {total_prs}")
        print(f"   - 数学库相关: {len(math_prs)}")
        print(f"   - Token标准相关: {len(token_prs)}")
        print(f"   - Auth/安全相关: {len(auth_prs)}")
        print(f"   - Gas/汇编优化相关: {len(gas_prs)}")
        print(f"   - 工具库相关: {len(utils_prs)}")
        print(f"   - 最活跃贡献者: {user_counts.head(1).index[0] if not user_counts.empty else 'N/A'}")

        return {
            'total_prs': total_prs,
            'math_prs': len(math_prs),
            'token_prs': len(token_prs),
            'auth_prs': len(auth_prs),
            'gas_prs': len(gas_prs),
            'utils_prs': len(utils_prs),
            'date_counts': date_counts,
            'user_counts': user_counts,
            'label_counts': label_counts,
            'code_stats': {'additions': total_additions, 'deletions': total_deletions, 'files': total_files}
        }

    def identify_bug_fix_prs(self, merged_prs):
        """识别 Bug 修复 PR (针对 Solmate 定制)"""
        print("🔍 识别 Solmate bug 修复相关的 PR...")

        bug_candidates = []

        for pr in merged_prs:
            title_lower = pr['title'].lower()
            body_lower = pr['body'].lower()
            labels_lower = [label.lower() for label in pr['labels']]
            title_body_text = title_lower + ' ' + body_lower

            # 1. 基础匹配
            general_keyword_matches = [kw for kw in self.general_bug_keywords if kw in title_body_text]
            solmate_keyword_matches = [kw for kw in self.solmate_keywords if kw in title_body_text]

            bug_labels = ['bug', 'defect', 'security', 'vulnerability', 'fix', 'hotfix', 'patch']
            label_matches = [label for label in labels_lower if any(bug_label in label for bug_label in bug_labels)]

            # 2. Fix 引用模式
            fix_patterns = [
                r'fix(?:es)?\s*#?\d+', r'resolv(?:es)?\s*#?\d+', r'clos(?:es)?\s*#?\d+',
                r'fix(?:es)?\s+\w+', r'patch(?:es)?\s+\w+'
            ]
            fix_references = []
            for pattern in fix_patterns:
                fix_references.extend(re.findall(pattern, title_body_text))

            # 3. Solmate 特定 Bug 模式 (重点关注数学和汇编)
            solmate_bug_patterns = [
                # 数学与溢出
                r'overflow.*(?:check|fix|bug|math|calc)',
                r'underflow.*(?:check|fix|bug|math)',
                r'rounding.*(?:error|bug|fix|direction|precision)',
                r'div.*(?:zero|bug|fix|revert)',
                r'mul.*(?:overflow|bug|fix)',
                r'unsafe.*(?:math|cast|conversion)',

                # 汇编与内存
                r'assembly.*(?:bug|fix|memory|storage|stack)',
                r'mstore.*(?:overwrite|bug|fix|offset)',
                r'memory.*(?:corruption|leak|bug|fix|overlap)',
                r'slot.*(?:collision|bug|fix|overwrite)',

                # ERC 标准合规性
                r'erc20.*(?:compliance|bug|fix|transfer|approve)',
                r'erc4626.*(?:rounding|preview|convert|bug|fix)',
                r'permit.*(?:signature|replay|bug|fix|deadline)',
                r'safe.*transfer.*(?:fail|revert|bug|fix|return)',

                # 认证与安全
                r'auth.*(?:bypass|bug|fix|check|owner)',
                r'reentrancy.*(?:bug|fix|guard|attack)',
                r'signature.*(?:invalid|replay|bug|fix|validation)'
            ]

            solmate_bug_matches = []
            for pattern in solmate_bug_patterns:
                solmate_bug_matches.extend(re.findall(pattern, title_body_text))

            # 计算分数
            match_score = (len(general_keyword_matches) + len(label_matches) +
                           len(fix_references) + len(solmate_bug_matches))

            if match_score > 0:
                confidence = 'high' if match_score >= 3 else 'medium' if match_score >= 1 else 'low'

                bug_candidates.append({
                    **pr,
                    'general_keyword_matches': general_keyword_matches,
                    'solmate_keyword_matches': solmate_keyword_matches,
                    'label_matches': label_matches,
                    'fix_references': fix_references,
                    'solmate_bug_matches': solmate_bug_matches,
                    'match_score': match_score,
                    'confidence': confidence
                })

        print(f"✅ 识别出 {len(bug_candidates)} 个疑似 bug 修复 PR")
        return bug_candidates

    def export_results(self, merged_prs, bug_candidates, stats):
        """导出结果到 Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_dir = os.path.abspath(SOLMATE_CONFIG['excel_output'])
        os.makedirs(excel_dir, exist_ok=True)
        excel_file = os.path.join(excel_dir, f"solmate_analysis_{timestamp}.xlsx")

        print(f"📂 正在创建 Excel 文件: {excel_file}")

        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Sheet 1: 所有 PR
                pd.DataFrame(merged_prs).to_excel(writer, sheet_name='All_Merged_PRs', index=False)

                # Sheet 2: Bug 候选
                if bug_candidates:
                    bug_df = pd.DataFrame(bug_candidates)
                    display_cols = ['number', 'title', 'user', 'merged_at', 'match_score', 'confidence',
                                    'solmate_bug_matches', 'url']
                    # 确保列存在
                    cols_to_use = [c for c in display_cols if c in bug_df.columns]

                    # 格式化列表列以便阅读
                    display_df = bug_df[cols_to_use].copy()
                    if 'solmate_bug_matches' in display_df.columns:
                        display_df['solmate_bug_matches'] = display_df['solmate_bug_matches'].apply(
                            lambda x: ', '.join(x[:5]))

                    display_df.to_excel(writer, sheet_name='Bug_Fix_Candidates', index=False)

                # Sheet 3: 统计概览
                stats_data = [
                    ['项目', 'Solmate'],
                    ['总 PR 数', stats['total_prs']],
                    ['疑似 Bug 修复', len(bug_candidates)],
                    ['数学库相关', stats['math_prs']],
                    ['Token标准相关', stats['token_prs']],
                    ['Gas/汇编相关', stats['gas_prs']],
                    ['Auth相关', stats['auth_prs']],
                    ['工具库相关', stats['utils_prs']]
                ]
                pd.DataFrame(stats_data, columns=['Metric', 'Value']).to_excel(writer, sheet_name='Statistics',
                                                                               index=False)

                # Sheet 4: 功能分类 (针对 Bug 候选)
                if bug_candidates:
                    func_data = []
                    for c in bug_candidates:
                        matches = c['solmate_keyword_matches'] + c['solmate_bug_matches']
                        funcs = []
                        if any(k in str(matches) for k in ['math', 'overflow', 'div', 'mul']): funcs.append('Math')
                        if any(k in str(matches) for k in ['erc', 'token', 'transfer']): funcs.append('Token')
                        if any(k in str(matches) for k in ['gas', 'assembly', 'memory']): funcs.append('Gas/Assembly')
                        if any(k in str(matches) for k in ['auth', 'owner']): funcs.append('Auth')

                        func_data.append({
                            'PR': c['number'],
                            'Title': c['title'],
                            'Category': ', '.join(funcs) if funcs else 'General',
                            'Confidence': c['confidence']
                        })
                    pd.DataFrame(func_data).to_excel(writer, sheet_name='Bug_Categories', index=False)

            print(f"✅ Excel 导出成功: {os.path.getsize(excel_file):,} bytes")
            return excel_file
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return None

    def make_request(self, url, params=None):
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200: return response.json()
            print(f"API Error: {response.status_code}")
            return None
        except Exception as e:
            print(f"Request Exception: {e}")
            return None

    def run_collection(self):
        print("🚀 开始分析 transmissions11/solmate ...")
        merged_prs = self.collect_all_merged_prs()
        if not merged_prs: return

        stats = self.analyze_merged_prs(merged_prs)
        bug_candidates = self.identify_bug_fix_prs(merged_prs)
        self.export_results(merged_prs, bug_candidates, stats)
        print("\n🏁 任务完成")


if __name__ == "__main__":
    collector = SolmateCollector()
    collector.run_collection()