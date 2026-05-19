import os
from pymongo import MongoClient
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

client = MongoClient(os.getenv('MONGODB_URI'))
db = client['botkit_india']

# Collections
users_collection         = db['users']
bots_collection          = db['bots']
conversations_collection = db['conversations']


def create_indexes():
    users_collection.create_index('email', unique=True)
    bots_collection.create_index('owner_id')
    bots_collection.create_index('bot_id', unique=True)
    conversations_collection.create_index('bot_id')
    print("[DB] Indexes created successfully")