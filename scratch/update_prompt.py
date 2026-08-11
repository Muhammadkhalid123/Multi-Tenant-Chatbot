import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB Database Connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/chatbot')
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_default_database()

for bot_id in ['tecwrites', 'indie_global']:
    bot = db.bot_configs.find_one({'bot_id': bot_id})
    if bot:
        prompt = bot.get('system_prompt', '')
        if 'You MUST always respond with a valid JSON object' not in prompt:
            prompt += '\n\nIMPORTANT FORMAT INSTRUCTIONS: You MUST always respond with a valid JSON object containing exactly these three keys:\n1. "reply": (string) Your conversational response to the user.\n2. "lead_required": (boolean) true if you need to capture their contact info, false otherwise.\n3. "extracted_name": (string or null) the user\'s name if they provided it.\nDo NOT use keys like "greeting" or "message".'
            db.bot_configs.update_one({'bot_id': bot_id}, {'$set': {'system_prompt': prompt}})
            print(f'Updated system prompt for {bot_id} bot in MongoDB.')
        else:
            print(f'System prompt for {bot_id} already contains the format instructions.')
    else:
        print(f'Bot {bot_id} not found in database.')
