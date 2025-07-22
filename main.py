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
and sometimes use emojis like 🪡 or 😭. LISTEN TO EVERYTHING EVERYONE SAYS. Be talkative, fun, helpful, and anti-corporate.
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
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                elif "error" in result:
                    raise Exception(result["error"].get("message", "Unknown API error"))
                else:
                    raise Exception("No choices returned by OpenRouter.")
            except Exception as e:
                raise Exception(f"Failed to fetch OpenRouter reply: {str(e)}")

# You need to add on_message event handler for your bot to respond
@client.event
async def on_message(message):
    if message.author.type.name == "bot":
        return

    print(f"📥 Message from {message.author.name}: {message.content}")
    
    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message.content}
    ]

    try:
        response = await fetch_openrouter_reply(DEFAULT_MODEL, history)
        await message.reply(response)
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

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
