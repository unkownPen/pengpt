import os
import json
import aiohttp
import guilded
from guilded.ext import commands
from datetime import datetime

# 🧠 Chat memory
saved_chats = {}
MAX_SAVED_CHATS = 5
MAX_MESSAGES_PER_CHAT = 50
DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"

# 🗝️ API key (from OpenRouter) and Bot token (from Guilded)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")

intents = guilded.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

# 🧼 Save chat messages
def add_message(chat_id, role, content):
    if chat_id not in saved_chats:
        saved_chats[chat_id] = []
    saved_chats[chat_id].append({"role": role, "content": content})

# 🧹 Trim convo if too long
def trim_chats():
    while len(saved_chats) > MAX_SAVED_CHATS:
        oldest = sorted(saved_chats.items(), key=lambda x: x[1][0]["timestamp"])[0][0]
        del saved_chats[oldest]

    for chat_id in saved_chats:
        if len(saved_chats[chat_id]) > MAX_MESSAGES_PER_CHAT:
            saved_chats[chat_id] = saved_chats[chat_id][-MAX_MESSAGES_PER_CHAT:]

# 🤖 Query OpenRouter (DeepSeek Chimera)
async def query_openrouter(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourdomain.com",  # Optional
        "X-Title": "PenGPT P2"
    }
    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("https://openrouter.ai/api/v1/chat/completions",
                                headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"OpenRouter Error {resp.status}: {text}")
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

# ✅ SLASH COMMAND: /help
@bot.command()
async def help(ctx):
    await ctx.send("🖊️ **PenGPT P2 Help Menu**\n"
                   "`/pen <message>` — Ask anything\n"
                   "`@PenGPT P2 <message>` — Mention bot directly\n"
                   "Pen remembers chat context per user 🔥")

# ✅ SLASH COMMAND: /pen
@bot.command()
async def pen(ctx, *, prompt):
    chat_id = f"user-{ctx.author.id}"
    add_message(chat_id, "user", prompt)

    try:
        bot_reply = await query_openrouter(saved_chats[chat_id])
    except Exception as e:
        await ctx.send(f"❌ Error: `{str(e)}`")
        return

    add_message(chat_id, "assistant", bot_reply)
    trim_chats()
    await ctx.send(bot_reply)

# 💬 Message handler for @mentions
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user.id in [m.id for m in message.mentions]:
        chat_id = f"user-{message.author.id}"
        add_message(chat_id, "user", message.content)

        try:
            bot_reply = await query_openrouter(saved_chats[chat_id])
        except Exception as e:
            await message.channel.send(f"❌ Error: `{str(e)}`")
            return

        add_message(chat_id, "assistant", bot_reply)
        trim_chats()
        await message.channel.send(bot_reply)

    await bot.process_commands(message)  # So slash commands still work

# 🚀 GO TIME
bot.run(GUILDED_TOKEN)
