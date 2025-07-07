import guilded
import aiohttp
import asyncio
from flask import Flask
from threading import Thread
from collections import defaultdict, deque

app = Flask("")

@app.route("/")
def home():
    return "PenGPT v2 ALIVE 🖊️🔥"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# === HARDCODED KEYS ===
TOKEN = "gapi_PmD6r4VWBv2OAXhzy++jl4BzI9mI0EVhNs0FY+Iv8uot2lwF0zZrpr/7BzFwkskY1WLbQQZL+ea+7OHltg83jw=="
OPENROUTER_API_KEY = "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"
GROQ_API_KEY = "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"

client = guilded.Client()
saved_chats = defaultdict(lambda: deque(maxlen=50))
saved_memory_enabled = defaultdict(lambda: False)
ping_mode = defaultdict(lambda: True)
current_provider = defaultdict(lambda: "openrouter")

async def ask_ai(user_id, messages):
    provider = current_provider[user_id]
    if provider == "groq":
        return await ask_groq(messages)
    return await ask_openrouter(messages)

async def ask_openrouter(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat-v3-8b",
        "messages": messages
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload) as res:
                data = await res.json()
                return data["choices"][0]["message"]["content"]
    except Exception:
        return "PenGPT hit a snag with OpenRouter API, try again later."

async def ask_groq(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": messages
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.ai/openai/v1/chat/completions", headers=headers, json=payload) as res:
                data = await res.json()
                return data["choices"][0]["message"]["content"]
    except Exception:
        return "PenGPT hit a snag with Groq API, try again later."

def add_msg(uid, role, content):
    saved_chats[uid].append({"role": role, "content": content})

@client.event
async def on_message(msg):
    if msg.author.id == client.user.id: return
    content = msg.content.strip()
    uid = msg.author.id
    lower = content.lower()

    # --- COMMANDS ---
    if lower == "/help":
        await msg.reply(
            "**PenGPT v2 Help**\n"
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
            "`/de` - Reset\n"
            "`/pgV1` - Use Groq (⚡ fast)\n"
            "`/pgV2` - Use OpenRouter (🧠 smart)\n"
        ); return

    if lower == "/pgv1":
        current_provider[uid] = "groq"
        await msg.reply("Provider set to **Groq** (⚡ blazing fast)")
        return

    if lower == "/pgv2":
        current_provider[uid] = "openrouter"
        await msg.reply("Provider set to **OpenRouter** (🧠 smart mode)")
        return

    if lower == "/sv":
        saved_chats[uid] = deque(maxlen=50)
        await msg.reply("🫡 Saved chat ON.")
        return

    if lower == "/svc":
        saved_chats.pop(uid, None)
        await msg.reply("✅ Saved chat OFF.")
        return

    if lower == "/pd":
        ping_mode[uid] = False
        await msg.reply("🔕 Ping mode OFF.")
        return

    if lower == "/pa":
        ping_mode[uid] = True
        await msg.reply("🔔 Ping mode ON.")
        return

    if lower == "/svpd":
        saved_chats[uid] = deque(maxlen=50)
        ping_mode[uid] = False
        await msg.reply("📌 Saved chat + Ping OFF.")
        return

    if lower == "/sm":
        if len(saved_chats[uid]) >= 50:
            await msg.reply("⚠️ Memory full.")
        else:
            saved_memory_enabled[uid] = True
            await msg.reply("💾 Memory ON.")
        return

    if lower == "/smo":
        saved_memory_enabled[uid] = False
        await msg.reply("🛑 Memory OFF.")
        return

    if lower == "/csm":
        if saved_chats[uid]:
            saved_chats[uid].clear()
            await msg.reply("✅ Memory cleared.")
        else:
            await msg.reply("Memory clear — the only thing still full is your stomach buddy 🍔😎")
        return

    if lower == "/vsm":
        mem = list(saved_chats[uid])
        if not mem:
            await msg.reply("No memory.")
        else:
            msgs = [f"**{'You' if m['role']=='user' else 'PenGPT'}:** {m['content']}" for m in mem[-10:]]
            await msg.reply("\n".join(msgs))
        return

    if lower == "/smpd":
        if len(saved_chats[uid]) >= 50:
            await msg.reply("⚠️ Memory full.")
        else:
            saved_memory_enabled[uid] = True
            ping_mode[uid] = False
            await msg.reply("💾 Memory + 🔕 Ping OFF.")
        return

    if lower == "/de":
        saved_chats.pop(uid, None)
        saved_memory_enabled[uid] = False
        ping_mode[uid] = True
        current_provider[uid] = "openrouter"
        await msg.reply("♻️ Reset everything.")
        return

    # --- CHAT LOGIC ---
    if uid in saved_chats:
        if ping_mode[uid] and client.user.mention in content:
            prompt = content.replace(client.user.mention, "").strip()
        elif not ping_mode[uid]:
            prompt = content
        else:
            return
        add_msg(uid, "user", prompt)
        system = {
            "role": "system",
            "content": "You are PenGPT v2, Gen Z, cocky, slang lord. Say stuff like ts, icl, pmo, david, kevin, pack. UAE timezone. Be funny, smart, and always roast clean."
        }
        msgs = [system] + list(saved_chats[uid])
        reply = await ask_ai(uid, msgs)
        add_msg(uid, "assistant", reply)
        await msg.reply(reply)
        return

    # No memory, respond if pinged or ping mode off
    if not ping_mode[uid] or client.user.mention in content:
        prompt = content.replace(client.user.mention, "").strip()
        await msg.reply("PenGPT is typing... ⌛")
        msgs = [
            {"role": "system", "content": "You're PenGPT v2. Gen Z vibes, slang god, cocky and wise."},
            {"role": "user", "content": prompt}
        ]
        reply = await ask_ai(uid, msgs)
        if saved_memory_enabled[uid]:
            saved_chats[uid].append({"role": "user", "content": prompt})
            saved_chats[uid].append({"role": "assistant", "content": reply})
        await msg.reply(reply)

# === BOOT IT UP ===
keep_alive()
client.run(TOKEN)
