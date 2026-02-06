import requests
import sys
import os
import time
from datetime import datetime, timedelta

# 路径配置
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from config.settings_template import GITHUB_TOKEN
except ImportError:
    print("⚠️ 警告: 未找到配置文件，请确保 config/settings_template.py 存在且包含 GITHUB_TOKEN")
    GITHUB_TOKEN = ""

# --- 配置参数 ---
MIN_STARS = 1000  # 最小 Star 数 (保证影响力/工业界认可)
MIN_SOLIDITY_PCT = 40.0  # 最小 Solidity 语言占比 (保证 PR 分析的相关性)
MIN_AGE_YEARS = 2.0  # 最小项目年龄 (保证成熟度)

# --- 排除列表 (已分析或正在分析的项目) ---
# 使用小写进行模糊匹配，确保这些项目及其变体被排除
EXCLUDED_KEYWORDS = [
    'openzeppelin',
    'synthetix',
    'aave',
    'uniswap',
    'compound',
    'graphprotocol', 'graph-node',  # TheGraph
    'makerdao', 'dss',  # MakerDAO
    'rocket-pool', 'rocketpool',  # RocketPool
    'zksync', 'era-contracts', 'matter-labs'  # zkSync Era
]


def is_excluded(owner, repo):
    """检查项目是否在排除列表中"""
    full_name = f"{owner}/{repo}".lower()
    for keyword in EXCLUDED_KEYWORDS:
        if keyword in full_name:
            return True
    return False


def get_github_headers():
    return {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }


def search_github_repositories():
    """
    使用 GitHub Search API 搜索所有符合条件的项目
    条件: language:Solidity, stars >= 1000, created < (now - 2 years)
    """
    if not GITHUB_TOKEN:
        print("❌ 错误: 缺少 GITHUB_TOKEN。")
        return

    # 计算日期阈值 (当前时间 - 2年)
    # 假设当前是 2025.5，则寻找 2023.5 之前的项目
    cutoff_date = (datetime.now() - timedelta(days=365.25 * MIN_AGE_YEARS)).strftime('%Y-%m-%d')

    # 构建查询语句
    # q=language:Solidity+stars:>=1000+created:<=YYYY-MM-DD
    query = f"language:Solidity stars:>={MIN_STARS} created:<={cutoff_date} sort:stars"

    print(f"🔍 正在全网搜索 GitHub 项目...")
    print(f"ℹ️  搜索条件: Language=Solidity | Stars>={MIN_STARS} | Created<={cutoff_date}")
    print(f"ℹ️  过滤条件: Solidity占比 >= {MIN_SOLIDITY_PCT}% (确保PR与合约强相关)")
    print("=" * 100)
    print(f"{'Rank':<4} | {'Repository':<40} | {'Stars':<7} | {'Age(Yr)':<7} | {'Sol%':<6} | {'Status'}")
    print("-" * 100)

    page = 1
    found_projects = []

    while True:
        # GitHub Search API 限制：每页最多100条，前1000条结果
        search_url = "https://api.github.com/search/repositories"
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 30,  # 每页30条
            'page': page
        }

        try:
            response = requests.get(search_url, headers=get_github_headers(), params=params, timeout=15)

            if response.status_code == 403:
                print("⚠️  API 速率限制，等待 30 秒...")
                time.sleep(30)
                continue

            if response.status_code != 200:
                print(f"❌ API 错误: {response.status_code} - {response.text}")
                break

            data = response.json()
            items = data.get('items', [])

            if not items:
                break  # 没有更多结果

            for item in items:
                owner = item['owner']['login']
                repo = item['name']
                stars = item['stargazers_count']
                created_at_str = item['created_at']

                # 1. 检查排除列表
                if is_excluded(owner, repo):
                    # 可以在这里打印被排除的项目，或者直接跳过
                    # print(f"SKIP | {owner}/{repo:<40} | (已在排除名单中)")
                    continue

                # 2. 计算年龄
                created_at = datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ")
                age_years = (datetime.now() - created_at).days / 365.25

                # 3. 获取详细语言分布 (这是耗时操作，所以只对通过初步筛选的项目做)
                solidity_pct = get_solidity_percentage(owner, repo)

                # 4. 最终判定
                if solidity_pct >= MIN_SOLIDITY_PCT:
                    status = "✅ 收录"
                    project_info = {
                        'repo': f"{owner}/{repo}",
                        'stars': stars,
                        'age': age_years,
                        'solidity_pct': solidity_pct,
                        'url': item['html_url'],
                        'description': item['description']
                    }
                    found_projects.append(project_info)

                    print(
                        f"{len(found_projects):<4} | {owner}/{repo:<40} | {stars:>7,} | {age_years:>7.1f} | {solidity_pct:>5.1f}% | {status}")
                else:
                    # 即使Star很高，如果Solidity占比低，也打印出来但标记为不收录，让你知道为什么没选它
                    print(
                        f"SKIP | {owner}/{repo:<40} | {stars:>7,} | {age_years:>7.1f} | {solidity_pct:>5.1f}% | ❌ Sol占比低")

            page += 1
            # GitHub Search API 限制只能访问前1000个结果 (约34页)
            if page > 34:
                break

            # 礼貌性延迟，防止触发滥用检测
            time.sleep(1)

        except Exception as e:
            print(f"❌ 发生异常: {e}")
            break

    # --- 输出最终结果 ---
    print("\n" + "=" * 100)
    print(f"🎉 搜索完成! 共找到 {len(found_projects)} 个符合所有条件的新项目。")
    print("=" * 100)

    # 保存到文件 (可选)
    # save_to_file(found_projects)

    return found_projects


def get_solidity_percentage(owner, repo):
    """获取仓库中 Solidity 代码的字节占比"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/languages"
        response = requests.get(url, headers=get_github_headers(), timeout=10)

        if response.status_code == 200:
            langs = response.json()
            total = sum(langs.values())
            if total == 0: return 0
            return (langs.get('Solidity', 0) / total) * 100
    except:
        pass
    return 0


if __name__ == "__main__":
    search_github_repositories()