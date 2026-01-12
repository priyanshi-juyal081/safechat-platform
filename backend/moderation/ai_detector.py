import re
import os
import time
import asyncio
import requests
import httpx
from typing import Dict, List, Tuple

# -------------------------------
# Main Detector
# -------------------------------

class ToxicityDetector:
    """Main toxicity detection class"""

    def __init__(self, method='api'):
        """
        method: 'keyword', 'transformer', or 'api'
        """
        self.method = method
        self.keyword_detector = KeywordDetector()

        if method == 'transformer':
            self.model_detector = TransformerDetector()
        elif method == 'api':
            self.api_detector = APIDetector()

    def analyze(self, text: str) -> Dict:
        """Synchronous analyze method (legacy/fallback)"""
        if self.method == 'keyword':
            return self.keyword_detector.detect(text)
        elif self.method == 'transformer':
            return self.model_detector.detect(text)
        elif self.method == 'api':
            return self.api_detector.detect(text)
        else:
            return self.keyword_detector.detect(text)

    async def analyze_async(self, text: str) -> Dict:
        """Asynchronous analyze method (preferred)"""
        # Always run local keyword check first for speed and whitelist/custom rules
        keyword_result = self.keyword_detector.detect(text)
        if keyword_result['is_toxic']:
            print(f"   [-] Local detector flagged: {keyword_result['detected_words']}")
            return keyword_result

        if self.method == 'transformer':
            return self.model_detector.detect(text)
        elif self.method == 'api':
            return await self.api_detector.detect_async(text)
        else:
            return keyword_result


# -------------------------------
# Keyword Fallback Detector
# -------------------------------

class KeywordDetector:
    """Fast keyword-based toxicity detection"""

    def __init__(self):
        self.toxic_keywords = {
            'high': [
                'hate', 'die', 'death', 'nazi', 'terrorist',
                'rape', 'murder', 'violence', 'abuse', 'attack'
            ],
            'medium': [
                'stupid', 'idiot', 'dumb', 'moron', 'loser', 'pathetic',
                'trash', 'garbage', 'worthless', 'useless', 'disgusting',
                'fuck', 'shit', 'bitch', 'asshole', 'fucking'
            ],
            'low': [
                'shut up', 'annoying', 'boring', 'lame',
                'bad', 'terrible', 'awful', 'horrible',
                'fuck', 'shit', 'fucking', 'damn'
            ]
        }

        self.allowed_phrases = [
            'what the fuck', 'wtf', 'damn it', 'holy shit', 
            'no shit', 'bullshit', 'piece of shit'
        ]

        self.harassment_patterns = [
            r'\bkys\b',
            r'\bgo\s+die\b',
            # Targeted profanity: "you fuck", "fuck you", etc.
            r'\byou\s+.*fuck',
            r'\bfuck\s+you',
            r'\byou\s+suck',
            r'\bkill\s+yourself\b',
            r'\bkill\s+you\b',
            r'\bkilling\s+you\b',
        ]

        self.compliment_keywords = [
            'gorgeous', 'beautiful', 'amazing', 'stunning', 'wonderful',
            'great', 'awesome', 'lovely', 'pretty', 'handsome', 'perfect',
            'intelligent', 'smart', 'kind', 'friendly'
        ]

    def detect(self, text: str) -> Dict:
        text_lower = text.lower()
        
        # 0. Strip whitelisted phrases first to prevent detection
        temp_text = text_lower
        for phrase in self.allowed_phrases:
            temp_text = temp_text.replace(phrase, " [CLEANED] ")

        detected_words = []
        severity_scores = {'high': 0, 'medium': 0, 'low': 0}

        # Helper: allow non-word separators between characters to match obfuscated words
        def make_fuzzy_pattern(word: str) -> str:
            chars = [re.escape(c) for c in word]
            return r"\b" + r"\W*".join(chars) + r"\b"

        for severity, keywords in self.toxic_keywords.items():
            for keyword in keywords:
                pattern = make_fuzzy_pattern(keyword)
                # Check against the cleaned text
                if re.search(pattern, temp_text):
                    detected_words.append(keyword)
                    severity_scores[severity] += 1

        for pattern in self.harassment_patterns:
            if re.search(pattern, text_lower):
                detected_words.append('harassment_pattern')
                severity_scores['high'] += 1

        toxicity_score = (
            severity_scores['high'] * 1.0 +
            severity_scores['medium'] * 0.6 +
            severity_scores['low'] * 0.2
        )
        toxicity_score = min(toxicity_score / 1.5, 1.0)
        
        is_toxic = toxicity_score >= 0.4 or severity_scores['high'] > 0

        print(f"   [DEBUG] Keyword detector: is_toxic={is_toxic}, score={toxicity_score}, words={detected_words}")

        return {
            'is_toxic': is_toxic,
            'toxicity_score': toxicity_score,
            'categories': severity_scores,
            'detected_words': detected_words,
            'method': 'keyword'
        }


