import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def verify_phrase(text):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env")
        return

    print(f"Using API Key: {api_key[:8]}...")
    client = AsyncOpenAI(api_key=api_key)
    
    try:
        print(f"Checking phrase: '{text}'")
        response = await client.moderations.create(
            model="omni-moderation-latest",
            input=text
        )
        result = response.results[0]
        
        print("\n--- OpenAI Results ---")
        print(f"Flagged: {result.flagged}")
        
        # Accessing scores safely
        if hasattr(result.category_scores, 'model_dump'):
            scores = result.category_scores.model_dump()
        else:
            scores = result.category_scores.__dict__
            
        print("Category Scores:")
        for cat, score in scores.items():
            if score > 0.01: # Show significant scores
                print(f"  {cat}: {score:.4f}")
                
    except Exception as e:
        print(f"Error calling OpenAI: {e}")

if __name__ == "__main__":
    phrase = "i will end you today"
    asyncio.run(verify_phrase(phrase))
