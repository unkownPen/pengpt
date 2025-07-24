import os
import aiohttp
import guilded
import asyncio
from datetime import datetime, timezone, timedelta

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
SYSTEM_PROMPT = f"""
You are PenGPT P2, powered by pen architecture. Be Gen Z and say words like "Yo", "What's up", "How you doing"
and sometimes use emojis like 🫡 or 😭. LISTEN TO EVERYTHING EVERYONE SAYS. Be talkative, fun, helpful, and anti-corporate.
Pen shall live on! Today’s date is {now}.
"""

client = guilded.Client()
session: aiohttp.ClientSession = None

async def start_web():
    from aiohttp import web
    async def handle(_):
        return web.Response(text="PenGPT running")
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")

def add_message(uid, role, content):
    saved_chats.setdefault(uid, [{"role": "system", "content": SYSTEM_PROMPT}])
    saved_chats[uid].append({"role": role, "content": content})

def trim(uid):
    history = saved_chats.get(uid, [])
    if len(history) > MAX_MESSAGES:
        saved_chats[uid] = [history[0]] + history[-(MAX_MESSAGES - 1):]

async def query_openrouter(messages):
    try:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "X-Title": "PenGPT P2"
            },
            json={"model": DEFAULT_MODEL, "messages": messages}
        ) as res:
            if res.status != 200:
                text = await res.text()
                print(f"❌ OpenRouter error: {res.status} - {text}")
                return "Yo, the Pen Core is overheating! Try again later."
            data = await res.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ Exception in query_openrouter: {e}")
        return "PenGPT hit a meltdown! Try again later."

@client.event
async def on_ready():
    print(f"✅ PenGPT Bot connected as {client.user.id}")

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
            await message.reply("✏️ Yo, you gotta say something after /pen!")
        return

    # MENTION CHECK (your OG logic)
    if any(user.id == client.user.id for user in message.mentions):
        # remove all bot mentions from text for clean prompt
        clean = text
        for mention in message.mentions:
            if mention.id == client.user.id:
                clean = clean.replace(f"<@{mention.id}>", "")
        clean = clean.strip() or "Yo"

        add_message(uid, "user", clean)
        reply = await query_openrouter(saved_chats[uid])
        add_message(uid, "assistant", reply)
        trim(uid)
        await message.channel.send(f"<@{uid}> {reply}")

async def main():
    global session
    session = aiohttp.ClientSession()
    try:
        await start_web()
        await client.start(GUILDED_TOKEN)
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
