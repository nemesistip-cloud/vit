import asyncio
import os

# Mock the environment
os.environ["GEMINI_API_KEY"] = "fake"

async def test():
    try:
        from app.services.assistant_tools import GEMINI_TOOLS, TOOL_MAP
        print("Successfully imported assistant_tools")
        print(f"Tools available: {[t['function_declarations'][0]['name'] for t in GEMINI_TOOLS]}")

        from app.services.gemini_chat import chat
        print("Successfully imported gemini_chat")
    except Exception as e:
        print(f"Import failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
