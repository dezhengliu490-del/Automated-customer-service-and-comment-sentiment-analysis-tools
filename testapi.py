import os
# 如果没有安装该库，请先运行: pip install google-genai
from google import genai

def main():
    # 1. 设置 API 密钥
    api_key = "AIzaSyCY3h__s6UaNWQPHh0gmbTPnZDWi16V4GM"

    # 2. 初始化 Gemini 客户端
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"初始化客户端失败: {e}")
        return

    # 3. 准备你要发送给模型的问题 (Prompt)
    prompt = "请用三句话向初学者解释什么是机器学习。"
    print(f"正在发送请求...\n问题: {prompt}\n")

    # 4. 调用模型生成内容
    try:
        # 推荐使用 gemini-2.5-flash，它速度快且功能强大
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # 5. 打印结果
        print("--- Gemini 的回复 ---")
        print(response.text)
        
    except Exception as e:
        print(f"API 调用过程中发生错误: {e}")

if __name__ == "__main__":
    main()