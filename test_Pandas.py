import pandas as pd
import os

def test_csv_reader(file_path):
    # 1. 检查文件是否存在
    if not os.path.exists(file_path):
        print(f" 错误: 找不到文件 '{file_path}'")
        return

    try:
        # 2. 读取 CSV 文件
        # 这里使用了几个常用参数：encoding='utf-8' 处理编码，sep=',' 指定分隔符
        df = pd.read_csv(file_path)

        print(f"✅ 成功读取文件: {file_path}")
        print("-" * 30)

        # 3. 数据概览
        print(f" 数据维度: {df.shape[0]} 行 x {df.shape[1]} 列")
        print("\n前 5 行数据预览:")
        print(df.head())

        print("\n 列名列表:")
        print(df.columns.tolist())

        print("\nℹ数据类型摘要:")
        print(df.dtypes)

    except Exception as e:
        print(f" 读取过程中出错: {e}")

# --- 运行测试 ---
if __name__ == "__main__":
    test_csv_reader('online_shopping_10_cats.csv')