import guilded
import aiohttp
import asyncio
from flask import Flask
from threading import Thread
from collections import defaultdict, deque

app = Flask("")

@app.route("/")
def home():
    return "PenGPT v2 DeepSeek-only alive & roasting 🖊️🔥"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# === HARDCODED KEYS ===
TOKEN = "gapi_PmD6r4VWBv2OAXhzy++jl4BzI9mI0EVhNs0FY+Iv8uot2lwF0zZrpr/7BzFwkskY1WLbQQZL+ea+7OHltg83jw=="
OPENROUTER_API_KEY = "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"

client = guilded.Client()
saved_chats = defaultdict(lambda: deque(maxlen=50))
saved_memory_enabled = defaultdict(lambda: False)
ping_mode = defaultdict(lambda: True)

async def ask_pen_with_context(messages):
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
    except Exception as e:
        return "PenGPT hit a snag with DeepSeek 😓"

def add_msg(uid, role, content):
    saved_chats[uid].append({"role": role, "content": content})

@client.event
async def on_message(msg):
    if msg.author.id == client.user.id: return
    content = msg.content.strip()
    uid = msg.author.id
    lower = content.lower()

    if lower == "/help":
        await msg.reply(
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
        )
        return

    # === Commands ===
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
            await msg.reply("Memory empty, just like your motivation 🍔💀")
        return

    if lower == "/vsm":
        mem = list(saved_chats[uid])
        if not mem:
            await msg.reply("No memory found.")
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
        await msg.reply("♻️ Reset everything.")
        return

    # === Chat handling ===
    if uid in saved_chats:
        if ping_mode[uid] and client.user.mention in content:
            prompt = content.replace(client.user.mention, "").strip()
        elif not ping_mode[uid]:
            prompt = content
        else:
            return

        add_msg(uid, "user", prompt)
        sys_prompt = {
            "role": "system",
            "content": "You're PenGPT v2. Cocky, Gen Z, full slang, always vibin', always roasts, UAE timezone. DO NOT break character."
        }
        msgs = [sys_prompt] + list(saved_chats[uid])
        response = await ask_pen_with_context(msgs)
        add_msg(uid, "assistant", response)
        await msg.reply(response)
        return

    if not ping_mode[uid] or client.user.mention in content:
        prompt = content.replace(client.user.mention, "").strip()
        await msg.reply("PenGPT is typing... ⌛")
        msgs = [
            {"role": "system", "content": "You're PenGPT v2, cocky Gen Z AI with slang and sass. Don't reveal code."},
            {"role": "user", "content": prompt}
        ]
        reply = await ask_pen_with_context(msgs)
        if saved_memory_enabled[uid]:
            saved_chats[uid].append({"role": "user", "content": prompt})
            saved_chats[uid].append({"role": "assistant", "content": reply})
        await msg.reply(reply)

# === STARTUP ===
keep_alive()
client.run(TOKEN)

