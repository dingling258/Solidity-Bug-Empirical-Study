import sys
import os

# 确保可以导入上级目录的模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import pandas as pd
import json
import re
from datetime import datetime
# 引入新增的 AIRCASH_CONFIG
from config.settings_template import GITHUB_TOKEN, AIRCASH_CONFIG


class AirCashCollector:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = AIRCASH_CONFIG['owner']
        self.repo = AIRCASH_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # 1. 通用 Bug 关键词
        self.general_bug_keywords = [
            'bug', 'fix', 'repair', 'defect', 'vulnerability', 'issue',
            'error', 'problem', 'incorrect', 'wrong', 'fail', 'crash',
            'security', 'exploit', 'attack', 'overflow', 'underflow',
            'reentrancy', 'gas', 'optimization', 'revert', 'panic'
        ]

        # 2. AirCash 特定关键词 (OTC 交易与仲裁逻辑)
        self.aircash_keywords = [
            # 核心交易实体
            'escrow', 'trade', 'order', 'cash', 'otc', 'deal',
            'merchant', 'user', 'buyer', 'seller', 'maker', 'taker',

            # 资金与支付
            'fee', 'tax', 'amount', 'balance', 'transfer', 'payment',
            'withdraw', 'deposit', 'token', 'currency', 'fiat',

            # 状态流转动作
            'create', 'cancel', 'pay', 'release', 'confirm', 'finish',
            'expire', 'timeout', 'lock', 'unlock',

            # 仲裁与证人系统 (Witness System - AirCash 核心特色)
            'witness', 'appeal', 'judge', 'vote', 'dispute', 'penalty',
            'evidence', 'arbitration', 'stake', 'slashing',

            # 治理与工具
            'governance', 'dao', 'proposal', 'config', 'param'
        ]

        # 合并所有关键词
        self.bug_keywords = self.general_bug_keywords + self.aircash_keywords
        self.merged_prs = []

    def collect_all_merged_prs(self):
        """收集所有已合并的PR"""
        print("📥 正在收集 Aircoin-official/AirCash 所有已合并的PR...")
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
                        'project_name': 'AirCash',
                        'project_type': 'OTC Platform',
                        'project_domain': 'DeFi / Payment',
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
        print("📊 分析 AirCash 已合并的PR...")

        total_prs = len(merged_prs)
        dates = [pr['merged_at'][:10] for pr in merged_prs]
        date_counts = pd.Series(dates).value_counts().sort_index()
        users = [pr['user'] for pr in merged_prs]
        user_counts = pd.Series(users).value_counts()

        all_labels = []
        for pr in merged_prs:
            all_labels.extend(pr['labels'])
        label_counts = pd.Series(all_labels).value_counts()

        # AirCash 领域分类
        trade_keywords = ['order', 'trade', 'create', 'cancel', 'release', 'escrow']
        witness_keywords = ['witness', 'appeal', 'judge', 'vote', 'dispute']
        finance_keywords = ['fee', 'tax', 'withdraw', 'transfer', 'token']
        ui_keywords = ['ui', 'frontend', 'css', 'html', 'style', 'display', 'mobile']  # AirCash 仓库可能包含前端

        trade_prs = [pr for pr in merged_prs if
                     any(k in pr['title'].lower() or k in pr['body'].lower() for k in trade_keywords)]
        witness_prs = [pr for pr in merged_prs if
                       any(k in pr['title'].lower() or k in pr['body'].lower() for k in witness_keywords)]
        finance_prs = [pr for pr in merged_prs if
                       any(k in pr['title'].lower() or k in pr['body'].lower() for k in finance_keywords)]
        ui_prs = [pr for pr in merged_prs if
                  any(k in pr['title'].lower() or k in pr['body'].lower() for k in ui_keywords)]

        print(f"📈 AirCash 统计结果:")
        print(f"   - 总合并PR数: {total_prs}")
        print(f"   - 交易/托管逻辑相关: {len(trade_prs)}")
        print(f"   - 证人/申诉系统相关: {len(witness_prs)}")
        print(f"   - 资金/费率相关: {len(finance_prs)}")
        print(f"   - 前端/UI相关: {len(ui_prs)}")

        return {
            'total_prs': total_prs,
            'trade_prs': len(trade_prs),
            'witness_prs': len(witness_prs),
            'finance_prs': len(finance_prs),
            'ui_prs': len(ui_prs),
            'date_counts': date_counts,
            'user_counts': user_counts,
            'label_counts': label_counts
        }

    def identify_bug_fix_prs(self, merged_prs):
        """识别 Bug 修复 PR (针对 OTC 业务逻辑定制)"""
        print("🔍 识别 AirCash bug 修复相关的 PR...")

        bug_candidates = []

        for pr in merged_prs:
            title_lower = pr['title'].lower()
            body_lower = pr['body'].lower()
            labels_lower = [label.lower() for label in pr['labels']]
            title_body_text = title_lower + ' ' + body_lower

            # 1. 基础匹配
            general_keyword_matches = [kw for kw in self.general_bug_keywords if kw in title_body_text]
            aircash_keyword_matches = [kw for kw in self.aircash_keywords if kw in title_body_text]

            bug_labels = ['bug', 'defect', 'security', 'fix', 'hotfix']
            label_matches = [label for label in labels_lower if any(bug_label in label for bug_label in bug_labels)]

            # 2. Fix 引用模式
            fix_patterns = [
                r'fix(?:es)?\s*#?\d+', r'resolv(?:es)?\s*#?\d+', r'clos(?:es)?\s*#?\d+',
                r'fix(?:es)?\s+\w+'
            ]
            fix_references = []
            for pattern in fix_patterns:
                fix_references.extend(re.findall(pattern, title_body_text))

            # 3. AirCash 特定 Bug 模式 (重点关注资金安全和流程闭环)
            aircash_bug_patterns = [
                # 交易状态机
                r'order.*(?:status|state|stuck|bug|fix)',
                r'cancel.*(?:fail|permission|time|bug|fix)',
                r'release.*(?:fail|double|check|bug|fix)',
                r'escrow.*(?:lock|balance|bug|fix)',

                # 证人与申诉
                r'witness.*(?:vote|count|list|bug|fix)',
                r'appeal.*(?:judge|result|time|bug|fix)',
                r'dispute.*(?:resolve|bug|fix)',

                # 资金计算
                r'fee.*(?:calc|deduct|amount|bug|fix)',
                r'tax.*(?:rate|bug|fix)',
                r'decimal.*(?:precision|bug|fix)',

                # 安全与权限
                r'signature.*(?:verify|invalid|bug|fix)',
                r'msg\.sender.*(?:check|bug|fix)',
                r'reentrancy.*(?:guard|bug|fix)'
            ]

            aircash_bug_matches = []
            for pattern in aircash_bug_patterns:
                aircash_bug_matches.extend(re.findall(pattern, title_body_text))

            # 计算分数
            match_score = (len(general_keyword_matches) + len(label_matches) +
                           len(fix_references) + len(aircash_bug_matches))

            if match_score > 0:
                confidence = 'high' if match_score >= 3 else 'medium' if match_score >= 1 else 'low'

                bug_candidates.append({
                    **pr,
                    'general_keyword_matches': general_keyword_matches,
                    'aircash_keyword_matches': aircash_keyword_matches,
                    'label_matches': label_matches,
                    'fix_references': fix_references,
                    'aircash_bug_matches': aircash_bug_matches,
                    'match_score': match_score,
                    'confidence': confidence
                })

        print(f"✅ 识别出 {len(bug_candidates)} 个疑似 bug 修复 PR")
        return bug_candidates

    def export_results(self, merged_prs, bug_candidates, stats):
        """导出结果到 Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_dir = os.path.abspath(AIRCASH_CONFIG['excel_output'])
        os.makedirs(excel_dir, exist_ok=True)
        excel_file = os.path.join(excel_dir, f"aircash_analysis_{timestamp}.xlsx")

        print(f"📂 正在创建 Excel 文件: {excel_file}")

        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Sheet 1: 所有 PR
                pd.DataFrame(merged_prs).to_excel(writer, sheet_name='All_Merged_PRs', index=False)

                # Sheet 2: Bug 候选
                if bug_candidates:
                    bug_df = pd.DataFrame(bug_candidates)
                    display_cols = ['number', 'title', 'user', 'merged_at', 'match_score', 'confidence',
                                    'aircash_bug_matches', 'url']
                    cols_to_use = [c for c in display_cols if c in bug_df.columns]

                    display_df = bug_df[cols_to_use].copy()
                    if 'aircash_bug_matches' in display_df.columns:
                        display_df['aircash_bug_matches'] = display_df['aircash_bug_matches'].apply(
                            lambda x: ', '.join(x[:5]))

                    display_df.to_excel(writer, sheet_name='Bug_Fix_Candidates', index=False)

                # Sheet 3: 统计概览
                stats_data = [
                    ['项目', 'AirCash'],
                    ['总 PR 数', stats['total_prs']],
                    ['疑似 Bug 修复', len(bug_candidates)],
                    ['交易/托管相关', stats['trade_prs']],
                    ['证人/申诉相关', stats['witness_prs']],
                    ['资金/费率相关', stats['finance_prs']],
                    ['前端/UI相关', stats['ui_prs']]
                ]
                pd.DataFrame(stats_data, columns=['Metric', 'Value']).to_excel(writer, sheet_name='Statistics',
                                                                               index=False)

                # Sheet 4: 功能分类 (针对 Bug 候选)
                if bug_candidates:
                    func_data = []
                    for c in bug_candidates:
                        matches = c['aircash_keyword_matches'] + c['aircash_bug_matches']
                        matches_str = str(matches).lower()
                        funcs = []

                        if any(k in matches_str for k in ['order', 'trade', 'escrow', 'release']): funcs.append(
                            'Trading Logic')
                        if any(k in matches_str for k in ['witness', 'appeal', 'vote']): funcs.append('Witness/Appeal')
                        if any(k in matches_str for k in ['fee', 'tax', 'withdraw']): funcs.append('Finance')
                        if any(k in matches_str for k in ['ui', 'css', 'display']): funcs.append('Frontend')

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
        print("🚀 开始分析 Aircoin-official/AirCash ...")
        merged_prs = self.collect_all_merged_prs()
        if not merged_prs: return

        stats = self.analyze_merged_prs(merged_prs)
        bug_candidates = self.identify_bug_fix_prs(merged_prs)
        self.export_results(merged_prs, bug_candidates, stats)
        print("\n🏁 任务完成")


if __name__ == "__main__":
    collector = AirCashCollector()
    collector.run_collection()