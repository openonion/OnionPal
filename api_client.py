import aiohttp
from config import API_URL

async def get_answer(question):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/answer", json={"question": question}) as response:
            if response.status == 200:
                data = await response.json()
                return data['answer']
            else:
                return f"Error: Unable to get answer. Status code: {response.status}"