import os
import asyncio
import guilded
import aiohttp
from aiohttp import web

GUILDED_TOKEN = os.getenv("GUILDED_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

bot = guilded.Client()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return

    # Only respond if the bot was pinged/mentioned
    if bot.user.mention in message.content:
        prompt = message.content.replace(bot.user.mention, "").strip()

        if prompt == "":
            await message.reply("❓ You pinged me but didn’t say anything.")
            return

        await message.reply("🤖 Thinking...")

        response = await get_openrouter_response(prompt)
        if response:
            await message.reply(response)
        else:
            await message.reply("❌ Failed to get a response.")

async def get_openrouter_response(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek/deepseek-chat-v3-0324",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_API_URL, headers=headers, json=data) as resp:
                result = await resp.json()
                return result["choices"][0]["message"]["content"]
    except Exception as e:
        print("❌ Error:", e)
        return None

# Render web stuff
async def handle_root(request):
    return web.Response(text="✅ Guilded bot is running!")

async def handle_health(request):
    return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/healthz", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()

    await bot.start(GUILDED_TOKEN)

asyncio.run(main())
