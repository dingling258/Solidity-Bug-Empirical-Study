import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import pandas as pd
import json
import re
from datetime import datetime
from config.settings_template import GITHUB_TOKEN, MAKERDAO_CONFIG


class MakerDAODSSCollector:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = MAKERDAO_CONFIG['owner']
        self.repo = MAKERDAO_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # 通用bug相关关键词（与原研究保持一致）
        self.general_bug_keywords = [
            'bug', 'fix', 'repair', 'defect', 'vulnerability', 'issue',
            'error', 'problem', 'incorrect', 'wrong', 'fail', 'crash',
            'security', 'exploit', 'attack', 'overflow', 'underflow',
            'reentrancy', 'gas', 'optimization', 'revert', 'panic'
        ]

        # MakerDAO DSS特定关键词
        self.makerdao_keywords = [
            'dai', 'cdp', 'vault', 'collateral', 'stability', 'maker', 'governance',
            'liquidation', 'auction', 'flapper', 'flopper', 'vow', 'jug', 'spot',
            'end', 'pause', 'proxy', 'registry', 'chief', 'hat', 'spell',
            'debt', 'surplus', 'deficit', 'rate', 'fee', 'penalty', 'kick',
            'bite', 'bark', 'dent', 'deal', 'tend', 'clip', 'calc', 'dog',
            'gem', 'join', 'adapt', 'flip', 'flop', 'hope', 'nope', 'rely',
            'deny', 'file', 'drip', 'fold', 'grab', 'heal', 'kiss', 'suck',
            'bump', 'dump', 'yank', 'cage', 'free', 'pack', 'cash', 'exit',
            'quit', 'move', 'flux', 'fork', 'frob', 'slip', 'toll', 'chop',
            'lump', 'step', 'cut', 'cusp', 'chip', 'tip', 'chost', 'buf',
            'tail', 'tau', 'ttl', 'lot', 'bid', 'guy', 'tic', 'gal', 'tab',
            'rad', 'wad', 'ray', 'pot', 'pie', 'chi', 'rho', 'dsr', 'live',
            'vat', 'cat', 'box', 'ilk', 'urn', 'gem', 'ink', 'art', 'dust',
            'line', 'hole', 'dirt', 'room', 'sin', 'vice', 'ash', 'on',
            'mkr', 'gov', 'iou', 'lock', 'free', 'vote', 'lift', 'slate'
        ]

        # 合并所有关键词
        self.bug_keywords = self.general_bug_keywords + self.makerdao_keywords

        self.merged_prs = []

    def collect_all_merged_prs(self):
        """收集所有已合并的PR"""
        print("📥 正在收集MakerDAO DSS所有已合并的PR...")
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
                        'project_name': 'MakerDAO',
                        'project_type': 'DeFi',
                        'project_domain': 'Stablecoin Protocol',
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
        print("📊 分析MakerDAO DSS已合并的PR...")

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

        # MakerDAO特定分析
        vault_keywords = ['vault', 'cdp', 'collateral', 'liquidation', 'auction']
        governance_keywords = ['governance', 'vote', 'spell', 'chief', 'hat', 'mkr']
        stability_keywords = ['dai', 'stability', 'rate', 'fee', 'dsr', 'surplus']

        vault_prs = [pr for pr in merged_prs
                     if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                            for keyword in vault_keywords)]

        governance_prs = [pr for pr in merged_prs
                         if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                                for keyword in governance_keywords)]

        stability_prs = [pr for pr in merged_prs
                        if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                               for keyword in stability_keywords)]

        print(f"📈 MakerDAO DSS统计结果:")
        print(f"   - 总合并PR数: {total_prs}")
        print(f"   - Vault相关PR数: {len(vault_prs)}")
        print(f"   - Governance相关PR数: {len(governance_prs)}")
        print(f"   - Stability相关PR数: {len(stability_prs)}")
        print(f"   - 最早合并日期: {min(dates) if dates else 'N/A'}")
        print(f"   - 最晚合并日期: {max(dates) if dates else 'N/A'}")
        print(
            f"   - 最活跃贡献者: {user_counts.head(1).index[0] if not user_counts.empty else 'N/A'} ({user_counts.iloc[0] if not user_counts.empty else 0} PRs)")
        print(f"   - 总代码行变更: +{total_additions:,} -{total_deletions:,}")
        print(f"   - 总文件变更: {total_files:,}")

        return {
            'total_prs': total_prs,
            'vault_prs': len(vault_prs),
            'governance_prs': len(governance_prs),
            'stability_prs': len(stability_prs),
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
        print("🔍 识别MakerDAO DSS bug修复相关的PR...")

        bug_candidates = []

        for pr in merged_prs:
            title_lower = pr['title'].lower()
            body_lower = pr['body'].lower()
            labels_lower = [label.lower() for label in pr['labels']]

            # 检查关键词匹配
            title_body_text = title_lower + ' ' + body_lower

            # 通用bug关键词匹配
            general_keyword_matches = [kw for kw in self.general_bug_keywords if kw in title_body_text]

            # MakerDAO特定关键词匹配
            makerdao_keyword_matches = [kw for kw in self.makerdao_keywords if kw in title_body_text]

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

            # MakerDAO特定的bug模式
            makerdao_bug_patterns = [
                r'vault.*(?:fail|error|bug|incorrect|liquidat)',
                r'auction.*(?:fail|error|bug|wrong|invalid)',
                r'governance.*(?:fail|error|bug|vote|spell)',
                r'dai.*(?:fail|error|bug|peg|stability|rate)',
                r'collateral.*(?:fail|error|bug|lock|unlock)',
                r'liquidation.*(?:fail|error|bug|penalty|auction)',
                r'surplus.*(?:fail|error|bug|auction|buffer)',
                r'deficit.*(?:fail|error|bug|auction|debt)',
                r'oracle.*(?:fail|error|bug|price|feed)',
                r'flash.*(?:fail|error|bug|loan|attack)',
                r'proxy.*(?:fail|error|bug|delegate|call)',
                r'pause.*(?:fail|error|bug|guardian|delay)',
                r'spell.*(?:fail|error|bug|cast|schedule)',
                r'chief.*(?:fail|error|bug|vote|hat)',
                r'pot.*(?:fail|error|bug|drip|dsr)',
                r'vat.*(?:fail|error|bug|frob|grab)',
                r'cat.*(?:fail|error|bug|bite|flip)',
                r'dog.*(?:fail|error|bug|bark|clip)',
                r'jug.*(?:fail|error|bug|drip|base)',
                r'spot.*(?:fail|error|bug|poke|par)'
            ]

            makerdao_bug_matches = []
            for pattern in makerdao_bug_patterns:
                makerdao_bug_matches.extend(re.findall(pattern, title_body_text))

            # 计算匹配分数（与原研究方法论一致）
            match_score = (len(general_keyword_matches) +
                           len(label_matches) +
                           len(fix_references) +
                           len(makerdao_bug_matches))

            if general_keyword_matches or label_matches or fix_references or makerdao_bug_matches:
                confidence = 'high' if match_score >= 3 else 'medium' if match_score >= 1 else 'low'

                bug_candidates.append({
                    **pr,
                    'general_keyword_matches': general_keyword_matches,
                    'makerdao_keyword_matches': makerdao_keyword_matches,
                    'label_matches': label_matches,
                    'fix_references': fix_references,
                    'makerdao_bug_matches': makerdao_bug_matches,
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

        # 按MakerDAO功能分类统计
        vault_bugs = len(
            [c for c in bug_candidates if any('vault' in match or 'cdp' in match or 'liquidat' in match
                                              for match in c['makerdao_keyword_matches'] + c['makerdao_bug_matches'])])
        governance_bugs = len(
            [c for c in bug_candidates if any('governance' in match or 'vote' in match or 'spell' in match
                                              for match in c['makerdao_keyword_matches'] + c['makerdao_bug_matches'])])
        stability_bugs = len(
            [c for c in bug_candidates if any('dai' in match or 'stability' in match or 'rate' in match
                                              for match in c['makerdao_keyword_matches'] + c['makerdao_bug_matches'])])

        print(f"   - Vault相关bug: {vault_bugs}")
        print(f"   - Governance相关bug: {governance_bugs}")
        print(f"   - Stability相关bug: {stability_bugs}")

        return bug_candidates

    def export_results(self, merged_prs, bug_candidates, stats):
        """导出结果到Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 使用绝对路径，确保目录创建
        excel_dir = os.path.abspath(MAKERDAO_CONFIG['excel_output'])
        os.makedirs(excel_dir, exist_ok=True)

        excel_file = os.path.join(excel_dir, f"makerdao_dss_{timestamp}.xlsx")

        print(f"📂 正在创建Excel文件...")
        print(f"   目录: {excel_dir}")
        print(f"   文件: makerdao_dss_{timestamp}.xlsx")

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
                        'general_keyword_matches', 'makerdao_keyword_matches', 'label_matches',
                        'project_name', 'project_type', 'project_domain', 'url'
                    ]].copy()

                    # 格式化匹配结果
                    bug_display_df['general_keyword_matches'] = bug_display_df['general_keyword_matches'].apply(
                        lambda x: ', '.join(x[:5]))
                    bug_display_df['makerdao_keyword_matches'] = bug_display_df['makerdao_keyword_matches'].apply(
                        lambda x: ', '.join(x[:5]))
                    bug_display_df['label_matches'] = bug_display_df['label_matches'].apply(lambda x: ', '.join(x))

                    bug_display_df.to_excel(writer, sheet_name='Bug_Fix_Candidates', index=False)

                # 3. 统计信息
                stats_data = [
                    ['项目名称', 'MakerDAO'],
                    ['项目类型', 'DeFi'],
                    ['项目领域', 'Stablecoin Protocol'],
                    ['仓库地址', f"{self.owner}/{self.repo}"],
                    ['总合并PR数', stats['total_prs']],
                    ['Vault相关PR数', stats['vault_prs']],
                    ['Governance相关PR数', stats['governance_prs']],
                    ['Stability相关PR数', stats['stability_prs']],
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

                # 6. MakerDAO功能分类
                if bug_candidates:
                    function_data = []
                    for candidate in bug_candidates:
                        functions = []
                        matches = candidate['makerdao_keyword_matches'] + candidate['makerdao_bug_matches']

                        if any('vault' in match or 'cdp' in match or 'liquidat' in match for match in matches):
                            functions.append('Vault')
                        if any('governance' in match or 'vote' in match or 'spell' in match for match in matches):
                            functions.append('Governance')
                        if any('dai' in match or 'stability' in match or 'rate' in match for match in matches):
                            functions.append('Stability')

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

        print(f"📁 MakerDAO DSS结果已导出到: {excel_file}")
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
        print("🚀 开始收集MakerDAO DSS已合并的PR...")
        print("📖 实验流程：专门分析Solidity智能合约仓库")
        print("🔗 项目：MakerDAO - 去中心化稳定币协议")
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

        print(f"\n✅ MakerDAO DSS数据收集完成！")
        print(f"📊 结果摘要:")
        print(f"   - 项目: MakerDAO")
        print(f"   - 类型: DeFi")
        print(f"   - 领域: Stablecoin Protocol")
        print(f"   - 总合并PR: {len(merged_prs)}")
        print(f"   - Vault功能PR: {stats['vault_prs']}")
        print(f"   - Governance功能PR: {stats['governance_prs']}")
        print(f"   - Stability功能PR: {stats['stability_prs']}")
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
        print(f"   4. 分析DeFi协议的特有bug模式")


if __name__ == "__main__":
    collector = MakerDAODSSCollector()
    collector.run_collection()