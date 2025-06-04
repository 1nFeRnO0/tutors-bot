import os
from dotenv import load_dotenv

load_dotenv()
 
TUTOR_BOT_TOKEN = os.getenv("TUTOR_BOT_TOKEN")
PARENT_BOT_TOKEN = os.getenv("PARENT_BOT_TOKEN")

if not TUTOR_BOT_TOKEN:
    raise ValueError("TUTOR_BOT_TOKEN not found in environment variables") 

if not PARENT_BOT_TOKEN:
    raise ValueError("PARENT_BOT_TOKEN not found in environment variables") 