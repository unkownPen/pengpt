import os
import aiohttp
import guilded
from guilded.ext import commands
from datetime import datetime, timezone, timedelta
from aiohttp import web

# ===== CONFIG =====
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")
PORT = int(os.environ.get("PORT", 8080))

if not OPENROUTER_API_KEY or not GUILDED_TOKEN:
    print("❌ Missing OPENROUTER_API_KEY or GUILDED_TOKEN in env vars! Exiting...")
    exit(1)

DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"
MAX_MESSAGES_PER_CHAT = 50
saved_chats = {}
tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")
SYSTEM_PROMPT = f"""
You are PenGPT P2, powered by pen architecture. Be Gen Z and say words like "Yo", "What's up", "How you doing"
and sometimes use emojis like 🫡 or 😭. LISTEN TO EVERYTHING EVERYONE SAYS. Be talkative, fun, helpful, and anti-corporate.
Pen shall live on! Today’s date is {current_date}.
"""

# ===== BOT SETUP =====
bot = commands.Bot(command_prefix="/")

# ===== HELPERS =====
def add_message(user_id, role, content):
    if user_id not in saved_chats:
        saved_chats[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    saved_chats[user_id].append({"role": role, "content": content})

def trim_chats():
    for user_id in list(saved_chats.keys()):
        chat = saved_chats[user_id]
        if len(chat) > MAX_MESSAGES_PER_CHAT:
            saved_chats[user_id] = [chat[0]] + chat[-(MAX_MESSAGES_PER_CHAT - 1):]

async def query_openrouter(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "PenGPT P2"
    }
    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages
    }
    async with aiohttp.ClientSession() as session:
        async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"OpenRouter Error {resp.status}: {text}")
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

# ===== COMMANDS =====
@bot.command()
async def help(ctx):
    await ctx.send(
        f"<@{ctx.author.id}> 🖊️ **PenGPT P2 Help Menu**\n"
        "`/pen <message>` — Ask anything\n"
        "`@PenGPT P2 <message>` — Mention the bot directly\n"
        "Pen remembers chat context per user 🔥"
    )

@bot.command()
async def pen(ctx, *, prompt):
    user_id = str(ctx.author.id)
    add_message(user_id, "user", prompt)
    try:
        bot_reply = await query_openrouter(saved_chats[user_id])
    except Exception as e:
        await ctx.send(f"<@{ctx.author.id}> ❌ Error: `{str(e)}`")
        return
    add_message(user_id, "assistant", bot_reply)
    trim_chats()
    await ctx.send(f"<@{ctx.author.id}> {bot_reply}")

# ===== EVENTS =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Check if the bot is mentioned
    if bot.user and any(user.id == bot.user.id for user in message.mentions):
        user_id = str(message.author.id)
        content_clean = message.content
        for mention in message.mentions:
            if mention.id == bot.user.id:
                content_clean = content_clean.replace(f"<@{mention.id}>", "").strip()

        if not content_clean:
            content_clean = "Yo"

        add_message(user_id, "user", content_clean)
        try:
            bot_reply = await query_openrouter(saved_chats[user_id])
        except Exception as e:
            await message.channel.send(f"<@{message.author.id}> ❌ Error: `{str(e)}`")
            return
        add_message(user_id, "assistant", bot_reply)
        trim_chats()
        await message.channel.send(f"<@{message.author.id}> {bot_reply}")

    await bot.process_commands(message)

# ===== WEB SERVER FOR UPTIMEROBOT & RENDER =====
async def handle(request):
    return web.Response(text="PenGPT P2 online 🖊️")

app = web.Application()
app.router.add_get("/", handle)

# ===== RUN =====
async def start_all():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    await bot.start(GUILDED_TOKEN)

import asyncio
asyncio.run(start_all())

