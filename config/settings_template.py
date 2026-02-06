import os

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_token_from_local():
    """从本地配置文件读取token"""
    try:
        from config.local_settings import GITHUB_TOKEN
        return GITHUB_TOKEN
    except ImportError:
        print("⚠️  请创建 config/local_settings.py 文件并设置您的 GITHUB_TOKEN")
        print("   或设置环境变量: set GITHUB_TOKEN=your_token_here")
        return None

# GitHub API配置 - 从环境变量或本地配置文件读取
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or get_token_from_local()

# The Graph Contracts配置
THEGRAPH_CONFIG = {
    'owner': 'graphprotocol',
    'repo': 'contracts',  # 专门的Solidity合约仓库
    'output_dir': './output',
    'cache_dir': './data/cache',
    'excel_output': './output/excel',
    'reports_output': './output/reports'
}

TORNADO_CONFIG = {
    'owner': 'tornadocash',
    'repo': 'tornado-core',
    'output_dir': './output/tornado_cash',
    'cache_dir': './data/cache/tornado_cash',
    'excel_output': './output/tornado_cash/excel',
    'reports_output': './output/tornado_cash/reports'
}

# MakerDAO DSS配置
MAKERDAO_CONFIG = {
    'owner': 'makerdao',
    'repo': 'dss',
    'output_dir': './output/makerdao_dss',
    'cache_dir': './data/cache/makerdao_dss',
    'excel_output': './output/makerdao_dss/excel',
    'reports_output': './output/makerdao_dss/reports'
}

# Rocket Pool配置
ROCKETPOOL_CONFIG = {
    'owner': 'rocket-pool',
    'repo': 'rocketpool',
    'output_dir': './output/rocket_pool',
    'cache_dir': './data/cache/rocket_pool',
    'excel_output': './output/rocket_pool/excel',
    'reports_output': './output/rocket_pool/reports'
}

# zkSync Era配置
ZKSYNC_CONFIG = {
    'owner': 'matter-labs',
    'repo': 'era-contracts',
    'output_dir': './output/zksync_era',
    'cache_dir': './data/cache/zksync_era',
    'excel_output': './output/zksync_era/excel',
    'reports_output': './output/zksync_era/reports'
}

# Solmate 配置
SOLMATE_CONFIG = {
    'owner': 'transmissions11',
    'repo': 'solmate',
    'output_dir': './output/solmate',
    'cache_dir': './data/cache/solmate',
    'excel_output': './output/solmate/excel',
    'reports_output': './output/solmate/reports'
}

# 创建 Solmate 必要的目录
for dir_path in [SOLMATE_CONFIG['output_dir'],
                 SOLMATE_CONFIG['cache_dir'],
                 SOLMATE_CONFIG['excel_output'],
                 SOLMATE_CONFIG['reports_output']]:
    os.makedirs(dir_path, exist_ok=True)

# Vectorized/solady 配置
SOLADY_CONFIG = {
    'owner': 'Vectorized',
    'repo': 'solady',
    'output_dir': './output/solady',
    'cache_dir': './data/cache/solady',
    'excel_output': './output/solady/excel',
    'reports_output': './output/solady/reports'
}

# 创建 Solady 必要的目录
for dir_path in [SOLADY_CONFIG['output_dir'],
                 SOLADY_CONFIG['cache_dir'],
                 SOLADY_CONFIG['excel_output'],
                 SOLADY_CONFIG['reports_output']]:
    os.makedirs(dir_path, exist_ok=True)

# Lens Protocol 配置
LENS_CONFIG = {
    'owner': 'lens-protocol',
    'repo': 'core',
    'output_dir': './output/lens',
    'cache_dir': './data/cache/lens',
    'excel_output': './output/lens/excel',
    'reports_output': './output/lens/reports'
}

# 创建 Lens 必要的目录
for dir_path in [LENS_CONFIG['output_dir'],
                 LENS_CONFIG['cache_dir'],
                 LENS_CONFIG['excel_output'],
                 LENS_CONFIG['reports_output']]:
    os.makedirs(dir_path, exist_ok=True)

# AirCash 配置 
AIRCASH_CONFIG = {
    'owner': 'Aircoin-official',
    'repo': 'AirCash',
    'output_dir': './output/aircash',
    'cache_dir': './data/cache/aircash',
    'excel_output': './output/aircash/excel',
    'reports_output': './output/aircash/reports'
}

