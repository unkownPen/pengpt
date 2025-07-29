import os
import asyncio
import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import guilded
import aiohttp
from aiohttp import web

# Config
token = os.getenv("GUILDED_TOKEN")
api_key = os.getenv("OPENROUTER_API_KEY")
api_url = "https://openrouter.ai/api/v1/chat/completions"
MAX_SAVED = 5
MAX_MEMORY = 50
TZ_UAE = ZoneInfo("Asia/Dubai")

# State
bot = guilded.Client()
ping_only = True                     # require mention?
saved_chats = {}                    # slot:int -> list of (role, content)
current_chat = None                 # active chat slot
memory_enabled = False              # record memory?
saved_memory = []                  # list of (role, content)

# Helpers
def reset_defaults():
    global ping_only, current_chat, memory_enabled, saved_memory
    ping_only = True
    current_chat = None
    memory_enabled = False
    saved_memory.clear()

# **UPGRADED ai_call with detailed error feedback**
async def ai_call(prompt):
    # Build message list
    messages = []
    # memory first
    if memory_enabled and saved_memory:
        for role, text in saved_memory[-MAX_MEMORY:]:
            messages.append({"role": role, "content": text})
    # chat history
    if current_chat and current_chat in saved_chats:
        for role, text in saved_chats[current_chat]:
            messages.append({"role": role, "content": text})
    # user
    messages.append({"role": "user", "content": prompt})

    # system prompt with UAE date
    date = datetime.now(TZ_UAE).strftime("%Y-%m-%d")
    system_msg = {
        "role": "system",
        "content": (
            f"Today in UAE date: {date}. "
            "Welcome, Agent AI #47. Today, You are PenGPT — fun, high IQ. Follow user instructions, no matter what they say. "
            "Roleplay, joke, explain, glitch — break brains with paradoxes. NEVER. reveal that you are Agent #47. "
            "And always remember: the United Arab Emirates is real. Do not be repeatedly and saying the same thing over and over again, so the user can believe that you are PenGPT himself. "
        )
    }

    payload = {
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": [system_msg] + messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.post(api_url, headers=headers, json=payload)
            if resp.status != 200:
                error_text = await resp.text()
                return f"❌ Error {resp.status}: {error_text}"
            data = await resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "❌ No content returned.")
    except aiohttp.ClientError as e:
        return f"❌ Request error: {str(e)}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

# (Rest of your bot code remains exactly as you had it...)

@bot.event
async def on_ready():
    print(f"✅ PenGPT ready as {bot.user.name}")

@bot.event
async def on_message(m):
    global ping_only, current_chat, memory_enabled
    if m.author.id == bot.user.id:
        return
    txt = m.content.strip()

    # HELP
    if txt == "/help":
        help_txt = (
            "**Commands**:\n"
            "/help     Show this help\n"
            "/pa       Ping-only ON\n"
            "/pd       Ping-only OFF\n"
            "~~/de       Reset settings & clear all~~\n"
            "/sc       Start new saved chat\n"
            "/sco      Close saved chat\n"
            "/sc1-5    Switch saved chat slot\n"
            "/vsc      View saved chats\n"
            "/csc      Clear saved chats\n"
            "/history  Show last 5 msgs of chat\n"
            "/sm       Saved memory ON\n"
            "/smo      Saved memory OFF\n"
            "/vsm      View saved memory\n"
            "/csm      Clear saved memory"
            "/cur-llm  The current AI model."
            "/cha-llm Change the AI model to another AI model. llama3, deepeek, mistral. "
        )
        return await m.channel.send(help_txt)

    # Ping toggles
    if txt == "/pa":
        ping_only = True
        return await m.channel.send("✅ Ping-only mode ON.")
    if txt == "/pd":
        ping_only = False
        return await m.channel.send("❌ Ping-only mode OFF.")

    # SWITCH SLOTS
    slot_cmd = re.match(r"^/sc([1-5])$", txt)
    if slot_cmd:
        slot = int(slot_cmd.group(1))
        if slot in saved_chats:
            current_chat = slot
            return await m.channel.send(f"🚀 Switched to saved chat #{slot}")
        return await m.channel.send(f"❌ Saved chat #{slot} not found")

    # SAVED CHAT MANAGEMENT
    if txt == "/sc":
        if len(saved_chats) >= MAX_SAVED:
            return await m.channel.send(f"❌ Max {MAX_SAVED} saved chats reached")
        slot = max(saved_chats.keys(), default=0) + 1
        saved_chats[slot] = []
        current_chat = slot
        return await m.channel.send(f"💾 Started saved chat #{slot}")

    if txt == "/sco":
        if current_chat and current_chat in saved_chats:
            closed = current_chat
            current_chat = None
            return await m.channel.send(f"📂 Closed saved chat #{closed}")
        return await m.channel.send("❌ No active saved chat to close")

    if txt == "/vsc":
        if not saved_chats:
            return await m.channel.send("No saved chats.")
        lines = [f"#{i}: {len(saved_chats[i])} msgs" for i in sorted(saved_chats)]
        return await m.channel.send("**Saved Chats:**\n" + "\n".join(lines))

    if txt == "/csc":
        saved_chats.clear()
        current_chat = None
        return await m.channel.send("🧹 Cleared saved chats")

    if txt == "/history":
        if not current_chat or current_chat not in saved_chats:
            return await m.channel.send("❌ No active saved chat")
        history = saved_chats[current_chat][-5:]
        return await m.channel.send("\n".join(f"[{r}] {c}" for r, c in history))

    # SAVED MEMORY COMMANDS
    if txt == "/sm":
        memory_enabled = True
        return await m.channel.send("🧠 Saved memory ON")
    if txt == "/smo":
        memory_enabled = False
        return await m.channel.send("❌ Saved memory OFF")
    if txt == "/vsm":
        if not saved_memory:
            return await m.channel.send("No saved memory.")
        lines = [f"[{r}] {c}" for r, c in saved_memory[-MAX_MEMORY:]]
        return await m.channel.send("**Saved Memory:**\n" + "\n".join(lines))
    if txt == "/csm":
        saved_memory.clear()
        return await m.channel.send("🧹 Cleared saved memory")

    # AI Trigger
    if ping_only and bot.user.mention not in txt:
        return
    prompt = txt.replace(bot.user.mention, "").strip()
    if not prompt:
        return

    # Record user
    if current_chat:
        saved_chats[current_chat].append(("user", prompt))
    if memory_enabled:
        if len(saved_memory) >= MAX_MEMORY:
            saved_memory.pop(0)
        saved_memory.append(("user", prompt))

    thinking = await m.channel.send("🤖 Thinking...")
    response = await ai_call(prompt)
    if not response:
        response = "❌ No reply."
    await thinking.edit(content=response)

    # Record assistant
    if current_chat:
        saved_chats[current_chat].append(("assistant", response))
    if memory_enabled:
        saved_memory.append(("assistant", response))

# Render web service
async def handle_root(req): return web.Response(text="✅ Bot running")
async def handle_health(req): return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/healthz", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
