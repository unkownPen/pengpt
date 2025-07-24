import os
import aiohttp
import guilded
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
client = guilded.Client()
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

# ── EVENT HANDLERS ──
@client.event
async def on_ready():
    print("✅ Bot connected:", client.user.id)

@client.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    uid = str(message.author.id)

    # DEBUG prints for mention inspection
    print("DEBUG: Message content:", text)
    print("DEBUG: Mentions:", [(u.id, u.name) for u in message.mentions])

    # Regex mention pattern for bot (accounts for optional username part)
    bot_id_str = str(client.user.id)
    mention_pattern = re.compile(rf"<@{bot_id_str}(:[a-zA-Z0-9_]+)?>")

    # Check mention either via mentions or regex match in text
    if mention_pattern.search(text) or any(u.id == client.user.id for u in message.mentions):
        # Remove all mention variants
        clean = mention_pattern.sub("", text).strip() or "Yo"
        add_message(uid, "user", clean)
        reply = await query_openrouter(saved_chats[uid])
        add_message(uid, "assistant", reply)
        trim(uid)
        await message.channel.send(f"<@{uid}> {reply}")
        return

    # /pen command
    if text.startswith("/pen"):
        prompt = text[4:].strip()
        if prompt:
            add_message(uid, "user", prompt)
            reply = await query_openrouter(saved_chats[uid])
            add_message(uid, "assistant", reply)
            trim(uid)
            await message.channel.send(f"<@{uid}> {reply}")
        else:
            await message.channel.send("✏️ You gotta give me something after /pen")
        return

    # Let commands process (if any added later)
    await client.process_commands(message)

# ── MAIN ──
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