# 创建 AirCash 必要的目录
for dir_path in [AIRCASH_CONFIG['output_dir'],
                 AIRCASH_CONFIG['cache_dir'],
                 AIRCASH_CONFIG['excel_output'],
                 AIRCASH_CONFIG['reports_output']]:
    os.makedirs(dir_path, exist_ok=True)

    # OpenZeppelin 配置
    OPENZEPPELIN_CONFIG = {
        'owner': 'OpenZeppelin',
        'repo': 'openzeppelin-contracts',
        'output_dir': './output/openzeppelin',
        'cache_dir': './data/cache/openzeppelin',
        'excel_output': './output/openzeppelin/excel',
        'reports_output': './output/openzeppelin/reports'
    }

    # 创建 OpenZeppelin 必要的目录
    for dir_path in [OPENZEPPELIN_CONFIG['output_dir'],
                     OPENZEPPELIN_CONFIG['cache_dir'],
                     OPENZEPPELIN_CONFIG['excel_output'],
                     OPENZEPPELIN_CONFIG['reports_output']]:
        os.makedirs(dir_path, exist_ok=True)

# API请求配置
API_CONFIG = {
    'max_retries': 5,
    'retry_delay': 3,
    'requests_per_minute': 30,
    'timeout': 30
}

# 创建必要的目录
for dir_path in [THEGRAPH_CONFIG['output_dir'],
                 THEGRAPH_CONFIG['cache_dir'],
                 THEGRAPH_CONFIG['excel_output'],
                 THEGRAPH_CONFIG['reports_output']]:
    os.makedirs(dir_path, exist_ok=True)

# 创建MakerDAO必要的目录
for dir_path in [MAKERDAO_CONFIG['output_dir'],
                 MAKERDAO_CONFIG['cache_dir'],
                 MAKERDAO_CONFIG['excel_output'],
                 MAKERDAO_CONFIG['reports_output']]:
    os.makedirs(dir_path, exist_ok=True)

# 创建Rocket Pool必要的目录
for dir_path in [ROCKETPOOL_CONFIG['output_dir'],
                 ROCKETPOOL_CONFIG['cache_dir'],
                 ROCKETPOOL_CONFIG['excel_output'],
                 ROCKETPOOL_CONFIG['reports_output']]:
    os.makedirs(dir_path, exist_ok=True)

# 创建zkSync Era必要的目录
for dir_path in [ZKSYNC_CONFIG['output_dir'],
                 ZKSYNC_CONFIG['cache_dir'],
                 ZKSYNC_CONFIG['excel_output'],
                 ZKSYNC_CONFIG['reports_output']]:
    os.makedirs(dir_path, exist_ok=True)

# Seaport (OpenSea) 配置
SEAPORT_CONFIG = {
    'owner': 'ProjectOpenSea',
    'repo': 'seaport',
    'output_dir': './output/seaport',
    'cache_dir': './data/cache/seaport',
    'excel_output': './output/seaport/excel',
    'reports_output': './output/seaport/reports'
}

# 创建 Seaport 必要的目录
for dir_path in [SEAPORT_CONFIG['output_dir'],
                 SEAPORT_CONFIG['cache_dir'],
                 SEAPORT_CONFIG['excel_output'],
                 SEAPORT_CONFIG['reports_output']]:
    os.makedirs(dir_path, exist_ok=True)

# 验证 Seaport 配置
if GITHUB_TOKEN:
    print("✅ Seaport 配置文件加载完成")


# SidraChain 配置
SIDRA_CONFIG = {
    'owner': 'SidraChain',
    'repo': 'sidra-contracts',
    'excel_output': 'data/output',
    'min_score_threshold': 5,
}

# 新增 LayerZero 配置
LAYERZERO_CONFIG = {
    'owner': 'LayerZero-Labs',
    'repo': 'LayerZero-v1',
    'excel_output': 'data/output',
    'min_score_threshold': 5, # 筛选缺陷的最低分
}

# 新增 Thirdweb 配置
THIRDWEB_CONFIG = {
    'owner': 'thirdweb-dev',
    'repo': 'contracts',
    'excel_output': 'data/output',
    'min_score_threshold': 5, # 筛选缺陷的最低分
}

# 新增 Nibbstack 配置
NIBBSTACK_CONFIG = {
    'owner': 'nibbstack',
    'repo': 'erc721',
    'excel_output': 'data/output',
    'min_score_threshold': 5,
}

# 验证token是否加载成功
if GITHUB_TOKEN:
    print("✅ The Graph配置文件加载完成，GitHub Token已设置")
    print("✅ MakerDAO配置文件加载完成")
    print("✅ Rocket Pool配置文件加载完成")
    print("✅ zkSync Era配置文件加载完成")
else:
    print("❌ GitHub Token未设置，请检查配置")