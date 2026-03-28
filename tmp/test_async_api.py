import asyncio
import sys
from pathlib import Path

# Add backend to sys.path
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from gemini_service import async_analyze_review_text_as_dict

async def test_async_call():
    test_text = "极简主义设计，非常好看，物流也很快！"
    try:
        print(f"Testing async call with text: {test_text}")
        result = await async_analyze_review_text_as_dict(test_text)
        print("Async call successful!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Async call failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_async_call())
