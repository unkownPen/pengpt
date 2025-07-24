import os
import aiohttp
from aiohttp import web
import guilded
import asyncio

GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")
BOT_USER_ID = "mjlxjn34"  # literal ID
BOT_MENTION = f"<@{BOT_USER_ID}>"

# Setup the bot
bot = guilded.Client()

# Optional web server for Render health checks or future webhooks
async def handle(request):
    return web.Response(text="Bot is alive.")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Web server running on port {port}")

# Message event
@bot.event
async def on_message(message):
    if message.created_by.bot:
        return

    content = message.content.strip()

    # Slash commands
    if content.startswith("/pen"):
        query = content[4:].strip()
        if not query:
            await message.reply("✏️ Say something after /pen, bruh.")
        else:
            await message.reply(f"💬 You said: {query}")
        return

    # Mention detection
    if BOT_MENTION in content:
        rest = content.replace(BOT_MENTION, "").strip()
        if not rest:
            await message.reply("👋 Yooo you pinged me but said nothing 💀")
        else:
            await message.reply(f"👀 You pinged me and said: {rest}")
        return

# Main runner
async def main():
    await start_web_server()
    await bot.login(GUILDED_TOKEN)

# Start everything
asyncio.run(main())
