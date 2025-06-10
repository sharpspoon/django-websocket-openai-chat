import os
import openai
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
import json

openai.api_key = os.getenv("OPENAI_API_KEY")

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        user_message = data.get("message", "")

        # Send the user message back to the client
        await self.send(text_data=json.dumps({
            "sender": "user",
            "message": user_message,
        }))

        # Stream OpenAI Assistant API response
        await self.stream_openai_response(user_message)

    async def stream_openai_response(self, user_message):
        import aiohttp

        assistant_id = os.getenv("OPENAI_ASSISTANT_ID")  # Set this in your env or hardcode here

        if not assistant_id:
            await self.send(text_data=json.dumps({
                "sender": "ai",
                "message": "[Error] OPENAI_ASSISTANT_ID not set."
            }))
            return

        openai_url = f"https://api.openai.com/v1/assistants/{assistant_id}/messages"
        headers = {
            "Authorization": f"Bearer {openai.api_key}",
            "OpenAI-Beta": "assistants=v2",
            "Content-Type": "application/json",
        }
        body = {
            "messages": [{"role": "user", "content": user_message}],
            "stream": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(openai_url, headers=headers, json=body) as resp:
                async for line in resp.content:
                    if line:
                        try:
                            line = line.decode("utf-8")
                            if line.startswith("data: "):
                                data_json = json.loads(line[6:])
                                content = data_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    await self.send(text_data=json.dumps({
                                        "sender": "ai",
                                        "message": content,
                                    }))
                        except Exception:
                            continue
