import os
import asyncio
import aiohttp
import json
from datetime import datetime, timezone, timedelta
from aiohttp import web
import guilded

# Tokens pulled from Render Secrets
GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Constants
MAX_SAVED_CHATS = 5
MAX_MESSAGES_PER_CHAT = 50
DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"
BOT_USER_ID = "mjlxjn34"

saved_chats = {}

# --- Chat Handling Functions ---
def add_message(chat_id, role, content):
    if chat_id not in saved_chats:
        saved_chats[chat_id] = []
    saved_chats[chat_id].append({"role": role, "content": content})

    # Keep only the most recent messages
    if len(saved_chats[chat_id]) > MAX_MESSAGES_PER_CHAT:
        saved_chats[chat_id] = saved_chats[chat_id][-MAX_MESSAGES_PER_CHAT:]

def trim_chats():
    if len(saved_chats) > MAX_SAVED_CHATS:
        oldest_chat = min(saved_chats.items(), key=lambda x: len(x[1]))[0]
        del saved_chats[oldest_chat]

# --- OpenRouter Query ---
async def query_openrouter(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourapp.com"
    }
    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            result = await resp.json()
            return result['choices'][0]['message']['content']

# --- Guilded Bot Setup ---
bot = guilded.Client()

@bot.event
async def on_ready():
    print(f"PenGPT P2 is online as {bot.user.name}")

@bot.event
async def on_message(message):
    if message.author.id == BOT_USER_ID:
        return

    # /help command
    if message.content.lower() == "/help":
        await message.channel.send("Yo! I'm PenGPT P2 🤖\nUse /help, or tag me like @PenGPT P2 and ask anything!")
        return

    # If the bot is mentioned directly (Guilded-style)
    if f"<@{BOT_USER_ID}>" in message.content or "@PenGPT P2" in message.content:
        chat_id = f"user-{message.author.id}"
        user_input = message.content

        add_message(chat_id, "user", user_input)
        try:
            response = await query_openrouter(saved_chats[chat_id])
        except Exception as e:
            await message.channel.send(f"❌ Error talking to OpenRouter: `{e}`")
        else:
            add_message(chat_id, "assistant", response)
            await message.channel.send(response)

bot.run(GUILDED_TOKEN)
