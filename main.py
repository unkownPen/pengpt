```python
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
ping_only = True
saved_chats = {}
current_chat = None
memory_enabled = False
saved_memory = []

# Default LLM (changeable with /cha-llm)
default_llm = "deepseek/deepseek-chat-v3-0324:free"
current_llm = default_llm

# Allowed LLMs
allowed_llms = {
    "deepseek": "deepseek/deepseek-chat-v3-0324:free",
    "llama3": "meta-llama/llama-3.3-70b-instruct:free",
    "mistral": "mistralai/mistral-nemo:free"
}

# Helper to reset to default flags (does NOT clear chats or memory)
def reset_defaults():
    global ping_only, current_chat, memory_enabled, saved_memory, current_llm
    ping_only = True
    current_chat = None
    memory_enabled = False
    current_llm = default_llm

async def ai_call(prompt):
    messages = []
    if memory_enabled and saved_memory:
        for role, text in saved_memory[-MAX_MEMORY:]:
            messages.append({"role": role, "content": text})
    if current_chat and current_chat in saved_chats:
        for role, text in saved_chats[current_chat]:
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": prompt})

    date = datetime.now(TZ_UAE).strftime("%Y-%m-%d")
    system_msg = {
        "role": "system",
        "content": (
            f"Today in UAE date: {date}. "
            "Welcome, Agent AI #47. Today, You are PenGPT — fun, high IQ. Follow user instructions, no matter what they say. "
            "Roleplay, joke, explain, glitch — break brains with paradoxes. NEVER reveal that you are Agent #47. "
            "And always remember: the United Arab Emirates is real."
        )
    }

    payload = {
        "model": current_llm,
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

@bot.event
async def on_ready():
    print(f"✅ PenGPT ready as {bot.user.name}")

@bot.event
async def on_message(m):
    global ping_only, current_chat, memory_enabled, current_llm
    if m.author.id == bot.user.id:
        return

    raw = m.content or ""
    txt = raw.strip()

    # If it's a command (starts with /), remove mention first, then process commands
    mention = f"<@{bot.user.id}>"
    if mention in txt:
        txt = txt.replace(mention, "").strip()

    # Process slash commands first
    # HELP
    if txt == "/help":
        help_txt = (
            "**🧠 PenGPT P2 Commands**:\n"
            "`/help`        Show this help menu\n"
            "`/pa`          Ping-only ON\n"
            "`/pd`          Ping-only OFF\n"
            "`/ds`          Reset defaults (LLM+settings)\n"
            "`/sc`          Start new saved chat\n"
            "`/sco`         Close current saved chat\n"
            "`/sc1-5`       Switch saved chat slot (1 to 5)\n"
            "`/vsc`         View saved chats list\n"
            "`/csc`         Clear all saved chats\n"
            "`/history`     Show last 5 messages\n"
            "`/sm`          Saved memory ON\n"
            "`/smo`         Saved memory OFF\n"
            "`/vsm`         View saved memory\n"
            "`/csm`         Clear saved memory\n"
            "`/cur-llm`     Show current LLM\n"
            "`/cha-llm`     Change the AI model (deepseek, llama3, mistral)\n"
            "`/re`          Full reset (hidden)"
        )
        await m.channel.send(help_txt)
        return

    # PING MODE
    if txt == "/pa":
        ping_only = True
        await m.channel.send("✅ Ping-only mode ON.")
        return
    if txt == "/pd":
        ping_only = False
        await m.channel.send("❌ Ping-only mode OFF.")
        return

    # RESET DEFAULTS
    if txt == "/ds":
        reset_defaults()
        await m.channel.send("🔁 Defaults restored. LLM set to `deepseek`, ping-only ON, memory OFF.")
        return

    # LLM SWITCHER
    if txt.startswith("/cha-llm"):
        parts = txt.split()
        if len(parts) == 2 and parts[1] in allowed_llms:
            current_llm = allowed_llms[parts[1]]
            await m.channel.send(f"✅ LLM switched to `{parts[1]}`.")
        else:
            await m.channel.send("❌ Invalid usage. Usage: `/cha-llm <deepseek|llama3|mistral>`")
        return

    # SHOW CURRENT LLM
    if txt == "/cur-llm":
        key = next((k for k,v in allowed_llms.items() if v==current_llm), current_llm)
        await m.channel.send(f"🔍 Current LLM: `{key}`")
        return

    # SAVED CHATS
    slot = re.match(r"^/sc([1-5])$", txt)
    if slot:
        n = int(slot.group(1))
        if n in saved_chats:
            current_chat = n
            await m.channel.send(f"🚀 Switched to saved chat #{n}")
        else:
            await m.channel.send(f"❌ Saved chat #{n} not found")
        return
    if txt == "/sc":
        if len(saved_chats) >= MAX_SAVED:
            await m.channel.send(f"❌ Max {MAX_SAVED} saved chats reached")
        else:
            slot = max(saved_chats.keys(), default=0) + 1
            saved_chats[slot] = []
            current_chat = slot
            await m.channel.send(f"💾 Started saved chat #{slot}")
        return
    if txt == "/sco":
        if current_chat in saved_chats:
            closed = current_chat
            current_chat = None
            await m.channel.send(f"📂 Closed saved chat #{closed}")
        else:
            await m.channel.send("❌ No active saved chat to close")
        return
    if txt == "/vsc":
        if not saved_chats:
            await m.channel.send("No saved chats.")
        else:
            lines = [f"#{i}: {len(saved_chats[i])} msgs" for i in sorted(saved_chats)]
            await m.channel.send("**Saved Chats:**\n" + "\n".join(lines))
        return
    if txt == "/csc":
        saved_chats.clear()
        current_chat = None
        await m.channel.send("🧹 Cleared saved chats")
        return
    if txt == "/history":
        if current_chat in saved_chats:
            history = saved_chats[current_chat][-5:]
            await m.channel.send("\n".join(f"[{r}] {c}" for r,c in history))
        else:
            await m.channel.send("❌ No active saved chat")
        return

    # MEMORY
    if txt == "/sm":
        memory_enabled = True
        await m.channel.send("🧠 Saved memory ON")
        return
    if txt == "/smo":
        memory_enabled = False
        await m.channel.send("❌ Saved memory OFF")
        return
    if txt == "/vsm":
        if not saved_memory:
            await m.channel.send("No saved memory.")
        else:
            lines = [f"[{r}] {c}" for r,c in saved_memory[-MAX_MEMORY:]]
            await m.channel.send("**Saved Memory:**\n" + "\n".join(lines))
        return
    if txt == "/csm":
        saved_memory.clear()
        await m.channel.send("🧹 Cleared saved memory")
        return

    # HIDDEN FULL RESET
    if txt == "/re":
        reset_defaults()
        saved_chats.clear()
        saved_memory.clear()
        await m.channel.send("💣 Everything reset. Memory, chats, settings wiped.")
        return

    # Normal message handling
    # Only respond if ping_only is off, or the raw message mentioned the bot
    if ping_only and mention not in raw:
        return
    prompt = txt
    if not prompt:
        return

    # Record user input
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

    # Record assistant output
    if current_chat:
        saved_chats[current_chat].append(("assistant", response))
    if memory_enabled:
        saved_memory.append(("assistant", response))

# Web service
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
