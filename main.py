import os
import aiohttp
import guilded
import asyncio
from aiohttp import web
from guilded.ext import commands
from datetime import datetime, timezone, timedelta

# ===== CONFIG =====
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")
if not OPENROUTER_API_KEY or not GUILDED_TOKEN:
    print("❌ Missing OPENROUTER_API_KEY or GUILDED_TOKEN")
    exit(1)

DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"
MAX_MESSAGES_PER_CHAT = 50
saved_chats = {}
tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")
SYSTEM_PROMPT = f"CUSTOM SYSTEM PROMPT..."

# ===== WEB SERVER for Render Health Check =====
async def handle_health(request):
    return web.Response(text="OK")
async def start_web():
    app = web.Application()
    app.router.add_get("/", handle_health)
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print(f"🌐 Health server on port {port}")

# ===== BOT SETUP =====
bot = commands.Bot(command_prefix="/")

def add_message(uid, role, txt):
    if uid not in saved_chats:
        saved_chats[uid] = [{"role":"system","content":SYSTEM_PROMPT}]
    saved_chats[uid].append({"role": role, "content": txt})

def trim_chats():
    for uid, chat in saved_chats.items():
        if len(chat) > MAX_MESSAGES_PER_CHAT:
            saved_chats[uid] = chat[-MAX_MESSAGES_PER_CHAT:]

async def query_openrouter(messages):
    headers = { "Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json" }
    payload = { "model": DEFAULT_MODEL, "messages": messages }
    async with aiohttp.ClientSession() as sess:
        resp = await sess.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        if resp.status != 200:
            text = await resp.text()
            raise Exception(f"API error {resp.status}: {text}")
        data = await resp.json()
        return data["choices"][0]["message"]["content"]

# ===== COMMANDS =====
@bot.command()
async def pen(ctx, *, prompt):
    uid = str(ctx.author.id)
    add_message(uid, "user", prompt)
    try:
        reply = await query_openrouter(saved_chats[uid])
    except Exception as e:
        await ctx.send(f"<@{uid}> ❌ {str(e)}")
        return
    add_message(uid, "assistant", reply)
    trim_chats()
    await ctx.send(f"<@{uid}> {reply}")

@bot.command()
async def help(ctx):
    await ctx.send(f"<@{ctx.author.id}> Use `/pen <message>` or ping me!")

# ===== EVENT: Reply on mention =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if bot.user in message.mentions:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip() or "Yo"
        uid = str(message.author.id)
        add_message(uid, "user", content)
        try:
            reply = await query_openrouter(saved_chats[uid])
        except Exception as e:
            await message.channel.send(f"<@{uid}> ❌ {str(e)}")
            return
        add_message(uid, "assistant", reply)
        trim_chats()
        await message.channel.send(f"<@{uid}> {reply}")
    await bot.process_commands(message)

# ===== READY LOG =====
@bot.event
async def on_ready():
    print(f"✅ Bot ready as {bot.user}")

# ===== MAIN =====
async def main():
    await start_web()
    await bot.start(GUILDED_TOKEN)

asyncio.run(main())
