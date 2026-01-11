import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
print(f"API_KEY_FOUND: {bool(api_key)}")
if api_key:
    print(f"API_KEY_LENGTH: {len(api_key)}")
    print(f"API_KEY_START: {api_key[:5]}...")
