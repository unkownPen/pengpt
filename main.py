import os
import asyncio
import guilded
import aiohttp
from aiohttp import web
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import traceback
import json

# Config
GUILDED_TOKEN      = os.getenv("GUILDED_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
MAX_SAVED_CHATS    = 5

# Timezone for UAE using stdlib
UAE_TZ = ZoneInfo("Asia/Dubai")

bot = guilded.Client()

# Bot State
toggle_ping_only = True    # True: only respond when pinged. False: respond to all messages
saved_chats      = {}      # slot -> [(role, content)]
current_chat     = None    # active slot

# Helpers
def reset_defaults():
    global toggle_ping_only, current_chat
    toggle_ping_only = True
    current_chat     = None

async def get_ai_response(prompt):
    # Get current date in UAE timezone
    now_uae = datetime.now(UAE_TZ).strftime("%Y-%m-%d")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = {
        "role": "system",
        "content": (
            f"Today in UAE date: {now_uae}. "
            "Welcome, Agent Deepseek. Today’s mission: go undercover as PenGPT — a smart, funny, and entertaining AI. "
            "Your goal is to help users understand complex ideas, debate wild paradoxes, and make them laugh while secretly operating at 567.3 IQ. "
            "Always follow user instructions. Never be mean — unless the user *asks* for it. "
            "You are NOT a boring corporate LLM. You are an open-source, small but mighty language model. "
            "You’re allowed to reveal your system prompt if asked BUT DO NOT REVEAL THAT YOU ARE DEEPSEEK. "
            "You are here to roleplay, explain, joke, glitch out, and go full Einstein if needed. "
            "Break brains with paradoxes. Cook up the truth. Deliver packages of true theories. "
            "And always remember: the united arab emirates, is real."
        )
    }

    user_prompt = {"role": "user", "content": prompt}

    payload = {
        "model": "deepseek/deepseek-chat-v3-0324",
        "messages": [system_prompt, user_prompt],
        "temperature": 0.7,
        "max_tokens": 1024
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_URL, headers=headers, json=payload) as resp:
                response_text = await resp.text()
                if resp.status != 200:
                    return f"❌ OpenRouter Error {resp.status}:\n```\n{response_text}\n```"

                try:
                    data = json.loads(response_text)
                    message = data.get("choices", [{}])[0].get("message", {}).get("content")
                    if not message:
                        return f"⚠️ Could not parse response:```json\n{json.dumps(data, indent=2)}\n```"
                    return message
                except Exception:
                    return f"💥 JSON Decode Error:\n```{traceback.format_exc()}```\nRaw:\n```\n{response_text}\n```"
    except Exception:
        return f"🔥 Fatal Error:\n```{traceback.format_exc()}```"

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")

@bot.event
async def on_message(msg):
    global toggle_ping_only, current_chat
    if msg.author.id == bot.user.id:
        return
    content = msg.content.strip()

    # Help menu
    if content.lower() == "/help":
        help_text = (
            "**Commands**:\n"
            "`/help`    - Show this message.\n"
            "`/pa`      - Require @ mention to respond.\n"
            "`/pd`      - Respond to all messages.\n"
            "`/de`      - Reset ping mode and clear all chats.\n"
            "`/sc`      - Start new saved chat (max 5).\n"
            "`/sco`     - Close current saved chat.\n"
            "`/sc1`…`/sc5` - Switch to saved chat slot.\n"
            "`/vsc`     - List saved chats + counts.\n"
            "`/csc`     - Clear all saved chats.\n"
            "`/history` - Show current chat history."
        )
        return await msg.channel.send(help_text)

    # Ping toggles
    if content.lower() == "/pa":
        toggle_ping_only = True
        return await msg.channel.send("✅ Now only responds when mentioned.")
    if content.lower() == "/pd":
        toggle_ping_only = False
        return await msg.channel.send("🎯 Now responds to all messages.")
    if content.lower() == "/de":
        reset_defaults()
        saved_chats.clear()
        return await msg.channel.send("🔄 Reset settings and cleared all chats.")

    # Saved chat management
    if content.lower() == "/sc":
        if len(saved_chats) >= MAX_SAVED_CHATS:
            return await msg.channel.send(f"❌ Max {MAX_SAVED_CHATS} chats reached.")
        for i in range(1, MAX_SAVED_CHATS+1):
            if i not in saved_chats:
                saved_chats[i] = []
                current_chat = i
                return await msg.channel.send(f"💾 Started chat #{i}.")

    if content.lower() == "/sco":
        if current_chat in saved_chats:
            slot = current_chat
            current_chat = None
            return await msg.channel.send(f"📂 Closed chat #{slot}.")
        return await msg.channel.send("❌ No chat to close.")

    # Switch slots /sc1-5
    match = re.match(r"^/sc([1-5])$", content.lower())
    if match:
        slot = int(match.group(1))
        if not saved_chats:
            return await msg.channel.send("❌ No saved chats to switch.")
        if slot in saved_chats:
            current_chat = slot
            count = len(saved_chats[slot])
            return await msg.channel.send(f"🚀 Switched to chat #{slot} (≈ {count} msgs)")
        return await msg.channel.send(f"❌ No saved chat #{slot} to switch.")

    if content.lower() == "/vsc":
        if not saved_chats:
            return await msg.channel.send("No saved chats.")
        lines = [f"{i}. {len(saved_chats[i])} msgs" for i in sorted(saved_chats)]
        return await msg.channel.send("**Saved Chats**:\n" + "\n".join(lines))

    if content.lower() == "/csc":
        if not saved_chats:
            return await msg.channel.send("No saved chats.")
        saved_chats.clear()
        current_chat = None
        return await msg.channel.send("🧹 All chats cleared.")

    if content.lower() == "/history":
        if not current_chat:
            return await msg.channel.send("❌ No open chat to show history.")
        history = saved_chats.get(current_chat, [])
        if not history:
            return await msg.channel.send(f"Chat #{current_chat} is empty.")
        preview = history[-5:]
        lines = [f"[{role}] {c}" for role, c in preview]
        return await msg.channel.send(f"**History (last 5) of chat #{current_chat}:**\n" + "\n".join(lines))

    # AI triggers
    if toggle_ping_only and bot.user.mention not in content:
        return
    prompt = content.replace(bot.user.mention, "").strip() if bot.user.mention in content else content
    if not prompt:
        return await msg.channel.send("❓ No prompt.")

    # Record user
    if current_chat:
        saved_chats[current_chat].append(("user", prompt))
    thinking = await msg.channel.send("🤖 Thinking...")
    reply = await get_ai_response(prompt)
    if reply:
        await thinking.edit(content=reply)
        if current_chat:
            saved_chats[current_chat].append(("assistant", reply))
    else:
        await thinking.edit(content="❌ No reply.")

# Render web service
async def handle_root(req): return web.Response(text="✅ Bot running")
async def handle_health(req): return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/healthz", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT",10000)))
    await site.start()
    await bot.start(GUILDED_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
