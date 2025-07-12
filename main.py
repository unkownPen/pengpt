import guilded
import aiohttp
import asyncio
import json
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread

# Flask keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return "PenGPT is alive 🫡"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run_flask)
    thread.start()

# 🔐 New API key
GUILDED_TOKEN = "gapi_Zuv6vWRnxoG/CjhXMd9aFNqPzgSr8kvRdo8iYMWmMtqfo4DCcYXBf7MCa3ardylB8GJ9yotHqnoMolvOMaTOaw=="
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

client = guilded.Client()

tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")

SYSTEM_PROMPT = f"""
You are PenGPT, powered by pen architecture. Be Gen Z and say words like "Yo" "What's up" "How you doing" and sometimes use emojis like 🫡 😢. LISTEN TO EVERYTHING. Be talkative, fun, smart, and helpful. No corporate vibes. Today’s date is {current_date}.
"""

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
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    print("⚠️ OpenRouter status:", response.status)
                    print("⚠️ OpenRouter response:", error_text)
                    return "Yo bro, something’s messed up with the API! 😢 Try again later, fam."
        except Exception as e:
            return f"Yo, we hit a Pen Core meltdown! Error: {str(e)} 🫡 Keep it chill and try again."

@client.event
async def on_ready():
    print(f"YO, {client.user.name} is online and ready to bring the Pen Federation vibes! 🫡")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    is_mentioned = any(user.id == client.user.id for user in message.mentions)

    if content.startswith("/"):
        cmd = content.lower()
        if cmd == "/help":
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
        elif cmd == "/sv":
            settings["saved_mode"] = True
            await message.channel.send("Saved chat mode activated 🫡")
        elif cmd == "/svc":
            settings["saved_mode"] = False
            await message.channel.send("Saved chat mode deactivated 🫡")
        elif cmd == "/pd":
            settings["ping_only"] = False
            await message.channel.send("Ping requirement deactivated 🫡")
        elif cmd == "/pa":
            settings["ping_only"] = True
            await message.channel.send("Ping requirement activated 🫡")
        elif cmd == "/svpd":
            settings["saved_mode"] = True
            settings["ping_only"] = False
            await message.channel.send("Saved chat + ping off mode activated 🫡")
        elif cmd == "/sm":
            settings["memory_enabled"] = True
            await message.channel.send("Memory enabled 🫡")
        elif cmd == "/smo":
            settings["memory_enabled"] = False
            await message.channel.send("Memory disabled 🫡")
        elif cmd == "/csm":
            settings["memory"] = []
            await message.channel.send("Memory cleared 🫡")
        elif cmd == "/vsm":
            if settings["memory"]:
                await message.channel.send("\n---\n".join([msg["content"] for msg in settings["memory"]]))
            else:
                await message.channel.send("Memory is empty fam 😭")
        elif cmd == "/smpd":
            settings["memory_enabled"] = True
            settings["ping_only"] = False
            await message.channel.send("Memory ON + Ping off mode activated 🫡")
        elif cmd == "/de":
            settings.update({
                "saved_mode": False,
                "ping_only": True,
                "memory_enabled": False,
                "memory": []
            })
            await message.channel.send("All settings reset 🫡")
        return

    if settings["ping_only"] and not is_mentioned and not content.startswith("!grok"):
        return

    if content.startswith("!grok"):
        content = content.replace("!grok", "").strip()

    if not content:
        await message.channel.send("Yo bro, you didn’t say nothin’! What’s up, fam? 🫡")
        return

    try:
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
    except Exception as e:
        await message.channel.send(f"Yo bro, we hit a Pen Core meltdown! Error: {str(e)} 😢 Keep it chill and try again.")

# 🔥 Flask alive + Run the bot
keep_alive()
client.run(GUILDED_TOKEN)
