import discord
from discord.ext import commands
import logging
import aiohttp
import os
import asyncio
from dotenv import load_dotenv
from question_detector import is_question
import json

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_URL = os.getenv('API_URL')
API_TOKEN = os.getenv('API_TOKEN')  # Read the API token from .env

# Set up logging
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def get_answer(question):
    url = f'{API_URL}/api/v1/chat/message'

    payload = {
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ],
        "stream": False,
        "model": "default",
        "temperature": 0,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "top_p": 0
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_TOKEN}'  # Add the API token to the headers
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            buffer = ""
            async for line in response.content:
                if line:
                    data = line.decode('utf-8').strip()
                    logging.info(f"Received data: {data}")

                    if data.startswith("data:"):
                        try:
                            json_data = json.loads(data.replace("data: ", "").strip())
                            answer_part = json_data.get("answer", "")
                            if answer_part and answer_part != '[DONE]':
                                buffer += answer_part
                                words = buffer.split(' ')
                                for word in words[:-1]:
                                    yield word
                                buffer = words[-1]  # Keep the last word which might be incomplete
                        except json.JSONDecodeError:
                            logging.error(f"Failed to parse JSON: {data}")

            if buffer:
                yield buffer

@bot.event
async def on_ready():
    logging.info(f'{bot.user} has connected to Discord!')
    logging.info(f'Bot is in {len(bot.guilds)} guilds')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    logging.info(f'Received message: {message.content}')

    if is_question(message.content):
        async with message.channel.typing():
            display_message = ""
            msg = await message.channel.send("...")  # Send an initial placeholder message
            async for word in get_answer(message.content):
                display_message += word + " "
                logging.info(f'Updating message: {display_message.strip()}')
                await msg.edit(content=display_message)

    await bot.process_commands(message)

@bot.command(name='ask')
async def ask_question(ctx, *, question):
    logging.info(f'Received !ask command: {question}')
    async with ctx.typing():
        display_message = ""
        msg = await ctx.send("...")  # Send an initial placeholder message
        async for word in get_answer(question):
            display_message += word + " "
            logging.info(f'Updating message: {display_message.strip()}')
            await msg.edit(content=display_message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
