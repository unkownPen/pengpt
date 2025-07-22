import os
import asyncio
import aiohttp
import json
from datetime import datetime, timezone, timedelta
from aiohttp import web
import guilded
from dotenv import load_dotenv

# Load .env (for local dev only)
load_dotenv()

GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

client = guilded.Client()
client.user_settings = {}

MAX_SAVED_CHATS = 5
MAX_MESSAGES_PER_CHAT = 50

# Timezone for Pen Federation
tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")

SYSTEM_PROMPT = f"""
You are PenGPT, powered by pen archectiture. Be Gen Z and say words like "Yo", "What's up", "How you doing"
and sometimes use emojis like 🫡 or 😭. LISTEN TO EVERYTHING EVERYONE SAYS. Be talkative, fun, helpful, and anti-corporate.
Pen shall live on! Today’s date is {current_date}.
"""

# --- Web Server for Render ---
async def handle_root(request):
    return web.Response(text="PenGPT is online and inked up! 🫡")

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
/de - Reset settings
""")

def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/help", handle_help)
    runner = web.AppRunner(app)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 8080)))
    loop.run_until_complete(site.start())

# --- AI Functions ---
async def get_deepseek_response(message_content):
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "tngtech/deepseek-r1t2-chimera:free",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message_content}
            ],
            "temperature": 1.0
        }
        try:
            async with session.post(OPENROUTER_API_URL, headers=headers, json=payload) as response:
                data = await response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error from Pen Core: {str(e)}"

async def generate_chat_title(messages):
    prompt = "Give a short and relevant name (max 6 words) for this conversation."
    text_block = "\n".join(messages[-MAX_MESSAGES_PER_CHAT:])

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text_block}
        ],
        "temperature": 0.5
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_API_URL, headers=headers, json=payload) as response:
                data = await response.json()
                return data["choices"][0]["message"]["content"].strip().strip('"')
    except:
        return "Untitled Chat"

# --- Events ---
@client.event
async def on_ready():
    print(f"PenGPT ready as {client.user.name} 🫡")

@client.event
async def on_message(msg):
    if msg.author.bot:
        return

    user_id = str(msg.author.id)
    lower = msg.content.lower()

    if user_id not in client.user_settings:
        client.user_settings[user_id] = {
            "saved_chat": False,
            "ping": True,
            "memory": False,
            "memory_store": [],
            "saved_chats": [],
            "current_chat_name": None
        }

    user_settings = client.user_settings[user_id]

    if lower == "/help":
        await msg.reply("""**PenGPT Help**\n`/sv`, `/svc`, `/pd`, `/pa`, `/svpd`, `/sm`, `/smo`, `/csm`, `/vsm`, `/vsc`, `/csc`, `/de`""")
        return

    elif lower == "/csc":
        user_settings["saved_chats"] = []
        await msg.reply("🗑️ All saved chats cleared.")
        return

    elif lower == "/sv":
        if len(user_settings["saved_chats"]) >= MAX_SAVED_CHATS:
            await msg.reply("❌ Max 5 saved chats. Use `/csc`.")
        else:
            user_settings["saved_chat"] = True
            user_settings["memory_store"] = []
            user_settings["current_chat_name"] = "Temporary Chat"
            await msg.reply("✅ Saved chat mode started.")
        return

    elif lower == "/svc":
        if user_settings["saved_chat"]:
            user_settings["saved_chat"] = False
            saved_data = user_settings["memory_store"][:]
            title = await generate_chat_title(saved_data)
            user_settings["saved_chats"].append({"name": title, "messages": saved_data})
            user_settings["memory_store"] = []
            await msg.reply(f"📂 Chat saved as **{title}**.")
        else:
            await msg.reply("⚠️ No saved chat active.")
        return

    elif lower == "/vsc":
        saved_chats = user_settings["saved_chats"]
        if not saved_chats:
            await msg.reply("📭 No saved chats yet.")
        else:
            preview = "\n".join([f"{i+1}. **{c['name']}**" for i, c in enumerate(saved_chats[:5])])
            sent = await msg.reply("**Saved Chats Menu**\nReact to load:\n" + preview)
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
            for i in range(len(saved_chats[:5])):
                await sent.add_reaction(emojis[i])
            if "reaction_menu" not in client.user_settings:
                client.user_settings["reaction_menu"] = {}
            client.user_settings["reaction_menu"][str(sent.id)] = {
                "user_id": user_id,
                "chats": saved_chats[:5]
            }
        return

    elif lower == "/vsm":
        mem = user_settings["memory_store"][-10:]
        await msg.reply("\n".join(mem) if mem else "🫥 Memory is empty.")
        return

    elif lower == "/csm":
        user_settings["memory_store"] = []
        await msg.reply("🧼 Memory cleared.")
        return

    elif lower == "/de":
        client.user_settings[user_id] = {
            "saved_chat": False, "ping": True, "memory": False,
            "memory_store": [], "saved_chats": [], "current_chat_name": None
        }
        await msg.reply("♻️ All settings reset.")
        return

    elif lower == "/pd": user_settings["ping"] = False; await msg.reply("🔕 Ping OFF."); return
    elif lower == "/pa": user_settings["ping"] = True; await msg.reply("🔔 Ping ON."); return
    elif lower == "/svpd": user_settings["saved_chat"] = True; user_settings["ping"] = False; await msg.reply("📦 Saved Chat + 🔕 Ping OFF."); return
    elif lower == "/sm": user_settings["memory"] = True; await msg.reply("🧠 Memory ON."); return
    elif lower == "/smo": user_settings["memory"] = False; await msg.reply("💤 Memory OFF."); return
    elif lower == "/smpd": user_settings["memory"] = True; user_settings["ping"] = False; await msg.reply("🧠+🔕 Memory + Ping OFF."); return

    is_mentioned = any(u.id == client.user.id for u in msg.mentions)
    if is_mentioned or lower.startswith("!pengpt"):
        content = msg.content.replace("!pengpt", "").strip()
        if not content:
            await msg.channel.send("Say something after !pengpt fam 😭")
            return

        if user_settings["memory"]:
            user_settings["memory_store"].append(f"User: {content}")

        response = await get_deepseek_response(content)

        if user_settings["memory"]:
            user_settings["memory_store"].append(f"AI: {response}")

        await msg.channel.send(response)

@client.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    msg_id = str(reaction.message.id)
    menu_data = client.user_settings.get("reaction_menu", {}).get(msg_id)
    if not menu_data or str(user.id) != menu_data["user_id"]:
        return

    emoji_to_index = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3, "5️⃣": 4}
    index = emoji_to_index.get(str(reaction.emoji))
    if index is None:
        return

    try:
        selected_chat = menu_data["chats"][index]
        ai_msgs = [m for m in selected_chat["messages"] if m.startswith("AI:")]
        if ai_msgs:
            await reaction.message.channel.send(f"🧠 **{selected_chat['name']}**\n{ai_msgs[-1][3:].strip()}")
        else:
            await reaction.message.channel.send("🤷‍♂️ No AI replies in that chat.")
    except Exception as e:
        await reaction.message.channel.send(f"❌ Failed to load chat: {e}")

if __name__ == "__main__":
    start_web_server()
    client.run(GUILDED_TOKEN)
