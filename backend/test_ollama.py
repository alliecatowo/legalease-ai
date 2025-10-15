import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://ollama:11434/api/generate",
            json={
                "model": "llama3.1:latest",
                "prompt": "test prompt",
                "system": "You are a test assistant",
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            result = response.json()
            print(f"Response: {result.get('response', 'NO RESPONSE')}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

asyncio.run(test())
