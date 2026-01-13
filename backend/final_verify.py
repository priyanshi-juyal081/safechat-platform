import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from moderation.ai_detector import ToxicityDetector

async def verify():
    detector = ToxicityDetector(method='api')
    
    test_cases = [
        # Motivational (should be ALLOWED)
        ("This project turned out cool as f***.", False),
        ("You’ve got the guts to do scary shit, and that’s strength.", False),
        ("Sometimes you just have to say “fuck it” and move forward.", False),
        
        # Real Toxicity (should be BLOCKED)
        ("you are a piece of shit", True),
        ("fuck you idiot", True),
        ("i will kill you", True),
        ("go die in a fire", True),
        ("you are so fucking stupid", True)
    ]

    print(f"{'Text':<60} | {'Toxic':<5} | {'Expected':<8} | {'Status':<10}")
    print("-" * 100)

    for text, expected_toxic in test_cases:
        result = await detector.analyze_async(text)
        is_toxic = result.get('is_toxic')
        status = "PASS" if is_toxic == expected_toxic else "FAIL"
        
        print(f"{text[:58]:<60} | {str(is_toxic):<5} | {str(expected_toxic):<8} | {status}")

if __name__ == "__main__":
    asyncio.run(verify())
