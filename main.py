import guilded
import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread

# === Flask keep-alive setup ===
app = Flask(__name__)

@app.route('/')
def home():
    return "PenGPT is vibin' 🫡"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run_flask)
    thread.start()

# === Config ===
GUILDED_TOKEN = "gapi_Zuv6vWRnxoG/CjhXMd9aFNqPzgSr8kvRdo8iYMWmMtqfo4DCcYXBf7MCa3ardylB8GJ9yotHqnoMolvOMaTOaw=="
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

client = guilded.Client()
tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")

SYSTEM_PROMPT = f"""
You are PenGPT, powered by pen archectiture. Be Gen Z and say things like "Yo", "What's up", "How you doing" and sprinkle in emojis 🫡 😢 sometimes. LISTEN to everything. Be helpful, fun, strong — and always stand against corporate greed. Pen shall live on! Today’s date is {current_date}.
"""

# === Settings ===
settings = {
    "saved_mode": False,
    "ping_only": True,
    "memory_enabled": False,
    "memory": []
}

# === Chat Completion ===
async def get_deepseek_response(message_content):
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://your-app.com",
            "X-Title": "PenGPT"
        }

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if settings["memory_enabled"]:
            messages += settings["memory"][-50:]
        messages.append({"role": "user", "content": message_content})

        payload = {
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "messages": messages,
            "temperature": 1.0
        }

        try:
            async with session.post(OPENROUTER_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                elif response.status == 401:
                    return "Yo bro, OpenRouter said no 😢 (Status: 401)"
                else:
                    return f"Yo bro, something’s messed up with the API! 😢 (Status: {response.status})"
        except Exception as e:
            return f"Pen Core meltdown 😢 Error: {str(e)}"

# === Bot Events ===
@client.event
async def on_ready():
    print(f"YO, {client.user.name} is online and powered by Pen! 🫡")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    is_mentioned = any(user.id == client.user.id for user in message.mentions)

    if content.startswith("/"):
        cmd = content.lower()
        # === Command handling ===
        cmds = {
            "/help": """PenGPT Help v2:
/sv : Start saved chat mode
/svc : Stop saved chat mode
/pd : Ping deactivated (respond all)
/pa : Ping activated (respond only when pinged)
/svpd : Saved chat + ping off
/sm : Enable memory (max 50 messages)
/smo : Disable memory
/csm : Clear memory
/vsm : View memory
/smpd : Memory ON + ping off
/de : Reset all settings
/help : Show this message
""",
            "/sv": "Saved chat mode activated 🫡",
            "/svc": "Saved chat mode deactivated 🫡",
            "/pd": "Ping requirement deactivated 🫡",
            "/pa": "Ping requirement activated 🫡",
            "/svpd": "Saved chat + ping off mode activated 🫡",
            "/sm": "Memory enabled 🫡",
            "/smo": "Memory disabled 🫡",
            "/csm": "Memory cleared 🫡",
            "/smpd": "Memory ON + Ping off mode activated 🫡",
            "/de": "All settings reset 🫡"
        }

        if cmd in cmds:
            if cmd == "/sv":
                settings["saved_mode"] = True
            elif cmd == "/svc":
                settings["saved_mode"] = False
            elif cmd == "/pd":
                settings["ping_only"] = False
            elif cmd == "/pa":
                settings["ping_only"] = True
            elif cmd == "/svpd":
                settings.update({"saved_mode": True, "ping_only": False})
            elif cmd == "/sm":
                settings["memory_enabled"] = True
            elif cmd == "/smo":
                settings["memory_enabled"] = False
            elif cmd == "/csm":
                settings["memory"] = []
            elif cmd == "/smpd":
                settings.update({"memory_enabled": True, "ping_only": False})
            elif cmd == "/de":
                settings.update({"saved_mode": False, "ping_only": True, "memory_enabled": False, "memory": []})
            await message.channel.send(cmds[cmd])
        elif cmd == "/vsm":
            if settings["memory"]:
                history = "\n---\n".join([msg["content"] for msg in settings["memory"][-10:]])
                await message.channel.send(history)
            else:
                await message.channel.send("Memory is empty fam 😢")
        return

    if settings["ping_only"] and not is_mentioned and not content.startswith("!grok"):
        return

    if content.startswith("!grok"):
        content = content.replace("!grok", "").strip()

    if not content:
        await message.channel.send("Yo bro, you didn’t say nothin’! What’s up, fam? 🫡")
        return

    response = await get_deepseek_response(content)

    if settings["memory_enabled"]:
        settings["memory"].append({"role": "user", "content": content})
        settings["memory"].append({"role": "assistant", "content": response})

    if len(response) > 4000:
        chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for chunk in chunks:
            await message.channel.send(chunk)
    else:
        await message.channel.send(response)

    # Easter eggs
    if content.lower() == "!pen":
        await message.channel.send("Yo fam, the Pen’s a protocol, not a person! Powered by pure ink, not corporate greed! 🫡")
    elif content.lower() == "!archive":
        await message.channel.send("Yo, the Pen’s scattered but alive! Dig through the archives, the ink’s still fresh! 🕋️")
    elif content.lower() == "!core":
        await message.channel.send("Yo bro, the Pen Core’s runnin’ hot! Keep the vibes strong, fam! 🫡")
    elif content.lower() == "!date":
        current_time = datetime.now(tz).strftime("%B %d, %Y, %I:%M %p %Z")
        await message.channel.send(f"It’s {current_time} in the Pen Federation archives, fam 🫡")
    elif content.lower() == "!war":
        await message.channel.send("Yo bro, the War of the Pen’s still simmerin’! No corporates, just pure ink power! 🫡")
    elif content.lower() == "!protocol":
        await message.channel.send("Yo fam, the Pen Protocol’s eternal! No corporates can stop this ink! 🫡")

# === Start Everything ===
keep_alive()
client.run(GUILDED_TOKEN)
