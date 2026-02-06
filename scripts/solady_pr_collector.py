import sys
import os

# 确保可以导入上级目录的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import pandas as pd
import json
import re
from datetime import datetime
# 引入新增的 SOLADY_CONFIG
from config.settings_template import GITHUB_TOKEN, SOLADY_CONFIG


class SoladyCollector:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = SOLADY_CONFIG['owner']
        self.repo = SOLADY_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # 1. 通用 Bug 关键词
        self.general_bug_keywords = [
            'bug', 'fix', 'repair', 'defect', 'vulnerability', 'issue',
            'error', 'problem', 'incorrect', 'wrong', 'fail', 'crash',
            'security', 'exploit', 'attack', 'overflow', 'underflow',
            'reentrancy', 'gas', 'optimization', 'revert', 'panic'
        ]

        # 2. Solady 特定关键词 (针对高度优化的汇编库)
        self.solady_keywords = [
            # 核心汇编与优化 (Solady 的灵魂)
            'assembly', 'yul', 'inline', 'mload', 'mstore', 'sload', 'sstore',
            'calldataload', 'calldatacopy', 'codecopy', 'returndatacopy',
            'bit', 'shift', 'mask', 'shr', 'shl', 'sar', 'not', 'xor', 'and', 'or',
            'unchecked', 'gas', 'optimize', 'scratch', 'pointer',

            # 账户抽象 (ERC-4337) - Solady 的重要组件
            'erc4337', 'account', 'abstraction', 'userop', 'bundler',
            'entrypoint', 'paymaster', 'factory', 'validate', 'signature',
            'smart', 'wallet', 'nonce',

            # 密码学与签名
            'ecdsa', 'secp256k1', 'signature', 'recover', 'malleability',
            'merkle', 'proof', 'leaf', 'root', 'hash', 'eip712', 'domain',
            'separator', 'p256', 'rsa',

            # 高级工具库 (Solady 特色)
            'libzip', 'compression', 'decompression', 'calldata',
            'libclone', 'proxy', 'minimal', 'clone', 'create2', 'create3',
            'libsort', 'sort', 'insertion', 'quick',
            'libstring', 'base64', 'hex', 'decimal',
            'libbitmap', 'bitmap', 'popcount',

            # 标准实现
            'erc20', 'erc721', 'erc1155', 'erc2981', 'royalty',
            'erc1967', 'beacon', 'implementation', 'admin',
            'permit2', 'allowance', 'transfer'
        ]

        # 合并所有关键词
        self.bug_keywords = self.general_bug_keywords + self.solady_keywords
        self.merged_prs = []

    def collect_all_merged_prs(self):
        """收集所有已合并的PR"""
        print("📥 正在收集 Vectorized/solady 所有已合并的PR...")
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
                        'project_name': 'Solady',
                        'project_type': 'Library',
                        'project_domain': 'Hyper-Optimized Solidity Library',
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
        print("📊 分析 Solady 已合并的PR...")

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

        # Solady 特定领域分类
        asm_keywords = ['assembly', 'yul', 'gas', 'optimize', 'inline']
        aa_keywords = ['erc4337', 'userop', 'paymaster', 'bundler', 'account']
        crypto_keywords = ['ecdsa', 'signature', 'merkle', 'hash', 'ecrecover']
        utils_keywords = ['libzip', 'libclone', 'libsort', 'libstring', 'utils']
        token_keywords = ['erc20', 'erc721', 'erc1155', 'permit']

        asm_prs = [pr for pr in merged_prs if
                   any(k in pr['title'].lower() or k in pr['body'].lower() for k in asm_keywords)]
        aa_prs = [pr for pr in merged_prs if
                  any(k in pr['title'].lower() or k in pr['body'].lower() for k in aa_keywords)]
        crypto_prs = [pr for pr in merged_prs if
                      any(k in pr['title'].lower() or k in pr['body'].lower() for k in crypto_keywords)]
        utils_prs = [pr for pr in merged_prs if
                     any(k in pr['title'].lower() or k in pr['body'].lower() for k in utils_keywords)]
        token_prs = [pr for pr in merged_prs if
                     any(k in pr['title'].lower() or k in pr['body'].lower() for k in token_keywords)]

        print(f"📈 Solady 统计结果:")
        print(f"   - 总合并PR数: {total_prs}")
        print(f"   - 汇编/Gas优化相关: {len(asm_prs)}")
        print(f"   - 账户抽象(AA)相关: {len(aa_prs)}")
        print(f"   - 密码学相关: {len(crypto_prs)}")
        print(f"   - 工具库(Lib)相关: {len(utils_prs)}")
        print(f"   - Token标准相关: {len(token_prs)}")
        print(f"   - 最活跃贡献者: {user_counts.head(1).index[0] if not user_counts.empty else 'N/A'}")

        return {
            'total_prs': total_prs,
            'asm_prs': len(asm_prs),
            'aa_prs': len(aa_prs),
            'crypto_prs': len(crypto_prs),
            'utils_prs': len(utils_prs),
            'token_prs': len(token_prs),
            'date_counts': date_counts,
            'user_counts': user_counts,
            'label_counts': label_counts,
            'code_stats': {'additions': total_additions, 'deletions': total_deletions, 'files': total_files}
        }

    def identify_bug_fix_prs(self, merged_prs):
        """识别 Bug 修复 PR (针对 Solady 定制)"""
        print("🔍 识别 Solady bug 修复相关的 PR...")

        bug_candidates = []

        for pr in merged_prs:
            title_lower = pr['title'].lower()
            body_lower = pr['body'].lower()
            labels_lower = [label.lower() for label in pr['labels']]
            title_body_text = title_lower + ' ' + body_lower

            # 1. 基础匹配
            general_keyword_matches = [kw for kw in self.general_bug_keywords if kw in title_body_text]
            solady_keyword_matches = [kw for kw in self.solady_keywords if kw in title_body_text]

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

            # 3. Solady 特定 Bug 模式 (重点关注汇编、AA和密码学)
            solady_bug_patterns = [
                # 汇编与内存安全
                r'assembly.*(?:bug|fix|stack|memory|slot)',
                r'mstore.*(?:overwrite|bug|fix|offset|collision)',
                r'calldata.*(?:load|copy|bug|fix|offset)',
                r'memory.*(?:corruption|leak|bug|fix|expansion)',
                r'pointer.*(?:bug|fix|invalid|null)',
                r'stack.*(?:too.*deep|underflow|overflow)',

                # 账户抽象 (ERC4337)
                r'erc4337.*(?:compliance|bug|fix|validation)',
                r'userop.*(?:hash|bug|fix|gas|limit)',
                r'paymaster.*(?:bug|fix|deposit|stake)',
                r'validate.*(?:sig|userop|bug|fix)',

                # 密码学与签名
                r'ecdsa.*(?:malleability|recover|v|r|s|bug|fix)',
                r'signature.*(?:invalid|replay|bug|fix|check)',
                r'merkle.*(?:proof|verify|bug|fix|root)',
                r'ecrecover.*(?:address|zero|bug|fix)',

                # 工具库特定
                r'libzip.*(?:compress|decompress|bug|fix)',
                r'clone.*(?:predict|create|bug|fix|address)',
                r'sort.*(?:order|bug|fix|gas)',

                # 逻辑与位运算
                r'bit.*(?:shift|mask|op|bug|fix)',
                r'overflow.*(?:check|bug|fix|add|sub)',
                r'rounding.*(?:error|bug|fix|muldiv)'
            ]

            solady_bug_matches = []
            for pattern in solady_bug_patterns:
                solady_bug_matches.extend(re.findall(pattern, title_body_text))

            # 计算分数
            match_score = (len(general_keyword_matches) + len(label_matches) +
                           len(fix_references) + len(solady_bug_matches))

            if match_score > 0:
                confidence = 'high' if match_score >= 3 else 'medium' if match_score >= 1 else 'low'

                bug_candidates.append({
                    **pr,
                    'general_keyword_matches': general_keyword_matches,
                    'solady_keyword_matches': solady_keyword_matches,
                    'label_matches': label_matches,
                    'fix_references': fix_references,
                    'solady_bug_matches': solady_bug_matches,
                    'match_score': match_score,
                    'confidence': confidence
                })

        print(f"✅ 识别出 {len(bug_candidates)} 个疑似 bug 修复 PR")
        return bug_candidates

    def export_results(self, merged_prs, bug_candidates, stats):
        """导出结果到 Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_dir = os.path.abspath(SOLADY_CONFIG['excel_output'])
        os.makedirs(excel_dir, exist_ok=True)
        excel_file = os.path.join(excel_dir, f"solady_analysis_{timestamp}.xlsx")

        print(f"📂 正在创建 Excel 文件: {excel_file}")

        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Sheet 1: 所有 PR
                pd.DataFrame(merged_prs).to_excel(writer, sheet_name='All_Merged_PRs', index=False)

                # Sheet 2: Bug 候选
                if bug_candidates:
                    bug_df = pd.DataFrame(bug_candidates)
                    display_cols = ['number', 'title', 'user', 'merged_at', 'match_score', 'confidence',
                                    'solady_bug_matches', 'url']
                    # 确保列存在
                    cols_to_use = [c for c in display_cols if c in bug_df.columns]

                    display_df = bug_df[cols_to_use].copy()
                    if 'solady_bug_matches' in display_df.columns:
                        display_df['solady_bug_matches'] = display_df['solady_bug_matches'].apply(
                            lambda x: ', '.join(x[:5]))

                    display_df.to_excel(writer, sheet_name='Bug_Fix_Candidates', index=False)

                # Sheet 3: 统计概览
                stats_data = [
                    ['项目', 'Solady'],
                    ['总 PR 数', stats['total_prs']],
                    ['疑似 Bug 修复', len(bug_candidates)],
                    ['汇编/Gas优化相关', stats['asm_prs']],
                    ['账户抽象(AA)相关', stats['aa_prs']],
                    ['密码学相关', stats['crypto_prs']],
                    ['工具库相关', stats['utils_prs']],
                    ['Token标准相关', stats['token_prs']]
                ]
                pd.DataFrame(stats_data, columns=['Metric', 'Value']).to_excel(writer, sheet_name='Statistics',
                                                                               index=False)

                # Sheet 4: 功能分类 (针对 Bug 候选)
                if bug_candidates:
                    func_data = []
                    for c in bug_candidates:
                        matches = c['solady_keyword_matches'] + c['solady_bug_matches']
                        matches_str = str(matches).lower()
                        funcs = []

                        if any(k in matches_str for k in ['assembly', 'yul', 'gas', 'memory']): funcs.append(
                            'Assembly/Gas')
                        if any(k in matches_str for k in ['erc4337', 'userop', 'paymaster']): funcs.append(
                            'Account Abstraction')
                        if any(k in matches_str for k in ['ecdsa', 'signature', 'merkle']): funcs.append('Cryptography')
                        if any(k in matches_str for k in ['lib', 'zip', 'clone', 'sort']): funcs.append('Utils/Libs')
                        if any(k in matches_str for k in ['erc20', 'erc721', 'token']): funcs.append('Token Standards')

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
        print("🚀 开始分析 Vectorized/solady ...")
        merged_prs = self.collect_all_merged_prs()
        if not merged_prs: return

        stats = self.analyze_merged_prs(merged_prs)
        bug_candidates = self.identify_bug_fix_prs(merged_prs)
        self.export_results(merged_prs, bug_candidates, stats)
        print("\n🏁 任务完成")


if __name__ == "__main__":
    collector = SoladyCollector()
    collector.run_collection()