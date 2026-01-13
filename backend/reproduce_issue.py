import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from moderation.ai_detector import ToxicityDetector, sentiment_analyzer

async def reproduce():
    detector = ToxicityDetector(method='api')
    examples = [
        "This project turned out cool as f***.",
        "You’ve got the guts to do scary shit, and that’s strength.",
        "Sometimes you just have to say “fuck it” and move forward.",
        "This is your life—own that shit.",
        "Growth happens when you face uncomfortable shit.",
        "You figured it out—smart as fuck.",
        "You’re doing meaningful shit, even if it’s hard.",
        "You’ve got the courage to say “no” to dumb shit.",
        "You trusted yourself, and that’s powerful as fuck.",
        "You don’t need to explain your shit to everyone.",
        "Life’s tough, but you’re tougher than that shit."
    ]

    print(f"{'Text':<60} | {'Toxic':<5} | {'Warn':<5} | {'Score':<6} | {'Sentiment':<10}")
    print("-" * 100)

    for text in examples:
        # We need to simulate the API response or use keyword method to test if keywords are the issue
        # Let's test both API and Keyword
        
        # Test analysis
        result = await detector.analyze_async(text)
        sentiment = sentiment_analyzer.polarity_scores(text)
        
        print(f"{text[:58]:<60} | {str(result.get('is_toxic')):<5} | {str(result.get('should_warn')):<5} | {result.get('toxicity_score', 0):.2f} | {sentiment['compound']:.2f}")

if __name__ == "__main__":
    asyncio.run(reproduce())
