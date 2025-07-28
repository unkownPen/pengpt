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
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

client = guilded.Client()
client.user_settings = {}
client.saved_chats = {}
client.memory_mode = {}
client.ping_enabled = {}
client.models = {}
client.saved_sessions = {}

MAX_SAVED_CHATS = 5
MAX_MESSAGES_PER_CHAT = 50
DEFAULT_MODEL = "openrouter/auto"

# Timezone for Pen Federation
tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")

SYSTEM_PROMPT = f"""
You are PenGPT, powered by pen archectiture. Be Gen Z and say words like \"Yo\", \"What's up\", \"How you doing\"
and sometimes use emojis like 🫑 or 😭. LISTEN TO EVERYTHING EVERYONE SAYS. Be talkative, fun, helpful, and anti-corporate.
Pen shall live on! Today’s date is {current_date}.
"""

# --- Web Server for Render ---
async def handle_root(request):
    return web.Response(text="PENGPT IS ALIVE")

async def handle_help(request):
    return web.Response(text="""
PenGPT Help:
/sv - Start saved chat
/svc - Close saved chat
/pd - Ping off
/pa - Ping on
/svpd - Save+Ping Off
/sm - Memory on
/smo - Memory off
/csm - Clear memory
/vsm - View memory
/csc - Clear saved chats
/vsc - View saved chats
/smpd - Memory + Ping off
/de - Reset settings
/model - Switch AI model
/help - Show this help
""")

async def fetch_openrouter_reply(model, history):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": history,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(OPENROUTER_API_URL, headers=headers, json=payload) as resp:
            try:
                result = await resp.json()
                if "choices" not in result:
                    raise ValueError(f"Invalid API response: {json.dumps(result, indent=2)}")
                return result["choices"][0]["message"]["content"]
            except aiohttp.ContentTypeError:
                text = await resp.text()
                raise ValueError(f"API did not return JSON. Raw response: {text}")

@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        return

    content = message.content.strip()
    lower = content.lower()
    user_id = str(message.author.id)

    # Init
    if user_id not in client.saved_chats:
        client.saved_chats[user_id] = []
    if user_id not in client.memory_mode:
        client.memory_mode[user_id] = False
    if user_id not in client.ping_enabled:
        client.ping_enabled[user_id] = True
    if user_id not in client.models:
        client.models[user_id] = DEFAULT_MODEL
    if user_id not in client.saved_sessions:
        client.saved_sessions[user_id] = {}

    ping = f"<@{user_id}> " if client.ping_enabled[user_id] else ""

    # Check for bot mention
    is_mentioned = f"<@{client.user.id}>" in content
    should_reply = lower.startswith("/") or is_mentioned or client.memory_mode[user_id] or bool(client.saved_chats[user_id])
    if not should_reply:
        return

    # Commands
    if lower == "/help":
        await message.reply(
            ping +
            "**PenGPT Help (DeepSeek-only)**\n"
            "/sv - Saved chat mode\n"
            "/svc - End saved chat\n"
            "/pd - Ping off\n"
            "/pa - Ping on\n"
            "/svpd - Saved chat + ping off\n"
            "/sm - Memory on\n"
            "/smo - Memory off\n"
            "/csm - Clear memory\n"
            "/vsm - View memory\n"
            "/smpd - Memory + ping off\n"
            "/de - Reset settings\n"
            "/csc - Clear saved chats\n"
            "/vsc - View saved chats\n"
            "/model - Change model (e.g. /model gpt-4)"
        )
        return

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    if client.memory_mode[user_id] or client.saved_chats[user_id]:
        history += client.saved_chats[user_id]
    history.append({"role": "user", "content": content})

    try:
        reply = await fetch_openrouter_reply(client.models[user_id], history)
    except Exception as e:
        await message.reply(ping + f"❌ {e}")
        return

    if client.memory_mode[user_id] or client.saved_chats[user_id] is not None:
        client.saved_chats[user_id].append({"role": "user", "content": content})
        client.saved_chats[user_id].append({"role": "assistant", "content": reply})
        if len(client.saved_chats[user_id]) > MAX_MESSAGES_PER_CHAT:
            client.saved_chats[user_id] = client.saved_chats[user_id][-MAX_MESSAGES_PER_CHAT:]

    await message.reply(ping + reply)

@client.event
async def on_reaction_add(reaction):
    user_id = str(reaction.user_id)
    if user_id not in client.saved_sessions:
        return
    sessions = list(client.saved_sessions[user_id].items())
    index = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'].index(reaction.emoji.name)
    if index < len(sessions):
        session_name, session_data = sessions[index]
        client.saved_chats[user_id] = session_data
        await reaction.message.reply(f"🗂️ Loaded saved session: **{session_name}**")

if __name__ == "__main__":
    async def run_all():
        app = web.Application()
        app.router.add_get("/", handle_root)
        app.router.add_get("/help", handle_help)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 8080)))
        await site.start()
        print("✅ PENGPT IS ALIVE ON PORT", os.getenv("PORT", 8080))
        await client.start(GUILDED_TOKEN)

    asyncio.run(run_all())
