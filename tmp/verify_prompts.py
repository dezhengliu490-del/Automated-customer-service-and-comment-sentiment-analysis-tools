import sys
import os

# Add backend to path
sys.path.append(os.path.abspath('e:/work/bs/Automated customer service and comment sentiment analysis tools/backend'))

from prompts import REPLY_SYSTEM_INSTRUCTION, build_reply_user_prompt

def test_reply_generation():
    test_cases = [
        {
            "review": "这个酒店硬件还可以,但服务太差.首先酒店任何员工对客人都没有应有的尊重,客人可以被他们呼来呵去...",
            "sentiment": "negative",
            "pain_points": ["服务态度差", "员工不专业", "Check-in效率低"]
        },
        {
            "review": "苹果很好，买给儿子吃的。物流也很快！",
            "sentiment": "positive",
            "pain_points": []
        },
        {
            "review": "挺不错的，房间很敞亮，没有压抑感，看上去很干净，只是洗澡的地方有点小，不过水很大。",
            "sentiment": "neutral",
            "pain_points": ["洗澡间偏小"]
        }
    ]

    print("--- REPLY SYSTEM INSTRUCTION ---")
    print(REPLY_SYSTEM_INSTRUCTION)
    print("\n" + "="*50 + "\n")

    for i, case in enumerate(test_cases):
        prompt = build_reply_user_prompt(case["review"], case["sentiment"], case["pain_points"])
        print(f"Test Case {i+1}:")
        print(prompt)
        print("-" * 30)

if __name__ == "__main__":
    test_reply_generation()
