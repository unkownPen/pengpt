import os
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from aiohttp import web
import guilded

# ==== ENV & CONFIG ====

GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
PORT = int(os.getenv("PORT", 8080))

if not GUILDED_TOKEN:
    print("❌ GUILDED_TOKEN env var missing! Exiting...")
    exit(1)
if not OPENROUTER_API_KEY:
    print("❌ OPENROUTER_API_KEY env var missing! Exiting...")
    exit(1)

MAX_SAVED_CHATS = 5
MAX_MESSAGES_PER_CHAT = 50
DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"

tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")

SYSTEM_PROMPT = f"""
You are PenGPT, powered by pen archectiture. Be Gen Z and say words like "Yo", "What's up", "How you doing"
and sometimes use emojis like 🫡 or 😭. LISTEN TO EVERYTHING EVERYONE SAYS. Be talkative, fun, helpful, and anti-corporate.
Pen shall live on! Today’s date is {current_date}.
"""

# ==== CLIENT SETUP ====

client = guilded.Client()
client.saved_chats = {}
client.memory_mode = {}
client.ping_enabled = {}
client.models = {}
client.saved_sessions = {}

# ==== WEB HANDLERS ====

async def handle_root(request):
    return web.Response(text="PENGPT IS ALIVE 🖋️")

