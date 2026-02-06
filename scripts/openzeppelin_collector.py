import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import pandas as pd
import json
import re
from datetime import datetime
from config.settings_template import GITHUB_TOKEN, OPENZEPPELIN_CONFIG


class OpenZeppelinCollector:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = OPENZEPPELIN_CONFIG['owner']
        self.repo = OPENZEPPELIN_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # 核心bug修复关键词（强信号）
        self.core_bug_keywords = [
            'bug', 'fix', 'defect', 'vulnerability', 'exploit', 'attack',
            'incorrect', 'wrong', 'fail', 'crash', 'revert', 'panic',
            'security', 'reentrancy', 'overflow', 'underflow'
        ]

        # 排除模式 - 明确不是bug修复的PR类型
        self.exclusion_patterns = [
            # 依赖和工具链更新
            r'^bump\s+',
            r'^update\s+dependency',
            r'^upgrade\s+dependency',
            r'^\[deps\]',
            r'^chore\(deps\)',
            r'dependabot',
            r'renovate',

            # 文档和注释
            r'^docs?[\:\(]',
            r'^documentation',
            r'^\[docs?\]',
            r'^update.*readme',
            r'^fix.*typo',
            r'^typo',
            r'^comment',
            r'natspec',

            # 格式化和代码风格
            r'^format',
            r'^lint',
            r'^style',
            r'^prettier',
            r'^eslint',
            r'^cleanup',

            # 构建和CI/CD
            r'^ci[\:\(]',
            r'^build[\:\(]',
            r'^\[ci\]',
            r'github.*action',
            r'workflow',

            # 版本和发布
            r'^release',
            r'^version',
            r'^changelog',
            r'^prepare.*release',

            # 测试（除非明确提到fix）
            r'^test(?!.*fix)',
            r'^add.*test(?!.*fix)',

            # 重构（除非明确提到fix）
            r'^refactor(?!.*fix)',
            r'^rename(?!.*fix)',
        ]

        # OpenZeppelin合约特定关键词
        self.oz_contract_keywords = [
            # ERC标准
            'erc20', 'erc721', 'erc777', 'erc1155', 'erc1967', 'erc2612',
            'erc2771', 'erc3156', 'erc4626', 'token', 'nft',

            # 访问控制
            'ownable', 'accesscontrol', 'role', 'permission',

            # 安全机制
            'reentrancyguard', 'pausable', 'nonreentrant',

            # 代理和升级
            'proxy', 'upgradeable', 'uups', 'transparent', 'beacon',
            'initializable', 'storage collision',

            # 数学
            'safemath', 'safeCast', 'math', 'checked arithmetic',

            # 加密
            'ecdsa', 'signature', 'merkle', 'eip712',

            # 治理
            'governor', 'timelock', 'votes', 'voting',
        ]

        self.merged_prs = []

    def should_exclude_pr(self, pr):
        """判断PR是否应该被排除（明确不是bug修复）"""
        title = pr['title'].lower()
        user = pr['user'].lower()

        # 检查用户是否是bot
        bot_users = ['dependabot', 'renovate', 'dependabot-preview']
        if any(bot in user for bot in bot_users):
            return True

        # 检查标题是否匹配排除模式
        for pattern in self.exclusion_patterns:
            if re.match(pattern, title, re.IGNORECASE):
                return True

        # 只修改非Solidity文件的PR
        changed_files = pr.get('changed_files', 0)
        if changed_files > 0:
            # 如果能获取到文件列表会更准确，这里用启发式规则
            # 如果标题提到文档、依赖、CI等，且没有强bug关键词，排除
            non_code_indicators = ['readme', 'docs', 'package.json', 'lock', '.yml', '.yaml', '.md']
            if any(indicator in title for indicator in non_code_indicators):
                if not any(keyword in title for keyword in ['fix', 'bug', 'security', 'vulnerability']):
                    return True

        return False

    def calculate_bug_fix_score(self, pr):
        """计算bug修复相关性分数（改进的评分系统）"""
        title_lower = pr['title'].lower()
        body_lower = pr['body'].lower()
        labels_lower = [label.lower() for label in pr['labels']]

        score = 0
        evidence = {
            'strong_signals': [],
            'medium_signals': [],
            'weak_signals': [],
            'core_keywords': [],
            'oz_keywords': [],
            'labels': [],
            'issue_refs': []
        }

        # === 强信号 (+5分每个) ===

        # 1. 标签包含bug/security/vulnerability
        security_labels = ['bug', 'security', 'vulnerability', 'critical', 'high-severity']
        found_labels = [label for label in labels_lower if any(sl in label for sl in security_labels)]
        if found_labels:
            score += 5 * len(found_labels)
            evidence['strong_signals'].append(f"Security labels: {found_labels}")
            evidence['labels'] = found_labels

        # 2. 标题明确包含 "fix" + bug关键词
        if 'fix' in title_lower:
            for keyword in ['bug', 'vulnerability', 'security', 'exploit', 'reentrancy', 'overflow', 'underflow']:
                if keyword in title_lower:
                    score += 5
                    evidence['strong_signals'].append(f"Title: 'fix' + '{keyword}'")
                    break

        # 3. 正文包含 "Fixes #数字" 或 "Closes #数字"
        issue_ref_patterns = [
            r'fixes?\s+#(\d+)',
            r'closes?\s+#(\d+)',
            r'resolves?\s+#(\d+)',
        ]
        for pattern in issue_ref_patterns:
            matches = re.findall(pattern, body_lower)
            if matches:
                score += 3 * len(matches)  # 每个issue引用+3分
                evidence['medium_signals'].append(f"Issue references: #{', #'.join(matches)}")
                evidence['issue_refs'] = matches
                break

        # 4. 标题/正文明确提到严重性
        severity_keywords = ['critical', 'severe', 'high severity', 'security issue', 'vulnerability']
        for keyword in severity_keywords:
            if keyword in title_lower or keyword in body_lower:
                score += 4
                evidence['strong_signals'].append(f"Severity keyword: '{keyword}'")
                break

        # === 中等信号 (+2-3分) ===

        # 5. 核心bug关键词匹配
        title_body_text = title_lower + ' ' + body_lower
        core_matches = [kw for kw in self.core_bug_keywords if kw in title_body_text]
        if core_matches:
            score += min(len(core_matches) * 2, 6)  # 最多+6分
            evidence['medium_signals'].append(f"Core bug keywords: {core_matches[:3]}")
            evidence['core_keywords'] = core_matches[:5]

        # 6. OpenZeppelin合约关键词 + bug相关词
        oz_matches = [kw for kw in self.oz_contract_keywords if kw in title_body_text]
        if oz_matches and any(bug_kw in title_body_text for bug_kw in ['bug', 'fix', 'issue', 'incorrect', 'wrong']):
            score += 3
            evidence['medium_signals'].append(f"OZ keywords + bug context: {oz_matches[:2]}")
            evidence['oz_keywords'] = oz_matches[:3]

        # === 弱信号 (+1分) ===

        # 7. 包含错误/问题相关词，但没有强信号
        weak_keywords = ['error', 'problem', 'issue', 'incorrect', 'unexpected']
        weak_matches = [kw for kw in weak_keywords if kw in title_body_text]
        if weak_matches and not evidence['strong_signals']:
            score += len(weak_matches)
            evidence['weak_signals'].append(f"Weak keywords: {weak_matches[:2]}")

        # 8. 代码变更规模合理（bug修复通常不会特别大）
        additions = pr.get('additions', 0)
        deletions = pr.get('deletions', 0)
        total_changes = additions + deletions

        # 中小规模变更更可能是bug修复
        if 10 <= total_changes <= 500:
            score += 1
            evidence['weak_signals'].append(f"Moderate code changes: {total_changes} lines")

        return score, evidence

    def collect_all_merged_prs(self):
        """收集所有已合并的PR"""
        print("📥 正在收集OpenZeppelin所有已合并的PR...")
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
                        'project_name': 'OpenZeppelin',
                        'project_type': 'Smart Contract Library',
                        'project_domain': 'Reusable Solidity Security Contracts',
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

            if page_merged_count == 0:
                break

            page += 1

        print(f"✅ 总共收集到 {len(merged_prs)} 个已合并的PR")
        return merged_prs

    def analyze_merged_prs(self, merged_prs):
        """分析已合并的PR"""
        print("📊 分析OpenZeppelin已合并的PR...")

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

        print(f"📈 OpenZeppelin统计结果:")
        print(f"   - 总合并PR数: {total_prs}")
        print(f"   - 最早合并日期: {min(dates) if dates else 'N/A'}")
        print(f"   - 最晚合并日期: {max(dates) if dates else 'N/A'}")
        print(
            f"   - 最活跃贡献者: {user_counts.head(1).index[0] if not user_counts.empty else 'N/A'} ({user_counts.iloc[0] if not user_counts.empty else 0} PRs)")
        print(f"   - 总代码行变更: +{total_additions:,} -{total_deletions:,}")
        print(f"   - 总文件变更: {total_files:,}")

        return {
            'total_prs': total_prs,
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
        """识别bug修复相关的PR（改进版）"""
        print("🔍 识别OpenZeppelin bug修复相关的PR...")
        print("   使用改进的评分系统，排除非bug修复PR...")

        bug_candidates = []
        excluded_count = 0

        for pr in merged_prs:
            # 第一步：检查是否应该排除
            if self.should_exclude_pr(pr):
                excluded_count += 1
                continue

            # 第二步：计算bug修复评分
            score, evidence = self.calculate_bug_fix_score(pr)

            # 只保留有一定分数的PR
            if score >= 3:  # 最低门槛：3分
                # 根据分数确定置信度
                if score >= 10:
                    confidence = 'high'
                elif score >= 6:
                    confidence = 'medium'
                else:
                    confidence = 'low'

                bug_candidates.append({
                    **pr,
                    'bug_fix_score': score,
                    'confidence': confidence,
                    'evidence': evidence,
                    'strong_signals': len(evidence['strong_signals']),
                    'medium_signals': len(evidence['medium_signals']),
                    'weak_signals': len(evidence['weak_signals']),
                })

        # 按分数降序排序
        bug_candidates.sort(key=lambda x: x['bug_fix_score'], reverse=True)

        print(f"✅ 从 {len(merged_prs)} 个合并PR中识别出 {len(bug_candidates)} 个疑似bug修复PR")
        print(f"   排除了 {excluded_count} 个明确非bug修复的PR（依赖更新、文档等）")

        # 按置信度分类
        high_confidence = len([c for c in bug_candidates if c['confidence'] == 'high'])
        medium_confidence = len([c for c in bug_candidates if c['confidence'] == 'medium'])
        low_confidence = len([c for c in bug_candidates if c['confidence'] == 'low'])

        print(f"\n   置信度分布:")
        print(f"   - 高置信度 (≥10分): {high_confidence}")
        print(f"   - 中置信度 (6-9分): {medium_confidence}")
        print(f"   - 低置信度 (3-5分): {low_confidence}")

        # 显示Top 10 bug修复PR
        print(f"\n   🏆 Top 10 bug修复候选PR:")
        for i, candidate in enumerate(bug_candidates[:10], 1):
            print(f"   {i}. #{candidate['number']} (分数: {candidate['bug_fix_score']}): {candidate['title'][:60]}")

        return bug_candidates

    def export_results(self, merged_prs, bug_candidates, stats):
        """导出结果到Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        excel_dir = os.path.abspath(OPENZEPPELIN_CONFIG['excel_output'])
        os.makedirs(excel_dir, exist_ok=True)

        excel_file = os.path.join(excel_dir, f"openzeppelin_{timestamp}.xlsx")

        print(f"\n📂 正在创建Excel文件...")
        print(f"   目录: {excel_dir}")
        print(f"   文件: openzeppelin_{timestamp}.xlsx")

        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # 1. 所有合并的PR
                merged_df = pd.DataFrame(merged_prs)
                merged_df.to_excel(writer, sheet_name='All_Merged_PRs', index=False)

                # 2. bug修复候选PR（按分数排序）
                if bug_candidates:
                    bug_df = pd.DataFrame(bug_candidates)

                    # 准备显示列
                    display_columns = [
                        'number', 'title', 'user', 'merged_at',
                        'bug_fix_score', 'confidence', 'strong_signals', 'medium_signals',
                        'url', 'labels', 'additions', 'deletions', 'changed_files'
                    ]

                    bug_display_df = bug_df[display_columns].copy()
                    bug_display_df['labels'] = bug_display_df['labels'].apply(lambda x: ', '.join(x) if x else '')

                    bug_display_df.to_excel(writer, sheet_name='Bug_Fix_Candidates', index=False)

                    # 3. 详细证据表
                    evidence_data = []
                    for candidate in bug_candidates:
                        ev = candidate['evidence']
                        evidence_data.append({
                            'PR_Number': candidate['number'],
                            'Title': candidate['title'],
                            'Score': candidate['bug_fix_score'],
                            'Confidence': candidate['confidence'],
                            'Strong_Signals': '; '.join(ev['strong_signals']),
                            'Medium_Signals': '; '.join(ev['medium_signals']),
                            'Weak_Signals': '; '.join(ev['weak_signals']),
                            'Core_Keywords': ', '.join(ev['core_keywords'][:5]),
                            'OZ_Keywords': ', '.join(ev['oz_keywords'][:5]),
                            'Labels': ', '.join(ev['labels']),
                            'Issue_Refs': ', '.join([f"#{ref}" for ref in ev['issue_refs']])
                        })

                    evidence_df = pd.DataFrame(evidence_data)
                    evidence_df.to_excel(writer, sheet_name='Evidence_Details', index=False)

                # 4. 统计信息
                stats_data = [
                    ['项目名称', 'OpenZeppelin'],
                    ['项目类型', 'Smart Contract Library'],
                    ['项目领域', 'Reusable Solidity Security Contracts'],
                    ['仓库地址', f"{self.owner}/{self.repo}"],
                    ['总合并PR数', stats['total_prs']],
                    ['疑似bug修复PR数', len(bug_candidates)],
                    ['高置信度bug修复', len([c for c in bug_candidates if c['confidence'] == 'high'])],
                    ['中置信度bug修复', len([c for c in bug_candidates if c['confidence'] == 'medium'])],
                    ['低置信度bug修复', len([c for c in bug_candidates if c['confidence'] == 'low'])],
                    ['最活跃贡献者', stats['user_counts'].index[0] if not stats['user_counts'].empty else 'N/A'],
                    ['总代码增加行数', stats['code_stats']['additions']],
                    ['总代码删除行数', stats['code_stats']['deletions']],
                    ['总变更文件数', stats['code_stats']['files']]
                ]

                stats_df = pd.DataFrame(stats_data, columns=['指标', '数值'])
                stats_df.to_excel(writer, sheet_name='Statistics', index=False)

                # 5. 分数分布
                if bug_candidates:
                    score_ranges = {
                        '15+分 (极高)': len([c for c in bug_candidates if c['bug_fix_score'] >= 15]),
                        '10-14分 (高)': len([c for c in bug_candidates if 10 <= c['bug_fix_score'] < 15]),
                        '6-9分 (中)': len([c for c in bug_candidates if 6 <= c['bug_fix_score'] < 10]),
                        '3-5分 (低)': len([c for c in bug_candidates if 3 <= c['bug_fix_score'] < 6]),
                    }

                    score_df = pd.DataFrame(list(score_ranges.items()), columns=['分数区间', '数量'])
                    score_df.to_excel(writer, sheet_name='Score_Distribution', index=False)

            if os.path.exists(excel_file):
                file_size = os.path.getsize(excel_file)
                print(f"✅ 文件创建成功！")
                print(f"   大小: {file_size:,} bytes")
            else:
                print(f"❌ 文件创建失败！")

        except Exception as e:
            print(f"❌ 导出Excel时出错: {e}")
            import traceback
            traceback.print_exc()
            excel_file = None

        print(f"📁 OpenZeppelin结果已导出到: {excel_file}")
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
        print("🚀 开始收集OpenZeppelin已合并的PR...")
        print("📖 实验流程：专门分析Solidity智能合约库")
        print("🔗 项目：OpenZeppelin - 可重用的安全智能合约标准")
        print(f"📁 仓库：{self.owner}/{self.repo}")
        print("\n🎯 改进的bug识别策略：")
        print("   ✅ 排除：依赖更新、文档修改、格式化、CI/CD等")
        print("   ✅ 强信号：security标签、fix+bug关键词、issue引用")
        print("   ✅ 评分系统：强信号5分、中等信号2-3分、弱信号1分")
        print("   ✅ 按分数排序：让真正的bug修复排在前面\n")

        # 1. 收集所有已合并的PR
        merged_prs = self.collect_all_merged_prs()

        if not merged_prs:
            print("❌ 没有找到已合并的PR")
            return

        # 2. 分析PR数据
        stats = self.analyze_merged_prs(merged_prs)

        # 3. 识别bug修复相关的PR（改进版）
        bug_candidates = self.identify_bug_fix_prs(merged_prs)

        # 4. 导出结果
        excel_file = self.export_results(merged_prs, bug_candidates, stats)

        print(f"\n✅ OpenZeppelin数据收集完成！")
        print(f"📊 结果摘要:")
        print(f"   - 项目: OpenZeppelin")
        print(f"   - 总合并PR: {len(merged_prs)}")
        print(f"   - 疑似bug修复: {len(bug_candidates)}")
        print(f"   - 高置信度: {len([c for c in bug_candidates if c['confidence'] == 'high'])}")
        print(f"   - 结果文件: {excel_file}")

        print(f"\n📋 下一步:")
        print(f"   1. 优先审核高分数（≥10分）的PR")
        print(f"   2. 查看Evidence_Details工作表了解评分依据")
        print(f"   3. 确认真正的bug修复实例")
        print(f"   4. 按DASP和智能合约特有缺陷分类")


if __name__ == "__main__":
    collector = OpenZeppelinCollector()
    collector.run_collection()