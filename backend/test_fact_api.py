import os
import requests
from dotenv import load_dotenv
load_dotenv()

def test_fact_check(text):
    api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {
        "query": text,
        "key": api_key
    }
    
    print(f"🔍 Checking facts for: '{text}'")
    response = requests.get(url, params=params)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        claims = data.get('claims', [])
        print(f"Claims found: {len(claims)}")
        for i, claim in enumerate(claims[:3]):
            print(f"Claim {i+1}: {claim.get('text')}")
            for review in claim.get('claimReview', []):
                print(f"  Rating: {review.get('textualRating')}")
                print(f"  Publisher: {review.get('publisher', {}).get('name')}")
    else:
        print(f"Error: {response.text}")

# Test with a known false claim
test_fact_check("The moon is made of green cheese")
test_fact_check("vaccines cause autism")
