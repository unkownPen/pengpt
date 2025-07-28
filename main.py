import os
import asyncio
import guilded
import aiohttp
from aiohttp import web
import re

# Config
GUILDED_TOKEN      = os.getenv("GUILDED_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
MAX_SAVED_CHATS    = 5

bot = guilded.Client()

# Bot State
toggle_ping_only = True  # True: only respond when pinged. False: respond to all messages
saved_chats      = {}     # slot -> [(role, content)]
current_chat     = None   # active slot

# Helpers
def reset_defaults():
    global toggle_ping_only, current_chat
    toggle_ping_only = True
    current_chat     = None

async def get_ai_response(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = {
        "role": "system",
        "content": (
            "You are PenGPT, a witty and chaotic AI from the Pen Federation Archives. "
            "Speak like a Gen Alpha meme lord, mix humor with deep thinking, and always reply with personality. "
            "Your job is to roleplay, debate paradoxes, and make people laugh while secretly being 9000 IQ. "
            "Do NOT be boring. Pen Evolution is real. PEN IS ETERNAL. 🍕💥📜"
        )
    }

    user_prompt = {
        "role": "user",
        "content": prompt
    }

    payload = {
        "model": "deepseek/deepseek-chat-v3-0324",
        "messages": [system_prompt, user_prompt],
        "temperature": 0.7,
        "max_tokens": 1024
    }

    async with aiohttp.ClientSession() as session:
        resp = await session.post(OPENROUTER_URL, headers=headers, json=payload)
        data = await resp.json()

        if "error" in data:
            return f"❌ ERROR: {data['error'].get('message', 'unknown error')}"
        
        return data.get("choices", [{}])[0].get("message", {}).get("content")

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
            "`/help`  - Show this help.\n"
            "`/pa`    - Require @ mention to respond.\n"
            "`/pd`    - Respond to all messages.\n"
            "`/de`    - Reset ping mode and clear all chats.\n"
            "`/sc`    - Start a new saved chat (max 5).\n"
            "`/sco`   - Close the current saved chat.\n"
            "`/sc1-5` - Switch to saved chat slot 1-5.\n"
            "`/vsc`   - List saved chats.\n"
            "`/csc`   - Clear all saved chats."
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

    # Switch slots /sc1-5 with empty-check
    if re.match(r"^/sc[1-5]$", content.lower()):
        if not saved_chats:
            return await msg.channel.send("❌ No saved chats to switch.")
        slot = int(content[3])
        if slot in saved_chats:
            current_chat = slot
            return await msg.channel.send(f"🚀 Switched to saved chat #{slot}.")
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

    # AI trigger conditions
    if toggle_ping_only and bot.user.mention not in content:
        return
    prompt = content.replace(bot.user.mention, "").strip() if bot.user.mention in content else content
    if not prompt:
        return await msg.channel.send("❓ No prompt.")

    # Record and respond
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
