import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
import pandas as pd
import json
import re
from datetime import datetime
from config.settings_template import GITHUB_TOKEN, ZKSYNC_CONFIG


class zkSyncEraCollector:
    def __init__(self):
        self.headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        self.owner = ZKSYNC_CONFIG['owner']
        self.repo = ZKSYNC_CONFIG['repo']
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

        # 通用bug相关关键词（与原研究保持一致）
        self.general_bug_keywords = [
            'bug', 'fix', 'repair', 'defect', 'vulnerability', 'issue',
            'error', 'problem', 'incorrect', 'wrong', 'fail', 'crash',
            'security', 'exploit', 'attack', 'overflow', 'underflow',
            'reentrancy', 'gas', 'optimization', 'revert', 'panic'
        ]

        # zkSync Era特定关键词
        self.zksync_keywords = [
            # 核心Layer 2概念
            'rollup', 'layer2', 'l2', 'l1', 'sequencer', 'batch', 'commit',
            'prove', 'execute', 'finalize', 'finalization', 'verification',

            # 零知识证明相关
            'zkproof', 'proof', 'prover', 'verifier', 'circuit', 'witness',
            'plonk', 'recursion', 'aggregation', 'snark', 'stark', 'commitment',
            'merkle', 'polynomial', 'constraint', 'trusted', 'setup',

            # zkEVM和虚拟机
            'zkevm', 'vm', 'virtual', 'machine', 'opcode', 'bytecode',
            'execution', 'trace', 'memory', 'storage', 'stack', 'precompile',
            'intrinsic', 'simulation', 'interpreter', 'compilation',

            # 桥接和跨链
            'bridge', 'deposit', 'withdrawal', 'l1tol2', 'l2tol1', 'message',
            'cross', 'chain', 'mailbox', 'priority', 'queue', 'relay',
            'confirm', 'portal', 'messenger', 'transfer', 'lock', 'mint', 'burn',

            # 账户抽象
            'account', 'abstraction', 'aa', 'paymaster', 'factory', 'wallet',
            'signature', 'validation', 'nonce', 'sponsor', 'meta', 'transaction',
            'userops', 'operation', 'bundler', 'entrypoint', 'paymasterflow',

            # 交易和批次处理
            'transaction', 'tx', 'batch', 'commit', 'prove', 'execute',
            'priority', 'l2block', 'bootloader', 'compressed', 'calldata',
            'pubdata', 'overhead', 'encoding', 'decoding', 'hash',

            # Gas和费用机制
            'gas', 'fee', 'limit', 'price', 'estimation', 'computation',
            'ergs', 'cost', 'refund', 'surplus', 'overhead', 'intrinsic',
            'l2gas', 'l1gas', 'compensation', 'pricing', 'metering',

            # 状态管理
            'state', 'diff', 'tree', 'root', 'leaf', 'branch', 'node',
            'sparse', 'patricia', 'storage', 'commitment', 'update',
            'transition', 'snapshot', 'checkpoint', 'rollback', 'revert',

            # 系统合约
            'system', 'contract', 'deployer', 'compressor', 'known',
            'code', 'hash', 'registry', 'force', 'deploy', 'immutable',
            'simulator', 'context', 'meta', 'call', 'mimic',

            # 升级和治理
            'upgrade', 'governance', 'admin', 'diamond', 'facet', 'proxy',
            'implementation', 'transparent', 'beacon', 'timelock', 'delay',
            'proposal', 'execution', 'shadow', 'freeze', 'unfreeze',

            # 验证和校验
            'verify', 'validation', 'check', 'ensure', 'require', 'assert',
            'invariant', 'constraint', 'condition', 'precondition', 'postcondition',
            'safety', 'liveness', 'soundness', 'completeness', 'correctness',

            # 网络和同步
            'sync', 'reorg', 'fork', 'chain', 'head', 'canonical', 'consensus',
            'peer', 'network', 'protocol', 'handshake', 'discovery', 'gossip',
            'mempool', 'pending', 'confirmed', 'finalized', 'orphan',

            # 存储和数据结构
            'storage', 'slot', 'key', 'value', 'mapping', 'array', 'struct',
            'packed', 'unpacked', 'layout', 'offset', 'size', 'alignment',
            'compression', 'decompression', 'serialization', 'encoding',

            # 密码学和安全
            'crypto', 'hash', 'keccak', 'sha256', 'ecdsa', 'secp256k1',
            'signature', 'recovery', 'address', 'public', 'private', 'key',
            'random', 'nonce', 'salt', 'entropy', 'secure', 'audit',

            # zkSync特有组件
            'zksync', 'era', 'matter', 'labs', 'boojum', 'circuit',
            'fri', 'goldilocks', 'poseidon', 'rescue', 'algebraic', 'field'
        ]

        # 合并所有关键词
        self.bug_keywords = self.general_bug_keywords + self.zksync_keywords

        self.merged_prs = []

    def collect_all_merged_prs(self):
        """收集所有已合并的PR"""
        print("📥 正在收集zkSync Era所有已合并的PR...")
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
                        'project_name': 'zkSync Era',
                        'project_type': 'Layer 2',
                        'project_domain': 'Ethereum ZK-Rollup Scaling Solution',
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
        print("📊 分析zkSync Era已合并的PR...")

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

        # zkSync Era特定分析
        zk_proof_keywords = ['proof', 'prover', 'verifier', 'circuit', 'plonk', 'recursion', 'aggregation']
        bridge_keywords = ['bridge', 'deposit', 'withdrawal', 'l1tol2', 'l2tol1', 'cross', 'chain']
        aa_keywords = ['account', 'abstraction', 'paymaster', 'factory', 'userops', 'sponsor']
        gas_keywords = ['gas', 'fee', 'ergs', 'estimation', 'pricing', 'computation', 'overhead']
        batch_keywords = ['batch', 'commit', 'prove', 'execute', 'sequencer', 'priority', 'bootloader']
        upgrade_keywords = ['upgrade', 'governance', 'diamond', 'facet', 'proxy', 'timelock']

        zk_proof_prs = [pr for pr in merged_prs
                        if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                               for keyword in zk_proof_keywords)]

        bridge_prs = [pr for pr in merged_prs
                      if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                             for keyword in bridge_keywords)]

        aa_prs = [pr for pr in merged_prs
                  if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                         for keyword in aa_keywords)]

        gas_prs = [pr for pr in merged_prs
                   if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                          for keyword in gas_keywords)]

        batch_prs = [pr for pr in merged_prs
                     if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                            for keyword in batch_keywords)]

        upgrade_prs = [pr for pr in merged_prs
                       if any(keyword in pr['title'].lower() or keyword in pr['body'].lower()
                              for keyword in upgrade_keywords)]

        print(f"📈 zkSync Era统计结果:")
        print(f"   - 总合并PR数: {total_prs}")
        print(f"   - ZK证明相关PR数: {len(zk_proof_prs)}")
        print(f"   - 桥接相关PR数: {len(bridge_prs)}")
        print(f"   - 账户抽象相关PR数: {len(aa_prs)}")
        print(f"   - Gas/费用相关PR数: {len(gas_prs)}")
        print(f"   - 批次处理相关PR数: {len(batch_prs)}")
        print(f"   - 升级治理相关PR数: {len(upgrade_prs)}")
        print(f"   - 最早合并日期: {min(dates) if dates else 'N/A'}")
        print(f"   - 最晚合并日期: {max(dates) if dates else 'N/A'}")
        print(
            f"   - 最活跃贡献者: {user_counts.head(1).index[0] if not user_counts.empty else 'N/A'} ({user_counts.iloc[0] if not user_counts.empty else 0} PRs)")
        print(f"   - 总代码行变更: +{total_additions:,} -{total_deletions:,}")
        print(f"   - 总文件变更: {total_files:,}")

        return {
            'total_prs': total_prs,
            'zk_proof_prs': len(zk_proof_prs),
            'bridge_prs': len(bridge_prs),
            'aa_prs': len(aa_prs),
            'gas_prs': len(gas_prs),
            'batch_prs': len(batch_prs),
            'upgrade_prs': len(upgrade_prs),
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
        print("🔍 识别zkSync Era bug修复相关的PR...")

        bug_candidates = []

        for pr in merged_prs:
            title_lower = pr['title'].lower()
            body_lower = pr['body'].lower()
            labels_lower = [label.lower() for label in pr['labels']]

            # 检查关键词匹配
            title_body_text = title_lower + ' ' + body_lower

            # 通用bug关键词匹配
            general_keyword_matches = [kw for kw in self.general_bug_keywords if kw in title_body_text]

            # zkSync Era特定关键词匹配
            zksync_keyword_matches = [kw for kw in self.zksync_keywords if kw in title_body_text]

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

            # zkSync Era特定的bug模式
            zksync_bug_patterns = [
                # 证明系统bug
                r'proof.*(?:fail|error|bug|invalid|generation|verification)',
                r'prover.*(?:fail|error|bug|crash|timeout|memory|overflow)',
                r'verifier.*(?:fail|error|bug|invalid|reject|accept|wrong)',
                r'circuit.*(?:fail|error|bug|constraint|synthesis|compile)',
                r'plonk.*(?:fail|error|bug|setup|commitment|polynomial)',
                r'recursion.*(?:fail|error|bug|aggregation|proof|depth)',
                r'witness.*(?:fail|error|bug|generation|invalid|missing)',

                # zkEVM相关bug
                r'zkevm.*(?:fail|error|bug|execution|trace|opcode|bytecode)',
                r'vm.*(?:fail|error|bug|execution|memory|storage|stack)',
                r'opcode.*(?:fail|error|bug|implementation|execution|gas)',
                r'precompile.*(?:fail|error|bug|call|result|gas|revert)',
                r'bytecode.*(?:fail|error|bug|compilation|deployment|hash)',
                r'execution.*(?:fail|error|bug|trace|revert|panic|out)',
                r'memory.*(?:fail|error|bug|allocation|access|overflow)',
                r'storage.*(?:fail|error|bug|access|write|read|slot|key)',

                # 桥接相关bug
                r'bridge.*(?:fail|error|bug|deposit|withdrawal|transfer)',
                r'deposit.*(?:fail|error|bug|amount|token|l1|l2|stuck)',
                r'withdrawal.*(?:fail|error|bug|proof|finalization|delay)',
                r'l1tol2.*(?:fail|error|bug|message|relay|execution)',
                r'l2tol1.*(?:fail|error|bug|message|proof|inclusion)',
                r'mailbox.*(?:fail|error|bug|queue|priority|execution)',
                r'cross.*chain.*(?:fail|error|bug|message|sync|state)',
                r'portal.*(?:fail|error|bug|entry|exit|validation)',

                # 账户抽象bug
                r'account.*abstraction.*(?:fail|error|bug|validation)',
                r'paymaster.*(?:fail|error|bug|sponsor|fee|validation|flow)',
                r'factory.*(?:fail|error|bug|deployment|creation|salt)',
                r'userops.*(?:fail|error|bug|bundler|execution|validation)',
                r'signature.*(?:fail|error|bug|validation|recovery|invalid)',
                r'nonce.*(?:fail|error|bug|management|sequence|replay)',
                r'meta.*transaction.*(?:fail|error|bug|execution|sponsor)',

                # Gas和费用bug
                r'gas.*(?:fail|error|bug|estimation|limit|price|computation)',
                r'ergs.*(?:fail|error|bug|calculation|conversion|limit)',
                r'fee.*(?:fail|error|bug|calculation|payment|refund|sponsor)',
                r'overhead.*(?:fail|error|bug|calculation|l1|l2|pubdata)',
                r'intrinsic.*(?:fail|error|bug|gas|cost|calculation)',
                r'pricing.*(?:fail|error|bug|model|calculation|update)',
                r'refund.*(?:fail|error|bug|calculation|excess|surplus)',

                # 批次处理bug
                r'batch.*(?:fail|error|bug|commit|prove|execute|priority)',
                r'sequencer.*(?:fail|error|bug|ordering|inclusion|reorg)',
                r'commit.*(?:fail|error|bug|hash|data|compression|pubdata)',
                r'prove.*(?:fail|error|bug|generation|aggregation|time)',
                r'execute.*(?:fail|error|bug|transaction|block|bootloader)',
                r'priority.*(?:fail|error|bug|queue|ordering|timeout)',
                r'bootloader.*(?:fail|error|bug|execution|gas|memory)',
                r'compressed.*(?:fail|error|bug|data|encoding|decoding)',

                # 状态管理bug
                r'state.*(?:fail|error|bug|transition|diff|tree|root)',
                r'merkle.*(?:fail|error|bug|tree|proof|root|leaf|path)',
                r'storage.*tree.*(?:fail|error|bug|update|commit|sparse)',
                r'diff.*(?:fail|error|bug|calculation|compression|application)',
                r'rollback.*(?:fail|error|bug|revert|state|transaction)',
                r'checkpoint.*(?:fail|error|bug|creation|restoration)',
                r'snapshot.*(?:fail|error|bug|state|inconsistent|corrupt)',

                # 升级和治理bug
                r'upgrade.*(?:fail|error|bug|proxy|implementation|diamond)',
                r'governance.*(?:fail|error|bug|proposal|execution|timelock)',
                r'diamond.*(?:fail|error|bug|facet|cut|selector|storage)',
                r'proxy.*(?:fail|error|bug|delegate|call|storage|collision)',
                r'timelock.*(?:fail|error|bug|delay|execution|cancel)',
                r'freeze.*(?:fail|error|bug|emergency|unfreeze|governance)',

                # 同步和网络bug
                r'sync.*(?:fail|error|bug|block|state|peer|network)',
                r'reorg.*(?:fail|error|bug|chain|canonical|fork|handle)',
                r'fork.*(?:fail|error|bug|choice|resolution|consensus)',
                r'consensus.*(?:fail|error|bug|agreement|finality|safety)',
                r'mempool.*(?:fail|error|bug|transaction|ordering|full)',
                r'pending.*(?:fail|error|bug|transaction|inclusion|timeout)',

                # 密码学相关bug
                r'hash.*(?:fail|error|bug|collision|preimage|keccak|sha)',
                r'signature.*(?:fail|error|bug|ecdsa|recovery|malleability)',
                r'address.*(?:fail|error|bug|derivation|collision|zero)',
                r'random.*(?:fail|error|bug|entropy|seed|predictable|weak)',
                r'crypto.*(?:fail|error|bug|primitive|implementation|side)',

                # 数据编码解码bug
                r'encoding.*(?:fail|error|bug|rlp|abi|calldata|pubdata)',
                r'decoding.*(?:fail|error|bug|parsing|validation|format)',
                r'serialization.*(?:fail|error|bug|format|version|compat)',
                r'compression.*(?:fail|error|bug|ratio|algorithm|data)',
                r'calldata.*(?:fail|error|bug|encoding|size|limit|cost)'
            ]

            zksync_bug_matches = []
            for pattern in zksync_bug_patterns:
                zksync_bug_matches.extend(re.findall(pattern, title_body_text))

            # 计算匹配分数（与原研究方法论一致）
            match_score = (len(general_keyword_matches) +
                           len(label_matches) +
                           len(fix_references) +
                           len(zksync_bug_matches))

            if general_keyword_matches or label_matches or fix_references or zksync_bug_matches:
                confidence = 'high' if match_score >= 3 else 'medium' if match_score >= 1 else 'low'

                bug_candidates.append({
                    **pr,
                    'general_keyword_matches': general_keyword_matches,
                    'zksync_keyword_matches': zksync_keyword_matches,
                    'label_matches': label_matches,
                    'fix_references': fix_references,
                    'zksync_bug_matches': zksync_bug_matches,
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

        # 按zkSync Era功能分类统计
        proof_bugs = len([c for c in bug_candidates if any('proof' in match or 'prover' in match or 'circuit' in match
                                                           for match in
                                                           c['zksync_keyword_matches'] + c['zksync_bug_matches'])])
        bridge_bugs = len(
            [c for c in bug_candidates if any('bridge' in match or 'deposit' in match or 'withdrawal' in match
                                              for match in c['zksync_keyword_matches'] + c['zksync_bug_matches'])])
        aa_bugs = len([c for c in bug_candidates if any('account' in match or 'paymaster' in match or 'userops' in match
                                                        for match in
                                                        c['zksync_keyword_matches'] + c['zksync_bug_matches'])])
        gas_bugs = len([c for c in bug_candidates if any('gas' in match or 'fee' in match or 'ergs' in match
                                                         for match in
                                                         c['zksync_keyword_matches'] + c['zksync_bug_matches'])])
        batch_bugs = len([c for c in bug_candidates if any('batch' in match or 'sequencer' in match or 'commit' in match
                                                           for match in
                                                           c['zksync_keyword_matches'] + c['zksync_bug_matches'])])

        print(f"   - ZK证明相关bug: {proof_bugs}")
        print(f"   - 桥接相关bug: {bridge_bugs}")
        print(f"   - 账户抽象相关bug: {aa_bugs}")
        print(f"   - Gas/费用相关bug: {gas_bugs}")
        print(f"   - 批次处理相关bug: {batch_bugs}")

        return bug_candidates

    def export_results(self, merged_prs, bug_candidates, stats):
        """导出结果到Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 使用绝对路径，确保目录创建
        excel_dir = os.path.abspath(ZKSYNC_CONFIG['excel_output'])
        os.makedirs(excel_dir, exist_ok=True)

        excel_file = os.path.join(excel_dir, f"zksync_era_{timestamp}.xlsx")

        print(f"📂 正在创建Excel文件...")
        print(f"   目录: {excel_dir}")
        print(f"   文件: zksync_era_{timestamp}.xlsx")

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
                        'general_keyword_matches', 'zksync_keyword_matches', 'label_matches',
                        'project_name', 'project_type', 'project_domain', 'url'
                    ]].copy()

                    # 格式化匹配结果
                    bug_display_df['general_keyword_matches'] = bug_display_df['general_keyword_matches'].apply(
                        lambda x: ', '.join(x[:5]))
                    bug_display_df['zksync_keyword_matches'] = bug_display_df['zksync_keyword_matches'].apply(
                        lambda x: ', '.join(x[:5]))
                    bug_display_df['label_matches'] = bug_display_df['label_matches'].apply(lambda x: ', '.join(x))

                    bug_display_df.to_excel(writer, sheet_name='Bug_Fix_Candidates', index=False)

                # 3. 统计信息
                stats_data = [
                    ['项目名称', 'zkSync Era'],
                    ['项目类型', 'Layer 2'],
                    ['项目领域', 'Ethereum ZK-Rollup Scaling Solution'],
                    ['仓库地址', f"{self.owner}/{self.repo}"],
                    ['总合并PR数', stats['total_prs']],
                    ['ZK证明相关PR数', stats['zk_proof_prs']],
                    ['桥接相关PR数', stats['bridge_prs']],
                    ['账户抽象相关PR数', stats['aa_prs']],
                    ['Gas/费用相关PR数', stats['gas_prs']],
                    ['批次处理相关PR数', stats['batch_prs']],
                    ['升级治理相关PR数', stats['upgrade_prs']],
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

                # 6. zkSync Era功能分类
                if bug_candidates:
                    function_data = []
                    for candidate in bug_candidates:
                        functions = []
                        matches = candidate['zksync_keyword_matches'] + candidate['zksync_bug_matches']

                        if any('proof' in match or 'prover' in match or 'circuit' in match for match in matches):
                            functions.append('ZK_Proof')
                        if any('bridge' in match or 'deposit' in match or 'withdrawal' in match for match in matches):
                            functions.append('Bridge')
                        if any('account' in match or 'paymaster' in match or 'userops' in match for match in matches):
                            functions.append('Account_Abstraction')
                        if any('gas' in match or 'fee' in match or 'ergs' in match for match in matches):
                            functions.append('Gas_Fee')
                        if any('batch' in match or 'sequencer' in match or 'commit' in match for match in matches):
                            functions.append('Batch_Processing')
                        if any('upgrade' in match or 'governance' in match or 'diamond' in match for match in matches):
                            functions.append('Upgrade_Governance')

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

        print(f"📁 zkSync Era结果已导出到: {excel_file}")
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
        print("🚀 开始收集zkSync Era已合并的PR...")
        print("📖 实验流程：专门分析Solidity智能合约仓库")
        print("🔗 项目：zkSync Era - 零知识证明以太坊Layer 2扩容方案")
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

        print(f"\n✅ zkSync Era数据收集完成！")
        print(f"📊 结果摘要:")
        print(f"   - 项目: zkSync Era")
        print(f"   - 类型: Layer 2")
        print(f"   - 领域: Ethereum ZK-Rollup Scaling Solution")
        print(f"   - 总合并PR: {len(merged_prs)}")
        print(f"   - ZK证明功能PR: {stats['zk_proof_prs']}")
        print(f"   - 桥接功能PR: {stats['bridge_prs']}")
        print(f"   - 账户抽象功能PR: {stats['aa_prs']}")
        print(f"   - Gas/费用功能PR: {stats['gas_prs']}")
        print(f"   - 批次处理功能PR: {stats['batch_prs']}")
        print(f"   - 升级治理功能PR: {stats['upgrade_prs']}")
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
        print(f"   4. 分析Layer 2 ZK-Rollup的特有bug模式")
        print(f"   5. 重点关注证明系统、桥接、账户抽象、Gas机制等模块")


if __name__ == "__main__":
    collector = zkSyncEraCollector()
    collector.run_collection()