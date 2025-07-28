import os
import asyncio
import guilded
import aiohttp
from aiohttp import web

GUILDED_TOKEN        = os.getenv("GUILDED_TOKEN")
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL   = "https://openrouter.ai/api/v1/chat/completions"
MAX_SAVED_CHATS      = 5

bot = guilded.Client()

# State
ping_mode     = True
saved_chats   = {}        # slot (1–5) -> list of (role, content)
current_chat  = None       # slot number
recording     = True       # always record since esc removed

# Helpers
def reset_defaults():
    global ping_mode, current_chat
    ping_mode    = True
    current_chat = None

async def get_openrouter_response(prompt):
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek/deepseek-chat-v3-0324",
            "messages": [{"role":"user","content":prompt}],
            "temperature":0.7,
            "max_tokens":1024
        }
        async with session.post(OPENROUTER_API_URL, headers=headers, json=data) as resp:
            j = await resp.json()
            if "choices" in j:
                return j["choices"][0]["message"]["content"]
            return None

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")

@bot.event
async def on_message(message):
    global ping_mode, current_chat

    if message.author.id == bot.user.id:
        return

    content = message.content.strip()

    # Slash commands
    if content.lower() == "/help":
        return await message.channel.send(
            "**Commands:**\n"
            "`/help` `/pa` `/pd` `/de`\n"
            "`/sc` `/sco`\n"
            "`/vsc` `/csc`\n"
        )

    if content.lower() == "/pa":
        ping_mode = True
        return await message.channel.send("✅ Ping mode ON")

    if content.lower() == "/pd":
        ping_mode = False
        return await message.channel.send("❌ Ping mode OFF")

    if content.lower() == "/de":
        reset_defaults()
        return await message.channel.send("🔄 Reset to defaults (ping ON)")

    # Saved chat commands
    if content.lower() == "/sc":
        if len(saved_chats) >= MAX_SAVED_CHATS:
            return await message.channel.send(f"❌ Max {MAX_SAVED_CHATS} saved chats reached.")
        for i in range(1, MAX_SAVED_CHATS+1):
            if i not in saved_chats:
                saved_chats[i] = []
                current_chat = i
                return await message.channel.send(f"💾 Started saved chat #{i}.")
    
    if content.lower() == "/sco":
        if current_chat and current_chat in saved_chats:
            slot = current_chat
            current_chat = None
            return await message.channel.send(f"📂 Closed saved chat #{slot}.")
        return await message.channel.send("❌ No open saved chat to close.")

    if content.lower() == "/vsc":
        if not saved_chats:
            return await message.channel.send("no saved chats")
        text = "**Saved chats:**\n" + "\n".join(
            f"{i}. {len(saved_chats[i])} messages" for i in saved_chats
        )
        vmsg = await message.channel.send(text)
        for i in saved_chats:
            await vmsg.add_reaction(f"{i}\u20E3")
        return

    if content.lower() == "/csc":
        if not saved_chats:
            return await message.channel.send("no saved chats")
        saved_chats.clear()
        current_chat = None
        return await message.channel.send("🧹 Cleared all saved chats.")

    # AI ping logic
    if (bot.user.mention not in content) or not ping_mode:
        return

    prompt = content.replace(bot.user.mention, "").strip()
    if not prompt:
        return await message.channel.send("❓ You pinged but no prompt.")

    if current_chat:
        saved_chats[current_chat].append(("user", prompt))

    thinking = await message.channel.send("🤖 Thinking...")
    resp = await get_openrouter_response(prompt)

    if resp:
        await thinking.edit(content=resp)
        if current_chat:
            saved_chats[current_chat].append(("assistant", resp))
    else:
        await thinking.edit(content="❌ Failed to get a reply. Check credits.")

@bot.event
async def on_reaction_add(reaction, user):
    msg = reaction.message
    if msg.author.id != bot.user.id or not msg.content.startswith("**Saved chats**"):
        return
    count = next((r.count for r in msg.reactions if r.emoji == reaction.emoji), 0)
    if count >= 2 and reaction.emoji.endswith("\u20E3"):
        slot = int(reaction.emoji[0])
        if slot in saved_chats:
            last_ai = next((c for r, c in reversed(saved_chats[slot]) if r=="assistant"), None)
            if last_ai:
                await msg.edit(content=f"💬 Chat #{slot} last AI message:\n{last_ai}")

# Web service for Render
async def handle_root(request): return web.Response(text="✅ Bot running")
async def handle_health(request): return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/healthz", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site   = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()
    await bot.start(GUILDED_TOKEN)

asyncio.run(main())