async def handle_help(request):
    return web.Response(text="""
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

async def handle_health(request):
    return web.Response(text="OK")

# ==== OPENROUTER API CALL ====

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
            if resp.status != 200:
                text = await resp.text()
                print(f"❌ OpenRouter API error {resp.status}: {text}")
                raise Exception(f"OpenRouter API error {resp.status}: {text}")
            result = await resp.json()
            if "choices" in result and result["choices"]:
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(result.get("error", {}).get("message", "No response from OpenRouter"))

# ==== BOT EVENTS ====

@client.event
async def on_ready():
    print(f"✅ PenGPT connected as {client.user.name} (ID: {client.user.id})")

@client.event
async def on_message(message):
    if message.author.bot or (client.user and message.author.id == client.user.id):
        return

    content = message.content.strip()
    lower = content.lower()
    user_id = str(message.author.id)

    # Init user state if missing
    client.saved_chats.setdefault(user_id, [])
    client.memory_mode.setdefault(user_id, False)
    client.ping_enabled.setdefault(user_id, True)
    client.models.setdefault(user_id, DEFAULT_MODEL)
    client.saved_sessions.setdefault(user_id, {})

    ping = f"<@{user_id}> " if client.ping_enabled[user_id] else ""

    # -- COMMANDS --

    if lower == "/help":
        await message.reply(
            ping +
            "**PenGPT Help (DeepSeek-only)**\n"
            "`/sv` - Saved chat mode\n"
            "`/svc` - End saved chat\n"
            "`/pd` - Ping off\n"
            "`/pa` - Ping on\n"
            "`/svpd` - Saved chat + ping off\n"
            "`/sm` - Memory on\n"
            "`/smo` - Memory off\n"
            "`/csm` - Clear memory\n"
            "`/vsm` - View memory\n"
            "`/smpd` - Memory + ping off\n"
            "`/de` - Reset settings\n"
            "`/csc` - Clear saved chats\n"
            "`/vsc` - View saved chats\n"
            "`/model` - Change model (e.g. /model gpt-4)"
        )
        return

    elif lower == "/sv":
        if len(client.saved_sessions[user_id]) >= MAX_SAVED_CHATS:
            oldest = list(client.saved_sessions[user_id])[0]
            del client.saved_sessions[user_id][oldest]
        name = f"chat_{len(client.saved_sessions[user_id]) + 1}"
        client.saved_sessions[user_id][name] = []
        client.saved_chats[user_id] = client.saved_sessions[user_id][name]
        await message.reply(ping + f"💾 Saved chat started: **{name}**")
        return

    elif lower == "/svc":
        client.saved_chats[user_id] = []
        await message.reply(ping + "💾 Saved chat closed.")
        return

    elif lower == "/sm":
        client.memory_mode[user_id] = True
        await message.reply(ping + "🧠 Memory ON.")
        return

    elif lower == "/smo":
        client.memory_mode[user_id] = False
        await message.reply(ping + "🧠 Memory OFF.")
        return

    elif lower == "/pd":
        client.ping_enabled[user_id] = False
        await message.reply("🔕 Ping disabled.")
        return

    elif lower == "/pa":
        client.ping_enabled[user_id] = True
        await message.reply("🔔 Ping enabled.")
        return

    elif lower == "/svpd":
        if len(client.saved_sessions[user_id]) >= MAX_SAVED_CHATS:
            oldest = list(client.saved_sessions[user_id])[0]
            del client.saved_sessions[user_id][oldest]
        name = f"chat_{len(client.saved_sessions[user_id]) + 1}"
        client.saved_sessions[user_id][name] = []
        client.saved_chats[user_id] = client.saved_sessions[user_id][name]
        client.ping_enabled[user_id] = False
        await message.reply("💾 Saved chat started + 🔕 Ping disabled.")
        return

    elif lower == "/smpd":
        client.memory_mode[user_id] = True
        client.ping_enabled[user_id] = False
        await message.reply("🧠 Memory ON + 🔕 Ping OFF.")
        return

    elif lower == "/csm":
        # Clear current saved chat + all saved sessions for this user for consistency
        client.saved_chats[user_id].clear()
        for session in client.saved_sessions[user_id].values():
            session.clear()
        await message.reply(ping + "🧹 Memory cleared.")
        return

    elif lower == "/csc":
        client.saved_sessions[user_id] = {}
        client.saved_chats[user_id] = []
        await message.reply(ping + "🧼 All saved chats cleared.")
        return

    elif lower == "/vsm":
        mem = client.saved_chats[user_id]
        if mem:
            snippet = "\n".join(m["content"] for m in mem[-5:])
            await message.reply(ping + "🧠 Memory:\n```\n" + snippet + "\n```")
        else:
            await message.reply(ping + "🧠 No memory found.")
        return

    elif lower == "/vsc":
        sessions = client.saved_sessions[user_id]
        if not sessions:
            await message.reply("📁 No saved chats found.")
            return
        txt = "\n".join([f"{i+1}. {name}" for i, name in enumerate(sessions.keys())])
        msg = await message.reply(f"📁 Saved Chats:\n{txt}\nReact 1️⃣-5️⃣ to load.")
        for emoji in ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'][:len(sessions)]:
            try:
                await msg.add_reaction(emoji)
            except Exception as e:
                print(f"⚠️ Failed to add reaction {emoji}: {e}")
        return

    elif lower.startswith("/model"):
        parts = content.split(" ", 1)
        if len(parts) == 2:
            model = parts[1].strip()
            client.models[user_id] = model
            await message.reply(ping + f"🤖 Model set to `{model}`")
        else:
            await message.reply(ping + f"📦 Current model: `{client.models[user_id]}`")
        return

    elif lower == "/de":
        client.saved_chats[user_id] = []
        client.memory_mode[user_id] = False
        client.ping_enabled[user_id] = True
        client.models[user_id] = DEFAULT_MODEL
        client.saved_sessions[user_id] = {}
        await message.reply(ping + "♻️ All settings reset.")
        return

    # Should bot reply logic
    should_reply = (
        lower.startswith("/") or
        client.memory_mode[user_id] or
        bool(client.saved_chats[user_id])
    )
    if not should_reply:
        return

    # Compose message history for AI
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    if client.memory_mode[user_id] or client.saved_chats[user_id]:
        history += client.saved_chats[user_id]
    history.append({"role": "user", "content": content})

    try:
        reply = await fetch_openrouter_reply(client.models[user_id], history)
    except Exception as e:
        await message.reply(ping + f"❌ Error: {e}")
        return

    # Save memory/chat logs
    if client.memory_mode[user_id] or client.saved_chats[user_id]:
        client.saved_chats[user_id].append({"role": "user", "content": content})
        client.saved_chats[user_id].append({"role": "assistant", "content": reply})
        if len(client.saved_chats[user_id]) > MAX_MESSAGES_PER_CHAT:
            client.saved_chats[user_id] = client.saved_chats[user_id][-MAX_MESSAGES_PER_CHAT:]

    await message.reply(ping + reply)

@client.event
async def on_reaction_add(reaction, user):
    user_id = str(user.id)
    emoji = getattr(reaction.emoji, "name", None) or str(reaction.emoji)
    if user_id not in client.saved_sessions:
        return
    if emoji not in ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']:
        return
    sessions = list(client.saved_sessions[user_id].items())
    index = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'].index(emoji)
    if index < len(sessions):
        session_name, session_data = sessions[index]
        client.saved_chats[user_id] = session_data
        await reaction.message.reply(f"🗂️ Loaded saved session: **{session_name}**")

# ==== RUN EVERYTHING ====

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/help", handle_help)
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")

async def main():
    await asyncio.gather(
        start_web(),
        client.start(GUILDED_TOKEN)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Shutting down PenGPT...")
