import os
from dotenv import find_dotenv, dotenv_values

dotenv_path = find_dotenv()

print(dotenv_path)
config = dotenv_values(dotenv_path)
 
TUTOR_BOT_TOKEN = config["TUTOR_BOT_TOKEN"]
PARENT_BOT_TOKEN = config["PARENT_BOT_TOKEN"]

if not TUTOR_BOT_TOKEN:
    raise ValueError("TUTOR_BOT_TOKEN not found in environment variables") 

if not PARENT_BOT_TOKEN:
    raise ValueError("PARENT_BOT_TOKEN not found in environment variables") 