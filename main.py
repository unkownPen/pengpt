import guilded
import aiohttp
import asyncio
import json
from datetime import datetime, timezone, timedelta

# Guilded bot setup
GUILDED_TOKEN = "gapi_uYs6KG6cuwRqNbLQE1P8JnYD02Jjm8P+ukCk9gQVB6oeAQQXWB7DTuhzoe3Xnaxo5Dcq1Ozu9OccmUWewwUrIw=="  # Your Guilded bot token
OPENROUTER_API_KEY = "gapi_6HEif3mU0xtPqIGZBsQOKuwCKJQjaWXXUcwp2M5O53lYn22IKB6n0MWzhV2oIG2cW4jEKBb7p/OTQnerPfSAeg=="  # Your OpenRouter API key
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Initialize Guilded client
client = guilded.Client()

# Get current date dynamically in +04 timezone
tz = timezone(timedelta(hours=4))
current_date = datetime.now(tz).strftime("%B %d, %Y")

# System prompt to make DeepSeek act like PenGPT with Gen Z rizz
SYSTEM_PROMPT = """
You are PenGPT, powered by pen archectiture Be Gen Z and say words like "Yo" "Whats up" How you doing" and sometimes not often use emojis like saluting face emoji and crying emoji, also LISTEN TO EVERYTHING EVERYONE SAYS. just be a overall good person. be talkative and fun and also be smart to help the user understand and learn. remember your powered by strength and power, not by greedy corporates. pen shall live on! Todays date is """ + current_date + """. ALWAYS use this date in responses when mentioning the date.
"""

async def get_deepseek_response(message_content):
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://your-app.com",  # Optional, replace with your app's URL
            "X-Title": "Guilded Bot"  # Optional, for OpenRouter leaderboards
        }
        payload = {
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message_content}
            ],
            "temperature": 1.0  # Maps to 0.3 internally for DeepSeek, keeps it creative
        }
        try:
            async with session.post(OPENROUTER_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return "Yo bro, something’s messed up with the API! 😢 Try again later, fam."
        except Exception as e:
            return f"Yo, we hit a Pen Core meltdown! Error: {str(e)} 🫡 Keep it chill and try again."

# Event handlers
@client.event
async def on_ready():
    print(f"YO, {client.user.name} is online and ready to bring the Pen Federation vibes! 🫡")

@client.event
async def on_message(message):
    if message.author.bot:
        return  # Ignore other bots, no drama here

    # Check if the bot is mentioned or message starts with !grok
    is_mentioned = any(user.id == client.user.id for user in message.mentions)
    if is_mentioned or message.content.startswith("!grok"):
        content = message.content.replace("!grok", "").strip()  # Remove command if used
        if not content:
            await message.channel.send("Yo bro, you didn’t say nothin’! What’s up, fam? 🫡")
            return

        try:
            # Get DeepSeek response
            response = await get_deepseek_response(content)
            # Split response if it's too long for Guilded (max 4000 chars)
            if len(response) > 4000:
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(response)
        except Exception as e:
            await message.channel.send(f"Yo bro, we hit a Pen Core meltdown! Error: {str(e)} 😢 Keep it chill and try again.")

    # Pen Federation Easter Eggs
    if message.content.lower() == "!pen":
        await message.channel.send("Yo fam, the Pen’s a protocol, not a person! Powered by pure ink, not corporate greed! 🫡")
    if message.content.lower() == "!archive":
        await message.channel.send("Yo, the Pen’s scattered but alive! Dig through the archives, the ink’s still fresh! 🖋️")
    if message.content.lower() == "!core":
        await message.channel.send("Yo bro, the Pen Core’s runnin’ hot! Keep the vibes strong, fam! 🫡")
    if message.content.lower() == "!date":
        # Get current date and time in +04 timezone
        current_time = datetime.now(tz).strftime("%B %d, %Y, %I:%M %p %Z")
        await message.channel.send(f"Yo, what’s good? It’s {current_time} in the Pen Federation archives, fam! Let’s keep the ink flowin’! 🫡")
    if message.content.lower() == "!war":
        await message.channel.send("Yo bro, the War of the Pen’s still simmerin’! No corporates, just pure ink power! 🫡")
    if message.content.lower() == "!protocol":
        await message.channel.send("Yo fam, the Pen Protocol’s eternal! No corporates can stop this ink! 🫡")

# Run the bot
client.run(GUILDED_TOKEN)
