import os
import json
import uuid
import asyncio
from datetime import datetime
from guilded import Client, Embed
from guilded.ext import commands
import aiohttp

DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"
MAX_SAVED_CHATS = 5
MAX_MESSAGES_PER_CHAT = 50

bot = commands.Bot(command_prefix="/")
saved_chats = {}

def generate_chat_id():
    return str(uuid.uuid4())

def add_message(chat_id, role, content):
    if chat_id not in saved_chats:
        saved_chats[chat_id] = []
    saved_chats[chat_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    })
    if len(saved_chats[chat_id]) > MAX_MESSAGES_PER_CHAT:
        saved_chats[chat_id] = saved_chats[chat_id][-MAX_MESSAGES_PER_CHAT:]

def trim_chats():
    while len(saved_chats) > MAX_SAVED_CHATS:
        oldest_chat = min(saved_chats.items(), key=lambda x: x[1][0]['timestamp'])[0]
        del saved_chats[oldest_chat]

async def query_openrouter(messages, model=DEFAULT_MODEL):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in environment.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourapp.com",
        "X-Title": "PenGPT P2"
    }

    body = {
        "model": model,
        "messages": messages
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body) as resp:
            if resp.status != 200:
                return f"💀 OpenRouter Error: {resp.status}"
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

@bot.command()
async def pen(ctx, *, message: str):
    chat_id = f"user-{ctx.author.id}"
    add_message(chat_id, "user", message)

    try:
        bot_reply = await query_openrouter(saved_chats[chat_id])
    except Exception as e:
        await ctx.send(f"❌ Error: `{str(e)}`")
        return

    add_message(chat_id, "assistant", bot_reply)
    trim_chats()

    await ctx.send(bot_reply)

# Run the bot
bot.run(os.getenv("GUILDED_TOKEN"))

