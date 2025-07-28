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
    # ✅ Don’t respond to itself
    if message.author.id == bot.user.id:
        return

    # ✅ Only respond if pinged
    if bot.user.mention not in message.content:
        return

    # Extract prompt
    prompt = message.content.replace(bot.user.mention, "").strip()
    if not prompt:
        await message.reply("❓ You pinged me but didn’t give a prompt.")
        return

    # Send "Thinking..." placeholder
    thinking_msg = await message.reply("🤖 Thinking...")

    # Get response from OpenRouter
    response = await get_openrouter_response(prompt)

    # Edit original message with final reply
    if response:
        await thinking_msg.edit(content=response)
    else:
        await thinking_msg.edit(content="❌ Couldn’t get a valid reply. Might be outta credits.")

async def get_openrouter_response(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek/deepseek-chat-v3-0324",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_API_URL, headers=headers, json=data) as resp:
                result = await resp.json()

                if "choices" in result:
                    return result["choices"][0]["message"]["content"]
                elif "error" in result:
                    print("❌ OpenRouter API Error:", result["error"])
                    return None
                else:
                    print("❌ Unexpected response format:", result)
                    return None
    except Exception as e:
        print("❌ Exception:", e)
        return None

# 🛜 Render Web Routes
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
