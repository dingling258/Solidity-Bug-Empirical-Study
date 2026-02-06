import sys
import os

# 确保可以导入上级目录的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import pandas as pd
import json
import re
from datetime import datetime
# 引入新增的 LENS_CONFIG
from config.settings_template import GITHUB_TOKEN, LENS_CONFIG


class LensCollector:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = LENS_CONFIG['owner']
        self.repo = LENS_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # 1. 通用 Bug 关键词
        self.general_bug_keywords = [
            'bug', 'fix', 'repair', 'defect', 'vulnerability', 'issue',
            'error', 'problem', 'incorrect', 'wrong', 'fail', 'crash',
            'security', 'exploit', 'attack', 'overflow', 'underflow',
            'reentrancy', 'gas', 'optimization', 'revert', 'panic'
        ]

        # 2. Lens Protocol 特定关键词 (社交图谱业务逻辑)
        self.lens_keywords = [
            # 核心实体
            'lenshub', 'profile', 'publication', 'post', 'comment', 'mirror',
            'dispatcher', 'handle', 'namespace', 'storage', 'state',

            # 模块系统 (Module System) - Lens 的核心扩展点
            'module', 'collect', 'follow', 'reference', 'action',
            'whitelist', 'initialize', 'process', 'callback',

            # NFT 与 资产
            'nft', 'tokenuri', 'svg', 'metadata', 'image', 'trait',
            'burn', 'mint', 'transfer', 'approve',

            # 治理与权限
            'governance', 'admin', 'emergency', 'pause', 'unpause',
            'guardian', 'upgrade', 'proxy', 'implementation',

            # 元交易与签名 (EIP-712)
            'eip712', 'signature', 'nonce', 'deadline', 'recover',
            'meta-tx', 'gasless', 'relay', 'typed data'
        ]

        # 合并所有关键词
        self.bug_keywords = self.general_bug_keywords + self.lens_keywords
        self.merged_prs = []

    def collect_all_merged_prs(self):
        """收集所有已合并的PR"""
        print("📥 正在收集 lens-protocol/core 所有已合并的PR...")
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
                        'project_name': 'Lens Protocol',
                        'project_type': 'Social Graph',
                        'project_domain': 'SocialFi / App Logic',
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
        print("📊 分析 Lens 已合并的PR...")

        total_prs = len(merged_prs)
        dates = [pr['merged_at'][:10] for pr in merged_prs]
        date_counts = pd.Series(dates).value_counts().sort_index()
        users = [pr['user'] for pr in merged_prs]
        user_counts = pd.Series(users).value_counts()

        all_labels = []
        for pr in merged_prs:
            all_labels.extend(pr['labels'])
        label_counts = pd.Series(all_labels).value_counts()

        # Lens 领域分类
        core_keywords = ['lenshub', 'profile', 'publication', 'dispatcher']
        module_keywords = ['module', 'collect', 'follow', 'reference']
        nft_keywords = ['nft', 'erc721', 'tokenuri', 'svg', 'metadata']
        gov_keywords = ['governance', 'admin', 'upgrade', 'proxy']
        sig_keywords = ['eip712', 'signature', 'meta-tx', 'nonce']

        core_prs = [pr for pr in merged_prs if
                    any(k in pr['title'].lower() or k in pr['body'].lower() for k in core_keywords)]
        module_prs = [pr for pr in merged_prs if
                      any(k in pr['title'].lower() or k in pr['body'].lower() for k in module_keywords)]
        nft_prs = [pr for pr in merged_prs if
                   any(k in pr['title'].lower() or k in pr['body'].lower() for k in nft_keywords)]
        gov_prs = [pr for pr in merged_prs if
                   any(k in pr['title'].lower() or k in pr['body'].lower() for k in gov_keywords)]
        sig_prs = [pr for pr in merged_prs if
                   any(k in pr['title'].lower() or k in pr['body'].lower() for k in sig_keywords)]

        print(f"📈 Lens 统计结果:")
        print(f"   - 总合并PR数: {total_prs}")
        print(f"   - 核心逻辑(Hub/Profile)相关: {len(core_prs)}")
        print(f"   - 模块系统(Modules)相关: {len(module_prs)}")
        print(f"   - NFT/元数据相关: {len(nft_prs)}")
        print(f"   - 治理/升级相关: {len(gov_prs)}")
        print(f"   - 签名/元交易相关: {len(sig_prs)}")

        return {
            'total_prs': total_prs,
            'core_prs': len(core_prs),
            'module_prs': len(module_prs),
            'nft_prs': len(nft_prs),
            'gov_prs': len(gov_prs),
            'sig_prs': len(sig_prs),
            'date_counts': date_counts,
            'user_counts': user_counts,
            'label_counts': label_counts
        }

    def identify_bug_fix_prs(self, merged_prs):
        """识别 Bug 修复 PR (针对 Lens 业务逻辑定制)"""
        print("🔍 识别 Lens bug 修复相关的 PR...")

        bug_candidates = []

        for pr in merged_prs:
            title_lower = pr['title'].lower()
            body_lower = pr['body'].lower()
            labels_lower = [label.lower() for label in pr['labels']]
            title_body_text = title_lower + ' ' + body_lower

            # 1. 基础匹配
            general_keyword_matches = [kw for kw in self.general_bug_keywords if kw in title_body_text]
            lens_keyword_matches = [kw for kw in self.lens_keywords if kw in title_body_text]

            bug_labels = ['bug', 'defect', 'security', 'vulnerability', 'fix', 'hotfix', 'patch']
            label_matches = [label for label in labels_lower if any(bug_label in label for bug_label in bug_labels)]

            # 2. Fix 引用模式
            fix_patterns = [
                r'fix(?:es)?\s*#?\d+', r'resolv(?:es)?\s*#?\d+', r'clos(?:es)?\s*#?\d+',
                r'fix(?:es)?\s+\w+'
            ]
            fix_references = []
            for pattern in fix_patterns:
                fix_references.extend(re.findall(pattern, title_body_text))

            # 3. Lens 特定 Bug 模式 (重点关注业务逻辑和模块交互)
            lens_bug_patterns = [
                # 核心逻辑与状态
                r'profile.*(?:id|owner|bug|fix|check)',
                r'publication.*(?:type|pointer|bug|fix)',
                r'dispatcher.*(?:auth|permission|bug|fix)',
                r'state.*(?:update|stale|bug|fix)',

                # 模块交互
                r'module.*(?:return|data|decode|bug|fix)',
                r'collect.*(?:limit|fee|bug|fix|revert)',
                r'follow.*(?:nft|approve|bug|fix)',
                r'reference.*(?:validation|bug|fix)',
                r'callback.*(?:fail|reentrancy|bug|fix)',

                # 签名与安全
                r'signature.*(?:replay|invalid|domain|bug|fix)',
                r'nonce.*(?:increment|check|bug|fix)',
                r'meta-tx.*(?:sender|relayer|bug|fix)',
                r'front-run.*(?:protect|bug|fix)',

                # NFT 与 元数据
                r'tokenuri.*(?:json|format|bug|fix)',
                r'svg.*(?:render|size|bug|fix)',
                r'metadata.*(?:update|refresh|bug|fix)',

                # 治理与升级
                r'proxy.*(?:slot|collision|init|bug|fix)',
                r'upgrade.*(?:safe|check|bug|fix)',
                r'pause.*(?:logic|bypass|bug|fix)'
            ]

            lens_bug_matches = []
            for pattern in lens_bug_patterns:
                lens_bug_matches.extend(re.findall(pattern, title_body_text))

            # 计算分数
            match_score = (len(general_keyword_matches) + len(label_matches) +
                           len(fix_references) + len(lens_bug_matches))

            if match_score > 0:
                confidence = 'high' if match_score >= 3 else 'medium' if match_score >= 1 else 'low'

                bug_candidates.append({
                    **pr,
                    'general_keyword_matches': general_keyword_matches,
                    'lens_keyword_matches': lens_keyword_matches,
                    'label_matches': label_matches,
                    'fix_references': fix_references,
                    'lens_bug_matches': lens_bug_matches,
                    'match_score': match_score,
                    'confidence': confidence
                })

        print(f"✅ 识别出 {len(bug_candidates)} 个疑似 bug 修复 PR")
        return bug_candidates

    def export_results(self, merged_prs, bug_candidates, stats):
        """导出结果到 Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_dir = os.path.abspath(LENS_CONFIG['excel_output'])
        os.makedirs(excel_dir, exist_ok=True)
        excel_file = os.path.join(excel_dir, f"lens_analysis_{timestamp}.xlsx")

        print(f"📂 正在创建 Excel 文件: {excel_file}")

        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Sheet 1: 所有 PR
                pd.DataFrame(merged_prs).to_excel(writer, sheet_name='All_Merged_PRs', index=False)

                # Sheet 2: Bug 候选
                if bug_candidates:
                    bug_df = pd.DataFrame(bug_candidates)
                    display_cols = ['number', 'title', 'user', 'merged_at', 'match_score', 'confidence',
                                    'lens_bug_matches', 'url']
                    cols_to_use = [c for c in display_cols if c in bug_df.columns]

                    display_df = bug_df[cols_to_use].copy()
                    if 'lens_bug_matches' in display_df.columns:
                        display_df['lens_bug_matches'] = display_df['lens_bug_matches'].apply(
                            lambda x: ', '.join(x[:5]))

                    display_df.to_excel(writer, sheet_name='Bug_Fix_Candidates', index=False)

                # Sheet 3: 统计概览
                stats_data = [
                    ['项目', 'Lens Protocol'],
                    ['总 PR 数', stats['total_prs']],
                    ['疑似 Bug 修复', len(bug_candidates)],
                    ['核心逻辑相关', stats['core_prs']],
                    ['模块系统相关', stats['module_prs']],
                    ['NFT/元数据相关', stats['nft_prs']],
                    ['治理/升级相关', stats['gov_prs']],
                    ['签名/元交易相关', stats['sig_prs']]
                ]
                pd.DataFrame(stats_data, columns=['Metric', 'Value']).to_excel(writer, sheet_name='Statistics',
                                                                               index=False)

                # Sheet 4: 功能分类 (针对 Bug 候选)
                if bug_candidates:
                    func_data = []
                    for c in bug_candidates:
                        matches = c['lens_keyword_matches'] + c['lens_bug_matches']
                        matches_str = str(matches).lower()
                        funcs = []

                        if any(k in matches_str for k in ['profile', 'hub', 'publication']): funcs.append('Core Logic')
                        if any(k in matches_str for k in ['module', 'collect', 'follow']): funcs.append('Modules')
                        if any(k in matches_str for k in ['nft', 'svg', 'tokenuri']): funcs.append('NFT/Metadata')
                        if any(k in matches_str for k in ['eip712', 'signature', 'meta-tx']): funcs.append(
                            'Meta-Tx/Auth')
                        if any(k in matches_str for k in ['proxy', 'upgrade', 'admin']): funcs.append('Governance')

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
        print("🚀 开始分析 lens-protocol/core ...")
        merged_prs = self.collect_all_merged_prs()
        if not merged_prs: return

        stats = self.analyze_merged_prs(merged_prs)
        bug_candidates = self.identify_bug_fix_prs(merged_prs)
        self.export_results(merged_prs, bug_candidates, stats)
        print("\n🏁 任务完成")


if __name__ == "__main__":
    collector = LensCollector()
    collector.run_collection()