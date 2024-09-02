import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
from config import DISCORD_TOKEN, API_URL, API_TOKEN  # Import from config.py
from question_detector import is_question
import json

# Set up logging
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def get_answer(question):
    url = f'{API_URL}/api/v1/chat/premium_message'

    payload = {
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ],
        "stream": False,
        "model": "ofCourse",
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

async def get_user_info():
    url = f'{API_URL}/api/v1/user/getUserInfo'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_TOKEN}'  # Add the API token to the headers
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as response:
            if response.status == 200:
                user_info = await response.json()
                formatted_info = (
                    f"User Info:\n"
                    f"  Email: {user_info.get('email')}\n"
                    f"  First Name: {user_info.get('first_name')}\n"
                    f"  Last Name: {user_info.get('last_name')}\n"
                    f"  Created At: {user_info.get('created_at')}\n"
                    f"  Updated At: {user_info.get('updated_at')}\n"
                    f"  Credits: {user_info.get('credits')}\n"
                    f"  Nickname: {user_info.get('nickname')}\n"
                    f"  Description: {user_info.get('description')}\n"
                    f"  Invitation Code: {user_info.get('invitation_code')}\n"
                )
                logging.info(formatted_info)
            else:
                logging.error(f"Failed to get user info: {response.status}")

@bot.event
async def on_ready():
    logging.info(f'{bot.user} has connected to Discord!')
    logging.info(f'Bot is in {len(bot.guilds)} guilds')
    await get_user_info()  # Call the new function to get user info

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
            
            # Send additional information after the response
            additional_message = (
                "For better service, please visit https://openonion.ai.\n"
                "If you want to customize this bot, you can check the source code here: https://github.com/openonion/OnionPal"
            )
            await message.channel.send(additional_message)

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
        
        # Send additional information after the response
        additional_message = (
            "For better answer and service, please visit https://openonion.ai.\n"
            "If you want to customize this bot, you can check the source code here: https://github.com/openonion/OnionPal"
        )
        await ctx.send(additional_message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
