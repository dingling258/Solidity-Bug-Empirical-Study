import sys

print(f"Python版本: {sys.version}")
print(f"Python路径: {sys.executable}")

# 测试必需库
libraries = {
    'pandas': 'pandas',  # 修复这里：原来是'pd'，应该是'pandas'
    'requests': 'requests',
    'openpyxl': 'openpyxl',
    'json': 'json',
    'time': 'time',
    'os': 'os',
    're': 're'
}

print("\n=== 库安装检查 ===")
for lib_name, import_name in libraries.items():
    try:
        exec(f"import {import_name}")
        if hasattr(eval(import_name), '__version__'):
            version = eval(f"{import_name}.__version__")
            print(f"✅ {lib_name}: {version}")
        else:
            print(f"✅ {lib_name}: 已安装")
    except ImportError:
        print(f"❌ {lib_name}: 未安装")

print("\n=== 环境检查完成 ===")

# 额外的pandas功能测试
print("\n=== pandas功能测试 ===")
try:
    import pandas as pd
    import numpy as np

    # 创建一个简单的DataFrame测试
    test_df = pd.DataFrame({
        'A': [1, 2, 3],
        'B': ['a', 'b', 'c']
    })
    print("✅ pandas DataFrame创建成功")
    print("✅ 所有库工作正常，可以开始数据收集！")
except Exception as e:
    print(f"❌ pandas功能测试失败: {e}")