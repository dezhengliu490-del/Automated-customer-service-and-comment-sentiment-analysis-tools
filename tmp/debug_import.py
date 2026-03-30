import sys
from pathlib import Path

# Add backend to sys.path
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

try:
    from deepseek_service import DeepSeekService
    print("Importing DeepSeekService: Success")
    
    # Try to access the name
    from schemas import SentimentAnalysisResult
    print(f"SentimentAnalysisResult name resolution: {SentimentAnalysisResult}")
    
    # Check if DeepSeekService can see it
    service = DeepSeekService(api_key="test", model="test")
    print("Instantiation: Success")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
