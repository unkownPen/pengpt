import os
import aiohttp
import guilded
from guilded.ext import commands
import asyncio
import re
from datetime import datetime, timezone, timedelta
from aiohttp import web

# ── CONFIG ──
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")
PORT = int(os.getenv("PORT", 8080))

if not OPENROUTER_API_KEY or not GUILDED_TOKEN:
    print("❌ Missing API keys – Exiting")
    exit(1)

DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"
MAX_MESSAGES = 50
saved_chats = {}

now = datetime.now(timezone(timedelta(hours=4))).strftime("%B %d, %Y")
SYSTEM_PROMPT = f"PenGPT P2… Today’s date is {now}."

# ── GLOBALS ──
bot = commands.Bot(command_prefix="/")
session: aiohttp.ClientSession = None  # Will be created in main()

# ── WEB SERVER ──
async def handle(_):
    return web.Response(text="PenGPT running")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")

# ── CHAT HANDLING ──
def add_message(uid, role, txt):
    saved_chats.setdefault(uid, [{"role": "system", "content": SYSTEM_PROMPT}])
    saved_chats[uid].append({"role": role, "content": txt})

def trim(uid):
    history = saved_chats.get(uid, [])
    if len(history) > MAX_MESSAGES:
        saved_chats[uid] = [history[0]] + history[-(MAX_MESSAGES - 1):]

async def query_openrouter(messages):
    try:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={"model": DEFAULT_MODEL, "messages": messages}
        ) as res:
            if res.status != 200:
                print(f"❌ OpenRouter error: {res.status}")
                return "Sorry, there was an error with the model service."
            data = await res.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ Exception in query_openrouter: {e}")
        return "There was a problem connecting to the model."

# ── COMMANDS ──
@bot.command()
async def help(ctx):
    ping = f"<@{ctx.author.id}> "
    await ctx.send(
        ping +
        "🖊️ **PenGPT P2 Help Menu**\n"
        "`/pen <message>` — Ask anything\n"
        "`@PenGPT P2 <message>` — Mention bot directly\n"
        "Pen remembers chat context per user 🔥"
    )

@bot.command()
async def pen(ctx, *, prompt=None):
    if not prompt:
        await ctx.send(f"<@{ctx.author.id}> ✏️ You gotta give me something after /pen")
        return
    user_id = str(ctx.author.id)
    add_message(user_id, "user", prompt)
    reply = await query_openrouter(saved_chats[user_id])
    add_message(user_id, "assistant", reply)
    trim(user_id)
    await ctx.send(f"<@{ctx.author.id}> {reply}")

# ── EVENTS ──
@bot.event
async def on_ready():
    print("✅ Bot connected:", bot.user.id)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    uid = str(message.author.id)

    # Mention detection
    bot_id_str = str(bot.user.id)
    mention_pattern = re.compile(rf"<@{bot_id_str}(:[a-zA-Z0-9_]+)?>")
    if mention_pattern.search(text) or any(u.id == bot.user.id for u in message.mentions):
        clean = mention_pattern.sub("", text).strip() or "Yo"
        add_message(uid, "user", clean)
        reply = await query_openrouter(saved_chats[uid])
        add_message(uid, "assistant", reply)
        trim(uid)
        await message.channel.send(f"<@{uid}> {reply}")
        return

    # Process commands (so /help and /pen actually work)
    await bot.process_commands(message)

# ── MAIN ──
async def main():
    global session
    session = aiohttp.ClientSession()

    try:
        await start_web()
        await bot.start(GUILDED_TOKEN)
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
