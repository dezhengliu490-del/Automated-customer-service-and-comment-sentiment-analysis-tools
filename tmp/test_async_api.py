import asyncio
import sys
import json
from pathlib import Path

# Add backend to sys.path
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from llm_factory import get_llm_service
from config import get_llm_provider

async def test_async_call():
    test_text = "极简主义设计，非常好看，物流也很快！"
    provider = get_llm_provider()
    try:
        print(f"Testing async call via Factory [{provider.upper()}] with text: {test_text}")
        
        # 1. 获取 LLM 服务
        service = get_llm_service()
        
        # 2. 异步调用
        result = await service.async_analyze_review_as_dict(test_text)
        
        print("Async call successful!")
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        print(f"Async call failed: [{type(e).__name__}] {e}")

if __name__ == "__main__":
    asyncio.run(test_async_call())
