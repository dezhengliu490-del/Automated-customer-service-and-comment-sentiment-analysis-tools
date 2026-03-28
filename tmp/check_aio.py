from google import genai

def check_aio():
    try:
        client = genai.Client(api_key="test")
        print(f"client.aio exists: {hasattr(client, 'aio')}")
        if hasattr(client, 'aio'):
            print(f"client.aio.models attributes: {dir(client.aio.models)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_aio()
