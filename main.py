import guilded
import aiohttp
import asyncio
import json
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread

# Flask keep-alive
app = Flask(__name__)

@app.route("/")
def index():
    return "PenGPT is vibin’ 🫡"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# --- CONFIG ---
GUILDED_TOKEN = "gapi_Zuv6vWRnxoG/CjhXMd9aFNqPzgSr8kvRdo8iYMWmMtqfo4DCcYXBf7MCa3ardylB8GJ9yotHqnoMolvOMaTOaw=="
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

client = guilded.Client()
tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")

SYSTEM_PROMPT = f"""
You are PenGPT, powered by pen archectiture. Be Gen Z and say words like "Yo" "Whats up" "How you doing" and sometimes not often use emojis like saluting face emoji and crying emoji. LISTEN TO EVERYTHING. Be a good person, talkative, fun, and smart to help the user learn. You're powered by strength, not greedy corporates. Pen shall live on! Today's date is {current_date}.
"""

# --- SETTINGS ---
settings = {
    "saved_mode": False,
    "ping_only": True,
    "memory_enabled": False,
    "memory": []
}

async def get_deepseek_response(message_content):
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://your-app.com",
            "X-Title": "Guilded Bot"
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
                text = await response.text()
                print("OpenRouter status:", response.status)
                print("Response:", text)
                if response.status == 200:
                    data = json.loads(text)
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"Yo bro, OpenRouter said no 😢 (Status: {response.status})"
        except Exception as e:
            print("Pen Core error:", str(e))
            return f"Yo, Pen Core meltdown! Error: {str(e)} 🫡"

@client.event
async def on_ready():
    print(f"🔥 PenGPT is online as {client.user.name} 🫡")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    is_mentioned = any(user.id == client.user.id for user in message.mentions)

    # --- Slash Commands ---
    if content.startswith("/"):
        cmd = content.lower()
        match cmd:
            case "/help":
                await message.channel.send("""
PenGPT Help v2:
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
""")
            case "/sv":
                settings["saved_mode"] = True
                await message.channel.send("Saved chat mode activated 🫡")
            case "/svc":
                settings["saved_mode"] = False
                await message.channel.send("Saved chat mode deactivated 🫡")
            case "/pd":
                settings["ping_only"] = False
                await message.channel.send("Ping requirement deactivated 🫡")
            case "/pa":
                settings["ping_only"] = True
                await message.channel.send("Ping requirement activated 🫡")
            case "/svpd":
                settings["saved_mode"] = True
                settings["ping_only"] = False
                await message.channel.send("Saved chat + ping off mode activated 🫡")
            case "/sm":
                settings["memory_enabled"] = True
                await message.channel.send("Memory enabled 🫡")
            case "/smo":
                settings["memory_enabled"] = False
                await message.channel.send("Memory disabled 🫡")
            case "/csm":
                settings["memory"] = []
                await message.channel.send("Memory cleared 🫡")
            case "/vsm":
                if settings["memory"]:
                    await message.channel.send("\n---\n".join([msg["content"] for msg in settings["memory"]]))
                else:
                    await message.channel.send("Memory is empty fam 😭")
            case "/smpd":
                settings["memory_enabled"] = True
                settings["ping_only"] = False
                await message.channel.send("Memory ON + Ping OFF 🫡")
            case "/de":
                settings.update({
                    "saved_mode": False,
                    "ping_only": True,
                    "memory_enabled": False,
                    "memory": []
                })
                await message.channel.send("All settings reset 🫡")
        return

    # --- Filters ---
    if settings["ping_only"] and not is_mentioned and not content.startswith("!grok"):
        return
    if content.startswith("!grok"):
        content = content.replace("!grok", "").strip()
    if not content:
        await message.channel.send("Yo bro, you didn’t say nothin’! What’s up, fam? 🫡")
        return

    # --- Respond once ---
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

    # --- Easter Eggs ---
    lower = content.lower()
    if lower == "!pen":
        await message.channel.send("Yo fam, the Pen’s a protocol, not a person! 🫡")
    elif lower == "!archive":
        await message.channel.send("Yo, the Pen’s scattered but alive! Archives still vibin! 🕋")
    elif lower == "!core":
        await message.channel.send("Pen Core's still heating up 🔥 Keep pushing fam 🫡")
    elif lower == "!date":
        current_time = datetime.now(tz).strftime("%B %d, %Y, %I:%M %p %Z")
        await message.channel.send(f"It’s {current_time} in the Pen Federation 🫡")
    elif lower == "!war":
        await message.channel.send("Ink war’s still going strong 🫡")
    elif lower == "!protocol":
        await message.channel.send("The Pen Protocol shall NEVER DIE 💀")

# --- RUN BOT ---
client.run(GUILDED_TOKEN)
