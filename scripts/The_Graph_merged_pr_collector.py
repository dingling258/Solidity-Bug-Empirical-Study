import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import pandas as pd
import json
import re
from datetime import datetime
from config.settings_template import GITHUB_TOKEN, THEGRAPH_CONFIG


class TheGraphContractsCollector:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = THEGRAPH_CONFIG['owner']
        self.repo = THEGRAPH_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # 通用bug相关关键词（与原研究保持一致）
        self.general_bug_keywords = [
            'bug', 'fix', 'repair', 'defect', 'vulnerability', 'issue',
            'error', 'problem', 'incorrect', 'wrong', 'fail', 'crash',
            'security', 'exploit', 'attack', 'overflow', 'underflow',
            'reentrancy', 'gas', 'optimization', 'revert', 'panic'
        ]

        # The Graph Infrastructure特定关键词
        self.thegraph_keywords = [
            'subgraph', 'indexer', 'curator', 'delegator', 'indexing',
            'query', 'grt', 'token', 'stake', 'staking', 'delegate',
            'delegation', 'slash', 'slashing', 'reward', 'rebate',
            'allocation', 'signal', 'curation', 'thaw', 'collect',
            'withdraw', 'deposit', 'channel', 'attestation', 'dispute',
            'fisherman', 'epoch', 'settlement', 'payment', 'gateway',
            'subgraphdeployment', 'metadata', 'ipfs', 'graphql',
            'manifest', 'schema', 'mapping', 'datasource', 'handler',
            'entity', 'store', 'block', 'transaction', 'receipt',
            'log', 'event', 'call', 'function', 'contract'
        ]

        # 合并所有关键词
        self.bug_keywords = self.general_bug_keywords + self.thegraph_keywords

        self.merged_prs = []

    def collect_all_merged_prs(self):
        """收集所有已合并的PR"""
        print("📥 正在收集The Graph Contracts所有已合并的PR...")
        print(f"🔗 仓库: {self.owner}/{self.repo}")

        merged_prs = []
        page = 1
        total_collected = 0

        while True:
            print(f"   正在获取第 {page} 页...")

            # 只获取merged状态的PR
            prs = self.make_request(f"{self.base_url}/pulls", {
                'state': 'closed',  # GitHub API: closed包含merged和未merged的
                'per_page': 100,
                'page': page,
                'sort': 'updated',
                'direction': 'desc'
            })

            if not prs:
                break

            # 筛选出真正merged的PR
            page_merged_count = 0
            for pr in prs:
                if pr.get('merged_at') is not None:  # 关键：只要merged_at不为空
                    merged_prs.append({
                        'project_name': 'The Graph',
                        'project_type': 'Infrastructure',
                        'project_domain': 'Indexing Protocol',
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
                        'base_ref': pr.get('base', {}).get('ref', ''),
                        'head_ref': pr.get('head', {}).get('ref', '')
                    })
                    page_merged_count += 1

            total_collected += page_merged_count
            print(f"   第 {page} 页找到 {page_merged_count} 个合并的PR (总计: {total_collected})")

            # 如果这一页没有merged的PR，可能已经到底了
            if page_merged_count == 0:
                break

            page += 1

        print(f"✅ 总共收集到 {len(merged_prs)} 个已合并的PR")
        return merged_prs

    def analyze_merged_prs(self, merged_prs):
        """分析已合并的PR"""
        print("📊 分析The Graph Contracts已合并的PR...")

        # 基本统计
        total_prs = len(merged_prs)

        # 时间分析
        dates = [pr['merged_at'][:10] for pr in merged_prs]
        date_counts = pd.Series(dates).value_counts().sort_index()

        # 用户分析
        users = [pr['user'] for pr in merged_prs]
        user_counts = pd.Series(users).value_counts()

        # 标签分析
        all_labels = []
        for pr in merged_prs:
            all_labels.extend(pr['labels'])
        label_counts = pd.Series(all_labels).value_counts()

        # 代码变更分析
        total_additions = sum(pr['additions'] for pr in merged_prs)
        total_deletions = sum(pr['deletions'] for pr in merged_prs)
        total_files = sum(pr['changed_files'] for pr in merged_prs)

        # The Graph特定分析
        staking_keywords = ['stake', 'staking', 'delegate', 'delegation', 'slash', 'slashing']
        curation_keywords = ['curator', 'curation', 'signal', 'grt', 'token']
        indexing_keywords = ['indexer', 'indexing', 'subgraph', 'query', 'allocation']

        staking_prs = [pr for pr in merged_prs
                       if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                              for keyword in staking_keywords)]

        curation_prs = [pr for pr in merged_prs
                        if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                               for keyword in curation_keywords)]

        indexing_prs = [pr for pr in merged_prs
                        if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                               for keyword in indexing_keywords)]

        print(f"📈 The Graph Contracts统计结果:")
        print(f"   - 总合并PR数: {total_prs}")
        print(f"   - Staking相关PR数: {len(staking_prs)}")
        print(f"   - Curation相关PR数: {len(curation_prs)}")
        print(f"   - Indexing相关PR数: {len(indexing_prs)}")
        print(f"   - 最早合并日期: {min(dates) if dates else 'N/A'}")
        print(f"   - 最晚合并日期: {max(dates) if dates else 'N/A'}")
        print(
            f"   - 最活跃贡献者: {user_counts.head(1).index[0] if not user_counts.empty else 'N/A'} ({user_counts.iloc[0] if not user_counts.empty else 0} PRs)")
        print(f"   - 总代码行变更: +{total_additions:,} -{total_deletions:,}")
        print(f"   - 总文件变更: {total_files:,}")

        return {
            'total_prs': total_prs,
            'staking_prs': len(staking_prs),
            'curation_prs': len(curation_prs),
            'indexing_prs': len(indexing_prs),
            'date_counts': date_counts,
            'user_counts': user_counts,
            'label_counts': label_counts,
            'code_stats': {
                'additions': total_additions,
                'deletions': total_deletions,
                'files': total_files
            }
        }

    def identify_bug_fix_prs(self, merged_prs):
        """从已合并的PR中识别bug修复相关的PR（遵循原研究方法论）"""
        print("🔍 识别The Graph Contracts bug修复相关的PR...")

        bug_candidates = []

        for pr in merged_prs:
            title_lower = pr['title'].lower()
            body_lower = pr['body'].lower()
            labels_lower = [label.lower() for label in pr['labels']]

            # 检查关键词匹配
            title_body_text = title_lower + ' ' + body_lower

            # 通用bug关键词匹配
            general_keyword_matches = [kw for kw in self.general_bug_keywords if kw in title_body_text]

            # The Graph特定关键词匹配
            thegraph_keyword_matches = [kw for kw in self.thegraph_keywords if kw in title_body_text]

            # 检查标签
            bug_labels = ['bug', 'defect', 'security', 'vulnerability', 'fix', 'hotfix', 'patch', 'critical']
            label_matches = [label for label in labels_lower if any(bug_label in label for bug_label in bug_labels)]

            # 检查fix引用模式
            fix_patterns = [
                r'fix(?:es)?\s*#?\d+',  # fixes #123
                r'resolv(?:es)?\s*#?\d+',  # resolves #123
                r'clos(?:es)?\s*#?\d+',  # closes #123
                r'fix(?:es)?\s+\w+',  # fixes bug
                r'patch(?:es)?\s+\w+',  # patches issue
            ]
            fix_references = []
            for pattern in fix_patterns:
                fix_references.extend(re.findall(pattern, title_body_text))

            # The Graph特定的bug模式
            thegraph_bug_patterns = [
                r'staking.*(?:fail|error|bug|incorrect|slash)',
                r'delegation.*(?:fail|error|bug|wrong|invalid)',
                r'curation.*(?:fail|error|bug|signal|manipulation)',
                r'indexer.*(?:fail|error|bug|slash|penalty)',
                r'subgraph.*(?:fail|error|bug|invalid|malformed)',
                r'query.*(?:fail|error|bug|timeout|invalid)',
                r'allocation.*(?:fail|error|bug|overflow|underflow)',
                r'reward.*(?:fail|error|bug|calculation|distribution)',
                r'grt.*(?:fail|error|bug|transfer|burn|mint)',
                r'epoch.*(?:fail|error|bug|settlement|update)',
                r'channel.*(?:fail|error|bug|payment|dispute)',
                r'attestation.*(?:fail|error|bug|invalid|verification)'
            ]

            thegraph_bug_matches = []
            for pattern in thegraph_bug_patterns:
                thegraph_bug_matches.extend(re.findall(pattern, title_body_text))

            # 计算匹配分数（与原研究方法论一致）
            match_score = (len(general_keyword_matches) +
                           len(label_matches) +
                           len(fix_references) +
                           len(thegraph_bug_matches))

            if general_keyword_matches or label_matches or fix_references or thegraph_bug_matches:
                confidence = 'high' if match_score >= 3 else 'medium' if match_score >= 1 else 'low'

                bug_candidates.append({
                    **pr,
                    'general_keyword_matches': general_keyword_matches,
                    'thegraph_keyword_matches': thegraph_keyword_matches,
                    'label_matches': label_matches,
                    'fix_references': fix_references,
                    'thegraph_bug_matches': thegraph_bug_matches,
                    'match_score': match_score,
                    'confidence': confidence
                })

        print(f"✅ 从 {len(merged_prs)} 个合并PR中识别出 {len(bug_candidates)} 个疑似bug修复PR")

        # 按置信度分类统计
        high_confidence = len([c for c in bug_candidates if c['confidence'] == 'high'])
        medium_confidence = len([c for c in bug_candidates if c['confidence'] == 'medium'])
        low_confidence = len([c for c in bug_candidates if c['confidence'] == 'low'])

        print(f"   - 高置信度: {high_confidence}")
        print(f"   - 中置信度: {medium_confidence}")
        print(f"   - 低置信度: {low_confidence}")

        # 按The Graph功能分类统计
        staking_bugs = len(
            [c for c in bug_candidates if any('staking' in match or 'delegation' in match or 'slash' in match
                                              for match in c['thegraph_keyword_matches'] + c['thegraph_bug_matches'])])
        curation_bugs = len(
            [c for c in bug_candidates if any('curation' in match or 'signal' in match or 'curator' in match
                                              for match in c['thegraph_keyword_matches'] + c['thegraph_bug_matches'])])
        indexing_bugs = len(
            [c for c in bug_candidates if any('indexing' in match or 'subgraph' in match or 'query' in match
                                              for match in c['thegraph_keyword_matches'] + c['thegraph_bug_matches'])])

        print(f"   - Staking相关bug: {staking_bugs}")
        print(f"   - Curation相关bug: {curation_bugs}")
        print(f"   - Indexing相关bug: {indexing_bugs}")

        return bug_candidates

    def export_results(self, merged_prs, bug_candidates, stats):
        """导出结果到Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 使用绝对路径，确保目录创建
        excel_dir = os.path.abspath(THEGRAPH_CONFIG['excel_output'])
        os.makedirs(excel_dir, exist_ok=True)

        excel_file = os.path.join(excel_dir, f"thegraph_contracts_{timestamp}.xlsx")

        print(f"📂 正在创建Excel文件...")
        print(f"   目录: {excel_dir}")
        print(f"   文件: thegraph_contracts_{timestamp}.xlsx")

        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # 1. 所有合并的PR
                merged_df = pd.DataFrame(merged_prs)
                merged_df.to_excel(writer, sheet_name='All_Merged_PRs', index=False)

                # 2. 疑似bug修复PR
                if bug_candidates:
                    bug_df = pd.DataFrame(bug_candidates)
                    # 选择重要列
                    bug_display_df = bug_df[[
                        'number', 'title', 'user', 'merged_at', 'match_score', 'confidence',
                        'general_keyword_matches', 'thegraph_keyword_matches', 'label_matches',
                        'project_name', 'project_type', 'project_domain', 'url'
                    ]].copy()

                    # 格式化匹配结果
                    bug_display_df['general_keyword_matches'] = bug_display_df['general_keyword_matches'].apply(
                        lambda x: ', '.join(x[:5]))
                    bug_display_df['thegraph_keyword_matches'] = bug_display_df['thegraph_keyword_matches'].apply(
                        lambda x: ', '.join(x[:5]))
                    bug_display_df['label_matches'] = bug_display_df['label_matches'].apply(lambda x: ', '.join(x))

                    bug_display_df.to_excel(writer, sheet_name='Bug_Fix_Candidates', index=False)

                # 3. 统计信息
                stats_data = [
                    ['项目名称', 'The Graph'],
                    ['项目类型', 'Infrastructure'],
                    ['项目领域', 'Indexing Protocol'],
                    ['仓库地址', f"{self.owner}/{self.repo}"],
                    ['总合并PR数', stats['total_prs']],
                    ['Staking相关PR数', stats['staking_prs']],
                    ['Curation相关PR数', stats['curation_prs']],
                    ['Indexing相关PR数', stats['indexing_prs']],
                    ['疑似bug修复PR数', len(bug_candidates)],
                    ['最活跃贡献者', stats['user_counts'].index[0] if not stats['user_counts'].empty else 'N/A'],
                    ['总代码增加行数', stats['code_stats']['additions']],
                    ['总代码删除行数', stats['code_stats']['deletions']],
                    ['总变更文件数', stats['code_stats']['files']]
                ]

                stats_df = pd.DataFrame(stats_data, columns=['指标', '数值'])
                stats_df.to_excel(writer, sheet_name='Statistics', index=False)

                # 4. 时间趋势
                time_df = stats['date_counts'].reset_index()
                time_df.columns = ['日期', 'PR数量']
                time_df.to_excel(writer, sheet_name='Time_Trends', index=False)

                # 5. 置信度分布
                if bug_candidates:
                    confidence_counts = pd.Series([c['confidence'] for c in bug_candidates]).value_counts()
                    confidence_df = confidence_counts.reset_index()
                    confidence_df.columns = ['置信度', '数量']
                    confidence_df.to_excel(writer, sheet_name='Confidence_Distribution', index=False)

                # 6. The Graph功能分类
                if bug_candidates:
                    function_data = []
                    for candidate in bug_candidates:
                        functions = []
                        matches = candidate['thegraph_keyword_matches'] + candidate['thegraph_bug_matches']

                        if any('staking' in match or 'delegation' in match or 'slash' in match for match in matches):
                            functions.append('Staking')
                        if any('curation' in match or 'signal' in match or 'curator' in match for match in matches):
                            functions.append('Curation')
                        if any('indexing' in match or 'subgraph' in match or 'query' in match for match in matches):
                            functions.append('Indexing')

                        function_data.append({
                            'PR_Number': candidate['number'],
                            'Title': candidate['title'],
                            'Functions': ', '.join(functions) if functions else 'General',
                            'Confidence': candidate['confidence']
                        })

                    function_df = pd.DataFrame(function_data)
                    function_df.to_excel(writer, sheet_name='Function_Classification', index=False)

            # 验证文件是否真的创建成功
            if os.path.exists(excel_file):
                file_size = os.path.getsize(excel_file)
                print(f"✅ 文件创建成功！")
                print(f"   大小: {file_size:,} bytes")
            else:
                print(f"❌ 文件创建失败！")

        except Exception as e:
            print(f"❌ 导出Excel时出错: {e}")
            excel_file = None

        print(f"📁 The Graph Contracts结果已导出到: {excel_file}")
        print(f"📂 完整路径: {os.path.abspath(excel_file) if excel_file else 'N/A'}")
        return excel_file

    def make_request(self, url, params=None):
        """发送API请求"""
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print("⚠️  API配额可能不足，请稍后重试")
                return None
            else:
                print(f"API请求失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None

    def run_collection(self):
        """运行完整的收集流程"""
        print("🚀 开始收集The Graph Contracts已合并的PR...")
        print("📖 实验流程：专门分析Solidity智能合约仓库")
        print("🔗 项目：The Graph - 去中心化索引协议")
        print(f"📁 仓库：{self.owner}/{self.repo}")

        # 1. 收集所有已合并的PR
        merged_prs = self.collect_all_merged_prs()

        if not merged_prs:
            print("❌ 没有找到已合并的PR")
            return

        # 2. 分析PR数据
        stats = self.analyze_merged_prs(merged_prs)

        # 3. 识别bug修复相关的PR
        bug_candidates = self.identify_bug_fix_prs(merged_prs)

        # 4. 导出结果
        excel_file = self.export_results(merged_prs, bug_candidates, stats)

        print(f"\n✅ The Graph Contracts数据收集完成！")
        print(f"📊 结果摘要:")
        print(f"   - 项目: The Graph")
        print(f"   - 类型: Infrastructure")
        print(f"   - 领域: Indexing Protocol")
        print(f"   - 总合并PR: {len(merged_prs)}")
        print(f"   - Staking功能PR: {stats['staking_prs']}")
        print(f"   - Curation功能PR: {stats['curation_prs']}")
        print(f"   - Indexing功能PR: {stats['indexing_prs']}")
        print(f"   - 疑似bug修复: {len(bug_candidates)}")
        print(f"   - 结果文件: {excel_file}")

        # 显示项目目录结构
        print(f"\n📂 当前工作目录: {os.getcwd()}")
        print(f"📂 输出目录结构:")
        output_base = os.path.abspath('./output')
        if os.path.exists(output_base):
            for root, dirs, files in os.walk(output_base):
                level = root.replace(output_base, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    print(f"{subindent}{file}")

        print(f"\n📋 下一步:")
        print(f"   1. 人工审核疑似bug修复PR列表")
        print(f"   2. 确认真正的bug修复实例")
        print(f"   3. 按8种bug类型进行分类")
        print(f"   4. 分析Infrastructure vs DeFi的差异")


if __name__ == "__main__":
    collector = TheGraphContractsCollector()
    collector.run_collection()