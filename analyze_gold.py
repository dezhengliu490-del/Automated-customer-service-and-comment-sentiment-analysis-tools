
import pandas as pd
import numpy as np

# 加载数据
gold_path = r'e:\work\bs\Automated customer service and comment sentiment analysis tools\data\Fourth Week Gold Test Set.csv'
ai_path = r'e:\work\bs\Automated customer service and comment sentiment analysis tools\data\gold_200_end.csv'

df_gold = pd.read_csv(gold_path)
df_ai = pd.read_csv(ai_path)

# 对齐 ID
df_gold['id_num'] = df_gold['评论ID'].str.extract(r'(\d+)').astype(int)
df_ai['id_num'] = df_ai['index'] + 1

# 合并
df = pd.merge(df_gold, df_ai, on='id_num')

# 映射情感标签
# 用户要求：将中性视为正面
def map_sentiment(s):
    if s == 'negative':
        return 0
    elif s in ['positive', 'neutral']:
        return 1
    return -1

df['ai_sentiment_mapped'] = df['sentiment'].apply(map_sentiment)
df['gold_sentiment'] = df['情感倾向（0=负面，1=正面）']

# 手动计算指标
y_true = df['gold_sentiment'].values
y_pred = df['ai_sentiment_mapped'].values

total = len(y_true)
correct = (y_true == y_pred).sum()
accuracy = correct / total

# 正面 (1)
tp_pos = ((y_true == 1) & (y_pred == 1)).sum()
fp_pos = ((y_true == 0) & (y_pred == 1)).sum()
fn_pos = ((y_true == 1) & (y_pred == 0)).sum()
recall_pos = tp_pos / (tp_pos + fn_pos) if (tp_pos + fn_pos) > 0 else 0
precision_pos = tp_pos / (tp_pos + fp_pos) if (tp_pos + fp_pos) > 0 else 0

# 负面 (0)
tp_neg = ((y_true == 0) & (y_pred == 0)).sum()
fp_neg = ((y_true == 1) & (y_pred == 0)).sum()
fn_neg = ((y_true == 0) & (y_pred == 1)).sum()
recall_neg = tp_neg / (tp_neg + fn_neg) if (tp_neg + fn_neg) > 0 else 0
precision_neg = tp_neg / (tp_neg + fp_neg) if (tp_neg + fp_neg) > 0 else 0

print(f"--- 情感分析性能指标 (中性视为正面) ---")
print(f"准确率 (Accuracy): {accuracy:.2%}")
print(f"正面召回率 (Recall Positive): {recall_pos:.2%}")
print(f"负面召回率 (Recall Negative): {recall_neg:.2%}")
print(f"正面精确率 (Precision Positive): {precision_pos:.2%}")
print(f"负面精确率 (Precision Negative): {precision_neg:.2%}")

# 找出误判样本
mismatches = df[df['gold_sentiment'] != df['ai_sentiment_mapped']]
print(f"\n误判样本数量: {len(mismatches)}")

# 打印一些误判案例
print("\n--- 误判案例分析 ---")
for idx, row in mismatches.head(10).iterrows():
    print(f"ID: {row['评论ID']} | 黄金: {row['gold_sentiment']} | AI: {row['sentiment']} (Conf: {row['confidence']})")
    print(f"文本: {row['text'][:100]}...")
    print(f"AI摘要: {row['summary_zh']}")
    print(f"黄金痛点: {row['具体痛点（正面评论填“无”）']}")
    print(f"AI痛点: {row['pain_points']}")
    print("-" * 20)

# 对幻觉和语气的定性分析
print("\n--- 摘要与幻觉检测 ---")
# 选取一些置信度较低或情感复杂的样本进行分析
suspicious = df[(df['confidence'] < 0.8) | (df['sentiment'] == 'neutral')].head(5)
for idx, row in suspicious.iterrows():
    print(f"ID: {row['评论ID']} | AI情感: {row['sentiment']} (Conf: {row['confidence']})")
    print(f"文本: {row['text']}")
    print(f"AI摘要: {row['summary_zh']}")
    print(f"AI痛点: {row['pain_points']}")
    print("-" * 20)

# 保存误判数据供详细报告使用
mismatches.to_csv(r'e:\work\bs\Automated customer service and comment sentiment analysis tools\data\mismatches_analysis.csv', index=False)
