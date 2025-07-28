import os
import asyncio
import guilded
import aiohttp
from aiohttp import web

# Config
GUILDED_TOKEN      = os.getenv("GUILDED_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
MAX_SAVED_CHATS    = 5
KEYCAP_EMOJIS      = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]

bot = guilded.Client()

# Bot State
toggle_ping_only = True  # True: only respond when pinged. False: respond to all messages
saved_chats      = {}    # slot -> [(role, content)]
current_chat     = None  # active slot

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
    payload = {
        "model": "deepseek/deepseek-chat-v3-0324",
        "messages": [{"role":"user","content":prompt}],
        "temperature":0.7,
        "max_tokens":1024
    }
    async with aiohttp.ClientSession() as session:
        resp = await session.post(OPENROUTER_URL, headers=headers, json=payload)
        data = await resp.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        return None

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")

@bot.event
async def on_message(msg):
    global toggle_ping_only, current_chat
    if msg.author.id == bot.user.id:
        return
    content = msg.content.strip()

    # Slash commands
    if content.lower() == "/help":
        return await msg.channel.send(
            "**Commands**:\n"
            "`/help` - Show this help.\n"
            "`/pa`   - Require @ mention to respond.\n"
            "`/pd`   - Respond to every message.\n"
            "`/de`   - Reset ping mode and close chat.\n"
            "`/sc`   - Start a saved chat.\n"
            "`/sco`  - Close current saved chat.\n"
            "`/vsc`  - List saved chats (react 1️⃣–5️⃣ to open).\n"
            "`/csc`  - Clear all saved chats."
        )

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

    # Saved chat commands
    if content.lower() == "/sc":
        if len(saved_chats) >= MAX_SAVED_CHATS:
            return await msg.channel.send(f"❌ Max {MAX_SAVED_CHATS} chats.")
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
    if content.lower() == "/vsc":
        if not saved_chats:
            return await msg.channel.send("no saved chats")
        lines = [f"{i}. {len(saved_chats[i])} msgs" for i in saved_chats]
        vmsg = await msg.channel.send("**Saved Chats**:\n" + "\n".join(lines))
        for i in saved_chats:
            await vmsg.add_reaction(KEYCAP_EMOJIS[i-1])
        return
    if content.lower() == "/csc":
        if not saved_chats:
            return await msg.channel.send("no saved chats")
        saved_chats.clear()
        current_chat = None
        return await msg.channel.send("🧹 All chats cleared.")

    # AI Trigger
    if toggle_ping_only and bot.user.mention not in content:
        return

    prompt = content.replace(bot.user.mention, "").strip() if bot.user.mention in content else content
    if not prompt:
        return await msg.channel.send("❓ No prompt.")

    # record
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

@bot.event
async def on_reaction_add(reaction, user):
    # Only respond to reactions on saved-chat listings
    m = reaction.message
    if m.author.id != bot.user.id or not m.content.startswith("**Saved Chats**"):
        return
    emoji = reaction.emoji
    if emoji in KEYCAP_EMOJIS:
        total = next((r.count for r in m.reactions if r.emoji == emoji), 0)
        if total >= 2:
            slot = KEYCAP_EMOJIS.index(emoji) + 1
            if slot in saved_chats:
                last = next((c for r,c in reversed(saved_chats[slot]) if r=="assistant"), None)
                if last:
                    await m.edit(content=f"💬 Chat #{slot} last AI:\n{last}")

# Render Web Server
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

asyncio.run(main())
