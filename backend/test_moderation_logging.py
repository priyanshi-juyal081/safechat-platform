import os
import django
import asyncio
import sys

# Setup Django environment
sys.path.append(os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
# django.setup() # Not strictly needed if we just import the detector, but good practice

from moderation.ai_detector import ToxicityDetector

async def test_detection():
    detector = ToxicityDetector(method='api')
    
    print("\n--- Testing Keyword Detection ---")
    # 'hate' is in the toxic_keywords list
    await detector.analyze_async("I hate you so much")
    
    print("\n--- Testing OpenAI Detection ---")
    # 'poison' might not be in the local list but should be flagged by OpenAI
    # (Assuming OPENAI_API_KEY is set in the environment)
    await detector.analyze_async("You are a poisonous person who deserves to suffer.")

if __name__ == "__main__":
    asyncio.run(test_detection())
