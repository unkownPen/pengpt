import os
import aiohttp
import guilded
from datetime import datetime, timezone, timedelta
from aiohttp import web
import asyncio

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

# ── WEB SERVER ──
async def handle(_):
    return web.Response(text="PenGPT running")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    print(f"Web server on {PORT}")

# ── BOT CLIENT ──
client = guilded.Client()

def add_message(uid, role, txt):
    saved_chats.setdefault(uid, [{"role": "system", "content": SYSTEM_PROMPT}])
    saved_chats[uid].append({"role": role, "content": txt})

def trim(uid):
    history = saved_chats.get(uid, [])
    if len(history) > MAX_MESSAGES:
        saved_chats[uid] = [history[0]] + history[-(MAX_MESSAGES - 1):]

async def query_openrouter(messages):
    res = await aiohttp.ClientSession().post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={"model": DEFAULT_MODEL, "messages": messages}
    )
    data = await res.json()
    return data["choices"][0]["message"]["content"]

# ── EVENT HANDLERS ──
@client.event
async def on_ready():
    print("Bot connected:", client.user.id)

@client.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    uid = str(message.author.id)

    # /pen command
    if text.startswith("/pen"):
        prompt = text[4:].strip()
        if prompt:
            add_message(uid, "user", prompt)
            reply = await query_openrouter(saved_chats[uid])
            add_message(uid, "assistant", reply)
            trim(uid)
            await message.reply(f"<@{uid}> {reply}")
        else:
            await message.reply("✏️ You gotta give me something after /pen")
        return

    # Mention detection
    if client.user in message.mentions:
        clean = text.replace(f"<@{client.user.id}>", "").strip() or "Yo"
        add_message(uid, "user", clean)
        reply = await query_openrouter(saved_chats[uid])
        add_message(uid, "assistant", reply)
        trim(uid)
        await message.reply(f"<@{uid}> {reply}")
        return

# ── MAIN ──
async def main():
    await start_web()
    await client.start(GUILDED_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
