import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
from config import DISCORD_TOKEN, API_URL, API_TOKEN  # Import from config.py
from question_detector import is_question
import json
from typing import Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def get_message_history(channel, current_message, limit=5):
    messages = []
    async for msg in channel.history(limit=limit, before=current_message):
        if msg.author == bot.user:
            messages.append({"role": "assistant", "content": msg.content})
        else:
            messages.append({"role": "user", "content": msg.author.name + ": " + msg.content})
    return list(reversed(messages))  # Return messages in chronological order

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
        'Authorization': f'Bearer {API_TOKEN}'
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    return f"Error: Server returned status {response.status}"

                data = await response.text()
                complete_response = ""
                
                for line in data.split('\n'):
                    line = line.strip()
                    if line.startswith('data: '):
                        try:
                            json_data = json.loads(line[6:])
                            answer_part = json_data.get("answer", "")
                            if answer_part and answer_part != '[DONE]':
                                complete_response += answer_part
                        except json.JSONDecodeError:
                            logging.error(f"Failed to parse JSON: {line}")
                            continue
                
                return complete_response

    except aiohttp.ClientError as e:
        error_msg = f"Network error: {str(e)}"
        logging.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logging.error(error_msg)
        return error_msg

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

async def evaluate_unsw_relevance(message: str) -> Tuple[bool, str]:
    url = f'{API_URL}/api/v1/evaluate-logical-statement'
    
    payload = {
        "logical_statement": "This message or question is related to UNSW (University of New South Wales) course information",
        "context": message
    }
    
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logging.info(f'UNSW relevance evaluation result: {result}')
                    return result["is_true"], result["explanation"]
                return False, f"Error: Server returned status {response.status}"
    except Exception as e:
        return False, f"Error evaluating UNSW relevance: {str(e)}"

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

    # Check if the bot is mentioned
    if bot.user in message.mentions:
        async with message.channel.typing():
            response = await get_answer(message.content)
            await message.reply(response)
            
            additional_message = (
                "Powered by https://openonion.ai.\n"
            )
            await message.channel.send(additional_message)
        return

    if is_question(message.content):
        is_unsw_related, explanation = await evaluate_unsw_relevance(message.content)
        
        if not is_unsw_related:
            return  # Silently ignore non-UNSW questions

        async with message.channel.typing():
            response = await get_answer(message.content)
            await message.reply(response)
            
            additional_message = (
                "For better service, please visit https://openonion.ai.\n"
                "If you want to customize this bot, you can check the source code here: https://github.com/openonion/OnionPal"
            )
            await message.channel.send(additional_message)

    await bot.process_commands(message)

@bot.command(name='ask')
async def ask_question(ctx, *, question):
    logging.info(f'Received !ask command: {question}')
    
    is_unsw_related, explanation = await evaluate_unsw_relevance(question)
    
    if not is_unsw_related:
        return  # Silently ignore non-UNSW questions

    async with ctx.typing():
        previous_messages = await get_message_history(ctx.channel, ctx.message)
        messages = previous_messages + [{"role": "user", "content": question}]

        response = await get_answer(messages)
        await ctx.reply(response)
        
        additional_message = (
            "For better service, please visit https://openonion.ai.\n"
            "If you want to customize this bot, you can check the source code here: https://github.com/openonion/OnionPal"
        )
        await ctx.send(additional_message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
