# test.py
from dotenv import load_dotenv
import os

load_dotenv()

key = os.getenv("OPENAI_API_KEY")
if key:
    print("API Key: SUCCESS →", key[:10] + "...")
else:
    print("API Key: FAILED → Not found or invalid .env")