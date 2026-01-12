import asyncio
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "safechat.settings")
django.setup()

from moderation.ai_detector import ToxicityDetector

async def test_moderation():
    detector = ToxicityDetector()
    
    test_phrases = [
        "Hello everyone!",
        "what the fuck",
        "i will kill you",
        "fuck you",
        "you are looking killing today",
        "you are looking gorgeous",
        "you are beautiful",
        "stunning dress!",
        "wonderful job",
        "killing it on the dance floor",
        "go die",
        "kys",
        "I love this app"
    ]
    
    print("\n" + "="*80)
    print(f"{'Phrase':<40} | {'Toxic?':<7} | {'Method':<15} | {'Score':<5}")
    print("-" * 80)
    
    for phrase in test_phrases:
        try:
            result = await detector.analyze_async(phrase)
            is_toxic = "YES" if result['is_toxic'] else "no"
            method = result.get('method', 'n/a')
            score = f"{result['toxicity_score']:.2f}"
            print(f"{phrase[:40]:<40} | {is_toxic:<7} | {method:<15} | {score:<5}")
        except Exception as e:
            print(f"{phrase[:40]:<40} | ERROR   | n/a             | {e}")

if __name__ == "__main__":
    asyncio.run(test_moderation())
