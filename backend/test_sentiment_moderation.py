import asyncio
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safechat.settings')
django.setup()

from moderation.ai_detector import ToxicityDetector

async def test_sentiment():
    detector = ToxicityDetector(method='api')
    
    test_cases = [
        "you look so fucking gorgeous",  # Positive Sentiment
        "you are a fucking idiot",       # Negative Sentiment
        "i love this fucking song",      # Positive Sentiment
        "i will fucking kill you",       # Negative Sentiment/Threat
    ]
    
    print("\n--- Sentiment-Aware Moderation Test ---")
    for phrase in test_cases:
        result = await detector.analyze_async(phrase)
        
        status = "TOXIC" if result['is_toxic'] else "CLEAN"
        warn = "YES" if result.get('should_warn') else "NO"
        sentiment = result.get('sentiment_score', 0)
        
        print(f"Text:    '{phrase}'")
        print(f"Masked:  '{result.get('masked_text')}'")
        print(f"Result:  [{status}] (Sentiment: {sentiment:.2f})")
        print(f"Warning: {warn}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_sentiment())
