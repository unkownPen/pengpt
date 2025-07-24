import os
import aiohttp
import guilded
from guilded.ext import commands
from datetime import datetime, timezone, timedelta
from aiohttp import web
import asyncio

# — CONFIG —
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")
PORT = int(os.getenv("PORT", 8080))

if not OPENROUTER_API_KEY or not GUILDED_TOKEN:
    print("❌ Missing OPENROUTER_API_KEY or GUILDED_TOKEN")
    exit(1)

DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"
MAX_MESSAGES_PER_CHAT = 50
saved_chats = {}

tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")
SYSTEM_PROMPT = f"You are PenGPT P2… Today’s date is {current_date}."

# — WEB SERVER (for UptimeRobot + Render health) —
async def handle_health(request):
    return web.Response(text="OK")
async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    print(f"🌐 Web server running on port {PORT}")

# — BOT SETUP —
bot = commands.Bot(command_prefix="/")

def add_message(uid, role, txt):
    saved_chats.setdefault(uid, [{"role":"system","content":SYSTEM_PROMPT}])
    saved_chats[uid].append({"role": role, "content": txt})

def trim_chats():
    for uid in saved_chats:
        chat = saved_chats[uid]
        if len(chat) > MAX_MESSAGES_PER_CHAT:
            saved_chats[uid] = [chat[0]] + chat[-(MAX_MESSAGES_PER_CHAT - 1):]

async def query_openrouter(messages):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": DEFAULT_MODEL, "messages": messages}
    async with aiohttp.ClientSession() as sess:
        resp = await sess.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        if resp.status != 200:
            txt = await resp.text()
            raise Exception(f"API {resp.status}: {txt}")
        data = await resp.json()
        return data["choices"][0]["message"]["content"]

# — COMMANDS —
@bot.command()
async def pen(ctx, *, prompt):
    uid = str(ctx.author.id)
    add_message(uid, "user", prompt)
    try:
        reply = await query_openrouter(saved_chats[uid])
    except Exception as e:
        await ctx.send(f"<@{uid}> ❌ {e}")
        return
    add_message(uid, "assistant", reply)
    trim_chats()
    await ctx.send(f"<@{uid}> {reply}")

@bot.command()
async def help(ctx):
    await ctx.send(f"<@{ctx.author.id}> Use `/pen <message>` or ping me!")

# — MENTION HANDLER —
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if bot.user in message.mentions:
        uid = str(message.author.id)
        content = message.content.replace(f"<@{bot.user.id}>", "").strip() or "Yo"
        add_message(uid, "user", content)
        try:
            reply = await query_openrouter(saved_chats[uid])
        except Exception as e:
            await message.channel.send(f"<@{uid}> ❌ {e}")
            return
        add_message(uid, "assistant", reply)
        trim_chats()
        await message.channel.send(f"<@{uid}> {reply}")
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Bot ready as {bot.user}")

# — START BOT & SERVER —
async def main():
    await start_webserver()
    await bot.start(GUILDED_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
