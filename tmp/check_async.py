import asyncio
from google import genai

async def check_async():
    try:
        # Check if genai has Client or AsyncClient
        print(f"genai attributes: {dir(genai)}")
        if hasattr(genai, 'Client'):
            client = genai.Client(api_key="test")
            print(f"Client attributes: {dir(client)}")
            # Check if models has generate_content and its async version
            print(f"client.models attributes: {dir(client.models)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_async())