# -------------------------------
# Transformer Detector (Optional)
# -------------------------------

class TransformerDetector:
    def __init__(self):
        try:
            from transformers import pipeline
            self.classifier = pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                top_k=None
            )
        except Exception as e:
            print("Transformer load failed:", e)
            self.classifier = None

    def detect(self, text: str) -> Dict:
        if not self.classifier:
            return KeywordDetector().detect(text)

        try:
            results = self.classifier(text)[0]
            scores = {r['label'].lower(): r['score'] for r in results}
            toxicity_score = scores.get('toxic', 0.0)

            return {
                'is_toxic': toxicity_score > 0.5,
                'toxicity_score': toxicity_score,
                'categories': scores,
                'detected_words': [],
                'method': 'transformer'
            }
        except Exception:
            return KeywordDetector().detect(text)


# -------------------------------
# API Detector (OPENAI)
# -------------------------------

class APIDetector:
    """
    Uses OpenAI Moderation API (Async & Sync)
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("[!] OPENAI_API_KEY not set in environment!")

    def detect(self, text: str) -> Dict:
        """Synchronous detection"""
        if not self.api_key:
            print("[!] OPENAI_API_KEY not set, falling back to keywords")
            return KeywordDetector().detect(text)
        return self._openai_moderation_sync(text)

    async def detect_async(self, text: str) -> Dict:
        """Asynchronous detection"""
        if not self.api_key:
            print("[!] OPENAI_API_KEY not set, falling back to keywords")
            return KeywordDetector().detect(text)
        return await self._openai_moderation_async(text)

    def _process_results(self, result, text) -> Dict:
        """Helper to process OpenAI results"""
        # Convert category_scores to a regular dict
        if hasattr(result.category_scores, '__dict__'):
            scores = {k: v for k, v in result.category_scores.__dict__.items() if not k.startswith('_')}
        elif hasattr(result.category_scores, 'model_dump'):
            scores = result.category_scores.model_dump()
        else:
            scores = dict(result.category_scores)
        
        # Calculate max toxicity score
        toxicity_score = max(scores.values()) if scores else 0.0
        print(f"   [DEBUG] OpenAI Scores: {scores}")
        print(f"   [DEBUG] Max Score: {toxicity_score}")
        
        # Initial flagging decision
        is_toxic = result.flagged or any(score > 0.7 for score in scores.values())
        
        # Override for whitelisted phrases
        if is_toxic:
            keyword_detector = KeywordDetector()
            text_lower = text.lower().strip()
            for phrase in keyword_detector.allowed_phrases:
                clean_text = re.sub(r'[^\w\s]', '', text_lower)
                clean_phrase = re.sub(r'[^\w\s]', '', phrase)
                if clean_text == clean_phrase or (phrase in text_lower and len(text_lower) < len(phrase) + 5):
                    print(f"   [-] Overriding OpenAI flag for whitelisted phrase: '{phrase}'")
                    is_toxic = False
                    break
            
            # Additional override for compliments
            if is_toxic:
                for compliment in KeywordDetector().compliment_keywords:
                    if compliment in text_lower:
                        # Only override if it's not a severe violation (e.g. not hate speech score > 0.9)
                        if toxicity_score < 0.85:
                            print(f"   [-] Overriding OpenAI flag for compliment: '{compliment}'")
                            is_toxic = False
                            break

        if is_toxic:
            print(f"   [+] OpenAI flagged as TOXIC! (Score: {toxicity_score})")
            return {
                'is_toxic': True,
                'toxicity_score': toxicity_score,
                'categories': scores,
                'detected_words': [cat for cat, score in scores.items() if score > 0.5],
                'method': 'openai_moderation'
            }

        return {
            'is_toxic': False,
            'toxicity_score': toxicity_score,
            'categories': scores,
            'detected_words': [],
            'method': 'openai_moderation'
        }

    def _openai_moderation_sync(self, text: str) -> Dict:
        max_attempts = 3
        backoff = 1

        for attempt in range(1, max_attempts + 1):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)

                print(f"\n[?] Calling OpenAI Moderation API (SYNC) (attempt {attempt}/{max_attempts})")
                print(f"   Text: '{text}'")

                response = client.moderations.create(
                    model="text-moderation-latest",
                    input=text
                )
                result = response.results[0]
                return self._process_results(result, text)

            except Exception as e:
                msg = str(e)
                print(f"   [X] OpenAI moderation error (attempt {attempt}/{max_attempts}): {e}")
                
                if attempt < max_attempts and ("too many requests" in msg.lower() or "429" in msg):
                    print(f"   [!] Rate limited, waiting {backoff} seconds...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                
                print(f"   [!] Falling back to keyword detector")
                return KeywordDetector().detect(text)

    async def _openai_moderation_async(self, text: str) -> Dict:
        max_attempts = 3
        backoff = 1

        for attempt in range(1, max_attempts + 1):
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.api_key)

                print(f"\n[?] Calling OpenAI Moderation API (ASYNC) (attempt {attempt}/{max_attempts})")
                # print(f"   Text: '{text}'")

                response = await client.moderations.create(
                    model="text-moderation-latest",
                    input=text
                )
                result = response.results[0]
                return self._process_results(result, text)

            except Exception as e:
                msg = str(e)
                print(f"   [X] OpenAI Async moderation error (attempt {attempt}/{max_attempts}): {e}")
                
                # If rate limited, retry
                if attempt < max_attempts and ("too many requests" in msg.lower() or "429" in msg):
                    print(f"   [!] Rate limited, waiting {backoff} seconds...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                
                print(f"   [!] Falling back to keyword detector")
                return KeywordDetector().detect(text)


# -------------------------------
# Extra Quality Checks
# -------------------------------

def detect_spam(text: str) -> bool:
    return (
        len(text) > 500 or
        text.count('http') > 3
    )


def detect_repeated_characters(text: str) -> bool:
    return bool(re.search(r'(.)\1{5,}', text))


def detect_all_caps(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 5:
        return False
    return sum(c.isupper() for c in letters) / len(letters) > 0.7


async def comprehensive_check_async(text: str) -> Dict:
    detector = ToxicityDetector(method='api')
    result = await detector.analyze_async(text)

    return {
        **result,
        'is_spam': detect_spam(text),
        'has_repeated_chars': detect_repeated_characters(text),
        'is_shouting': detect_all_caps(text),
    }

def comprehensive_check(text: str) -> Dict:
    detector = ToxicityDetector(method='api')
    result = detector.analyze(text)

    return {
        **result,
        'is_spam': detect_spam(text),
        'has_repeated_chars': detect_repeated_characters(text),
        'is_shouting': detect_all_caps(text),
    }


async def is_factually_correct_async(text: str) -> Tuple[bool, str]:
    """
    Async Fact Check using Google API (httpx)
    """
    api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    if not api_key:
        print("[!] GOOGLE_FACT_CHECK_API_KEY not set, skipping fact check")
        return True, ""

    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "query": text,
            "key": api_key
        }
        
        print(f"Checking facts (ASYNC) for: '{text}'")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            
        print(f"API Response Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()

        claims = data.get('claims', [])
        if not claims:
            return True, ""

        for claim in claims:
            claim_review = claim.get('claimReview', [])
            if claim_review:
                rating = claim_review[0].get('textualRating', '').lower()
                publisher = claim_review[0].get('publisher', {}).get('name', 'Unknown')
                
                false_keywords = ['false', 'incorrect', 'misleading', 'fake', 'rumor', 'untrue', 'error']
                if any(k in rating for k in false_keywords):
                    reason = f"Fact Check: This claim was rated '{rating}' by {publisher}."
                    print(f"Fact check failed: {reason}")
                    return False, reason

        return True, ""

    except Exception as e:
        print(f"Fact Check API Error: {e}")
        return True, ""

def is_factually_correct(text: str) -> Tuple[bool, str]:
    """
    Checks if the text is factually correct using Google Fact Check API.
    Returns (is_correct, reason)
    """
    api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    if not api_key:
        print("⚠️ GOOGLE_FACT_CHECK_API_KEY not set, skipping fact check")
        return True, ""

    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "query": text,
            "key": api_key
        }
        
        print(f"🔍 Checking facts for: '{text}' using Google Fact Check API")
        response = requests.get(url, params=params)
        print(f"📡 API Response Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        print(f"📊 API Data Keys: {list(data.keys())}")

        claims = data.get('claims', [])
        print(f"🔎 Claims found: {len(claims)}")
        if not claims:
            return True, ""

        # Check the first claim's rating
        for claim in claims:
            claim_review = claim.get('claimReview', [])
            if claim_review:
                rating = claim_review[0].get('textualRating', '').lower()
                publisher = claim_review[0].get('publisher', {}).get('name', 'Unknown')
                
                # Broad keywords for false/misleading information
                false_keywords = ['false', 'incorrect', 'misleading', 'fake', 'rumor', 'untrue', 'error']
                if any(k in rating for k in false_keywords):
                    reason = f"Fact Check: This claim was rated '{rating}' by {publisher}."
                    print(f"🚨 Fact check failed: {reason}")
                    return False, reason

        return True, ""

    except Exception as e:
        print(f"❌ Fact Check API Error: {e}")
        return True, "" # Default to true on API failure to avoid blocking users


if __name__ == '__main__':
    # Test script
    import asyncio
    async def main():
        detector = ToxicityDetector(method='api')
        text = "go kill yourself"
        print(f"Testing Async Detection on: {text}")
        res = await detector.analyze_async(text)
        print(res)

    asyncio.run(main())



class AIImageDetector:
    def __init__(self):
        from django.conf import settings
        self.api_user = getattr(settings, 'SIGHTENGINE_API_USER', None)
        self.api_secret = getattr(settings, 'SIGHTENGINE_API_SECRET', None)
        self.api_url = "https://api.sightengine.com/1.0/check.json"

    def detect(self, image_url: str) -> Dict:
        if not self.api_user or not self.api_secret:
            return {'is_ai_generated': False, 'score': 0.0, 'error': 'API Credentials missing'}

        try:
            params = {
                'models': 'genai',
                'api_user': self.api_user,
                'api_secret': self.api_secret,
                'url': image_url
            }

            response = requests.get(self.api_url, params=params, timeout=15)
            
            if response.status_code != 200:
                return {'is_ai_generated': False, 'score': 0.0, 'error': f"API Error {response.status_code}"}

            data = response.json()

            if data.get('status') == 'success':
                type_scores = data.get('type', {})
                ai_score = type_scores.get('ai_generated', 0.0)
                is_ai = ai_score > 0.80  # Threshold
                
                return {
                    'is_ai_generated': is_ai,
                    'score': ai_score,
                    'details': type_scores
                }
            
            return {'is_ai_generated': False, 'score': 0.0, 'error': data.get('error', {}).get('message', 'Unknown error')}

        except Exception as e:
            print(f"Sightengine Error: {e}")
            return {'is_ai_generated': False, 'score': 0.0, 'error': str(e)}
