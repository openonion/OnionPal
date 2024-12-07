import discord
from discord.ext import commands
from discord import app_commands
import logging
import aiohttp
import asyncio
from config import DISCORD_TOKEN, API_URL, API_TOKEN, OPENAI_API_KEY  # Import from config.py
from question_detector import is_question
import json
from typing import Tuple
from datetime import datetime, timedelta
from openai import AsyncOpenAI  # Update this import

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up OpenAI with new client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def get_message_history(channel, current_message, limit=10):
    messages = []
    async for msg in channel.history(limit=limit, before=current_message):
        if msg.author == bot.user:
            messages.append({"role": "assistant", "content": msg.content})
        else:
            messages.append({"role": "user", "content": msg.author.name + ": " + msg.content})
    return list(reversed(messages))  # Return messages in chronological order

async def get_answer(messages):
    url = f'{API_URL}/api/v1/chat/premium_message'
    
    # Ensure messages is in the correct format for the API
    if not isinstance(messages, list):
        messages = [{"role": "user", "content": messages}]
        
    payload = {
        "messages": messages,  # Now passing the full message history
        "model": "ofCourse",
        "stream": False,
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

async def analyze_availabilities(messages):
    try:
        # Format the messages for OpenAI
        prompt = """
As a scheduling assistant, analyze these availability messages and:
1. Find all overlapping time slots between users
2. Format the response in markdown
3. If no common time is found, suggest who needs to provide more options

Current availabilities:
"""
        for msg in messages:
            prompt += f"\n{msg['role']}: {msg['content']}"

        prompt += """

Please provide your analysis in this format:
## This Week
- Common slots: [list overlapping times]
- Alternative slots: [if no common slots, suggest alternatives]

## Next Week
- Common slots: [list overlapping times]
- Alternative slots: [if no common slots, suggest alternatives]

## Recommendations
[If needed, suggest who should provide more options and what times might work]
"""

        # Call OpenAI API with new format
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful scheduling assistant that analyzes availability and finds common time slots."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content

    except Exception as e:
        logging.error(f"Error in analyze_availabilities: {str(e)}")
        return f"Error analyzing availabilities: {str(e)}"

async def create_scheduling_thread(interaction, mentioned_users):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        thread_name = f"{today} - Schedule Finding"
        
        # Create thread in the channel where the command was used
        thread = await interaction.channel.create_thread(
            name=thread_name,
            auto_archive_duration=1440  # 24 hours
        )
        
        initial_message = (
            "👋 Let's find a common time!\n\n"
            f"Finding available time slots for: {', '.join(user.mention for user in mentioned_users)}\n\n"
            "Please share your availability for this week and next week using the format below:\n"
            "```\n"
            "This week:\n"
            "- Monday 2-5pm\n"
            "- Wednesday 1-4pm\n"
            "\nNext week:\n"
            "- Tuesday 3-6pm\n"
            "- Thursday 2-4pm\n"
            "```"
        )
        await thread.send(initial_message)
        return thread
        
    except discord.Forbidden:
        await interaction.followup.send("❌ Error: I don't have permission to create threads!")
        return None
    except Exception as e:
        await interaction.followup.send(f"❌ Error creating thread: {str(e)}")
        return None

@bot.event
async def on_ready():
    logging.info(f'{bot.user} has connected to Discord!')
    logging.info(f'Bot is in {len(bot.guilds)} guilds')
    await get_user_info()  # Call the new function to get user info

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Case 1: Bot mention
    if bot.user in message.mentions:
        async with message.channel.typing():
            previous_messages = await get_message_history(message.channel, message)  # Gets 10 messages
            messages = previous_messages + [{"role": "user", "content": message.content}]
            response = await get_answer(messages)
            await message.reply(response)
            
            additional_message = (
                "For better service, please visit https://openonion.ai.\n"
            )
            await message.channel.send(additional_message)

    # Case 2: Question detection
    if is_question(message.content):
        is_unsw_related, explanation = await evaluate_unsw_relevance(message.content)
        if not is_unsw_related:
            return

        async with message.channel.typing():
            previous_messages = await get_message_history(message.channel, message)  # Gets 10 messages
            messages = previous_messages + [{"role": "user", "content": message.content}]
            response = await get_answer(messages)
            await message.reply(response)
            
            additional_message = (
                "For better service, please visit https://openonion.ai.\n"
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
        previous_messages = await get_message_history(ctx.channel, ctx.message)  # Gets 10 messages
        messages = previous_messages + [{"role": "user", "content": question}]
        response = await get_answer(messages)
        await ctx.reply(response)
        
        additional_message = (
            "For better service, please visit https://openonion.ai.\n"
        )
        await ctx.send(additional_message)

@bot.tree.command(name="find_time", description="Find a common time for multiple users")
async def find_time_slash(interaction: discord.Interaction, users: str):
    try:
        # Defer the response since this might take a while
        await interaction.response.defer(ephemeral=False)
        
        # Parse mentioned users from the users parameter
        mentioned_users = [user for user in interaction.guild.members if str(user.id) in users]
        
        if not mentioned_users:
            await interaction.followup.send("⚠️ Please mention at least one user!\nExample: `/find_time @user1 @user2`")
            return

        # Create thread
        thread = await create_scheduling_thread(interaction, mentioned_users)
        if not thread:
            return

        # Track mentioned users and responses
        mentioned_users_ids = set(user.id for user in mentioned_users)
        mentioned_users_ids.add(interaction.user.id)  # Include the command author
        responses = {}

        def check(m):
            return m.author.id in mentioned_users_ids and m.channel.id == thread.id

        # Send initial confirmation
        await interaction.followup.send(f"Created scheduling thread: {thread.mention}")

        # Wait for responses with timeout
        timeout_duration = 300.0  # 5 minutes
        end_time = datetime.now() + timedelta(seconds=timeout_duration)

        while len(responses) < len(mentioned_users_ids) and datetime.now() < end_time:
            try:
                remaining_time = (end_time - datetime.now()).total_seconds()
                message = await bot.wait_for('message', timeout=remaining_time, check=check)
                
                if message.author.id not in responses:
                    responses[message.author.id] = message.content
                    
                    # Format messages for analysis
                    messages = [
                        {"role": "user", "content": f"{bot.get_user(user_id).name}: {content}"}
                        for user_id, content in responses.items()
                    ]
                    
                    # Get analysis from OpenAI
                    analysis = await analyze_availabilities(messages)
                    await thread.send(f"**Current Analysis:**\n{analysis}")
                    
                    # If not everyone has responded, mention remaining users
                    if len(responses) < len(mentioned_users_ids):
                        waiting_for = [bot.get_user(uid).mention for uid in mentioned_users_ids if uid not in responses]
                        await thread.send(f"📝 Still waiting to hear from: {', '.join(waiting_for)}")

            except asyncio.TimeoutError:
                await thread.send("⚠️ Scheduling timeout. Not all users responded within 5 minutes.")
                break

        # Final analysis
        if responses:
            if len(responses) == len(mentioned_users_ids):
                await thread.send("✅ Everyone has responded! Here's the final schedule analysis:")
            else:
                responded_users = [bot.get_user(uid).mention for uid in responses.keys()]
                missing_users = [bot.get_user(uid).mention for uid in mentioned_users_ids if uid not in responses]
                await thread.send(
                    "⚠️ **Scheduling Incomplete**\n\n"
                    f"Responded users: {', '.join(responded_users)}\n"
                    f"Missing responses from: {', '.join(missing_users)}\n\n"
                    "Here's the analysis based on available responses:"
                )
            
            final_messages = [
                {"role": "user", "content": f"{bot.get_user(user_id).name}: {content}"}
                for user_id, content in responses.items()
            ]
            final_analysis = await analyze_availabilities(final_messages)
            await thread.send(final_analysis)

    except Exception as e:
        logging.error(f"Error in find_time command: {str(e)}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

# Add this to sync commands on startup
@bot.event
async def on_ready():
    logging.info(f'{bot.user} has connected to Discord!')
    logging.info(f'Bot is in {len(bot.guilds)} guilds')
    await get_user_info()
    
    # Sync the command tree
    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logging.error(f"Failed to sync commands: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
