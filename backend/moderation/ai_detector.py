import re
import os
import time
import asyncio
import requests
import httpx
from typing import Dict, List, Tuple
from better_profanity import profanity
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize sentiment analyzer
sentiment_analyzer = SentimentIntensityAnalyzer()

# Initialize profanity detector
profanity.load_censor_words() # Load default words
profanity.add_censor_words([
    'fuckwad', 'dickhead', 'shithead', 'pussy', 'cunt', 'faggot', 'fuck'
]) # Add some extras 

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
            self.api_detector = SightengineDetector() # Switch to Sightengine

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
        text_lower = text.lower()
        
        # Pre-check for motivational context to guide sentiment
        kw_detector = self.keyword_detector
        found_motivational = any(word in text_lower for word in kw_detector.motivational_keywords)
        found_compliment = any(word in text_lower for word in kw_detector.compliment_keywords)
        has_positive_context = found_motivational or found_compliment

        # 1. FAST PATH: Keyword check first
        keyword_result = self.keyword_detector.detect(text)
        
        # If the keyword detector is very confident it's toxic (high severity words)
        # OR if it's very clearly clean (no words detected at all)
        # and we don't have positive context that might override it, we can short-circuit
        is_clearly_toxic = keyword_result['categories']['high'] > 0
        is_clery_clean = not keyword_result['detected_words'] and not has_positive_context

        # Add sentiment score (VADER is fast, run it anyway)
        sentiment = sentiment_analyzer.polarity_scores(text)
        compound_score = sentiment['compound']
        
        if has_positive_context:
            if compound_score <= 0:
                soft_profanity = ['fuck', 'shit', 'fucking', 'damn', 'fuck it']
                if any(p in text_lower for p in soft_profanity):
                    compound_score += 0.9 if 'fuck it' in text_lower else 0.8

        keyword_result['sentiment_score'] = compound_score
        keyword_result['has_positive_context'] = has_positive_context
        keyword_result['masked_text'] = mask_text(text)

        # Higher threshold for positivity if motivational
        is_positive = compound_score > (0.2 if has_positive_context else 0.4)

        if is_clearly_toxic and not is_positive:
            print(f"   [FAST-PATH] Keyword detector high confidence (Toxic). Skipping API.")
            keyword_result['should_warn'] = True
            return keyword_result
        
        if is_clery_clean and not has_positive_context:
            # print(f"   [FAST-PATH] Keyword detector high confidence (Clean). Skipping API.")
            keyword_result['should_warn'] = False
            return keyword_result

        # 2. API Check fallback for nuanced cases
        if self.method == 'api':
            print(f"   [Nuance] Nuanced case detected, calling {self.api_detector.__class__.__name__}...")
            api_result = await self.api_detector.detect_async(text)
            
            api_result['masked_text'] = keyword_result['masked_text']
            api_result['sentiment_score'] = compound_score
            api_result['has_positive_context'] = has_positive_context
            
            # If Sightengine flagged it as an insult strictly
            is_insult = api_result.get('categories', {}).get('insult', 0) > 0.7
            
            if api_result['is_toxic']:
                # If it's a positive/motivational sentiment and NOT a direct insult, allow it
                if is_positive and not is_insult:
                    api_result['is_toxic'] = False
                    api_result['should_warn'] = False
                    print(f"   [SENTIMENT] Motivational/Positive context detected, allowing profanity.")
                    return api_result
                else:
                    api_result['should_warn'] = True
                return api_result
            
            # If API is clean but keywords caught something
            if keyword_result['is_toxic']:
                if is_positive:
                    keyword_result['is_toxic'] = False
                    keyword_result['should_warn'] = False
                    print(f"   [SENTIMENT] Positive sentiment detected ({compound_score}), allowing message (keyword-fallback).")
                else:
                    keyword_result['should_warn'] = True
                return keyword_result
            
            api_result['should_warn'] = False
            return api_result

        # Other methods (transformer or direct keyword)
        if self.method == 'transformer':
            return self.model_detector.detect(text)
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
                'rape', 'murder', 'violence', 'abuse', 'attack',
                'stab', 'shoot', 'kill', 'gun', 'bomb', 'murderer',
                'blood', 'corpse', 'destroy', 'weapon', 'assassin'
            ],
            'medium': [
                'stupid', 'idiot', 'dumb', 'moron', 'loser', 'pathetic',
                'trash', 'garbage', 'worthless', 'useless', 'disgusting',
                'fuck', 'shit', 'bitch', 'asshole', 'fucking', 'fuckwad', 'dickhead'
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
            r'\byou\s+.*fuck',
            r'\bfuck\s+you',
            r'\byou\s+suck',
            r'\bkill\s+yourself\b',
            r'\bkill\s+you\b',
            r'\bkilling\s+you\b',
            r'\bstab\s+you\b',
            r'\bshoot\s+you\b',
            r'\bi\s+will\s+kill\s+you\b',
            r'\bi\s+will\s+stab\s+you\b',
            r'\bi\s+will\s+shoot\s+you\b',
            r'\bi\s+am\s+going\s+to\s+kill\s+you\b',
            r'\bi\s+am\s+going\s+to\s+stab\s+you\b',
            r'\bkill\s+him\b',
            r'\bkill\s+her\b',
            r'\bkill\s+them\b'
        ]

        self.compliment_keywords = [
            'gorgeous', 'beautiful', 'amazing', 'stunning', 'wonderful',
            'great', 'awesome', 'lovely', 'pretty', 'handsome', 'perfect',
            'intelligent', 'smart', 'kind', 'friendly', 'cool', 'strength',
            'powerful', 'courage', 'growth', 'strength', 'tougher', 'proud'
        ]

        self.motivational_keywords = [
            'guts', 'strength', 'smart', 'powerful', 'tougher', 'meaningful',
            'courage', 'growth', 'proud', 'own it', 'keep going', 'forward',
            'trust', 'believe', 'hard work', 'focus', 'keep at it', 'life',
            'everything', 'tough', 'say no', 'explain your', 'figure it out',
            'fuck it', 'say'
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

        # Check for motivational context
        found_motivational = any(word in text_lower for word in self.motivational_keywords)
        found_compliment = any(word in text_lower for word in self.compliment_keywords)
        has_positive_context = found_motivational or found_compliment

        for severity, keywords in self.toxic_keywords.items():
            for keyword in keywords:
                pattern = make_fuzzy_pattern(keyword)
                # Check against the cleaned text
                if re.search(pattern, temp_text):
                    # If it's a "medium" word like 'shit' or 'fuck' and we have positive context,
                    # we demote it to 'low' or ignore it if it doesn't look like an attack
                    is_soft_profanity = keyword in ['fuck', 'shit', 'fucking']
                    
                    if is_soft_profanity and has_positive_context:
                        # Only demote if it's not a direct 'you are' attack
                        if not re.search(r'\byou\s+.*' + keyword, text_lower):
                            severity_scores['low'] += 1
                            continue
                    
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
        # If we have positive context, we are much more lenient on soft profanity
        if has_positive_context and severity_scores['high'] == 0:
            toxicity_score *= 0.5

        toxicity_score = min(toxicity_score / 1.5, 1.0)
        
        # Threshold for is_toxic: harder to reach if motivational
        threshold = 0.4
        if has_positive_context:
            threshold = 0.6
            
        is_toxic = toxicity_score >= threshold or severity_scores['high'] > 0

        log_entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Text: '{text_lower}' | is_toxic: {is_toxic} | score: {toxicity_score:.2f} | words: {detected_words} | motivational: {has_positive_context}\n"
        try:
            with open('moderation_debug.log', 'a') as f:
                f.write(log_entry)
        except:
            pass
        print(f"   [DETECTION] Text: '{text_lower}'")
        print(f"   [DETECTION] is_toxic: {is_toxic}, score: {toxicity_score}, words: {detected_words}, motivational: {has_positive_context}")

        return {
            'is_toxic': is_toxic,
            'toxicity_score': toxicity_score,
            'categories': severity_scores,
            'detected_words': detected_words,
            'has_positive_context': has_positive_context,
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


def mask_text(text: str) -> str:
    """Masks profane words keeping the first letter and hashing the rest"""
    try:
        from better_profanity import profanity
        # Use better-profanity to find what to mask
        # It has a censor method, but we want a custom format
        words = text.split()
        masked_words = []
        
        for word in words:
            # Check if word contains profanity
            if profanity.contains_profanity(word):
                # Mask it: keep first alphanumeric char, '*' for rest of alphanumeric chars
                # We handle punctuation around the word
                match = re.search(r'^(\W*)([a-zA-Z0-9])(.*)$', word)
                if match:
                    prefix, first, rest = match.groups()
                    masked_rest = re.sub(r'[a-zA-Z0-9]', '*', rest)
                    masked_words.append(prefix + first + masked_rest)
                else:
                    # Fallback for words that might not match the regex but are profane
                    masked_words.append(word[0] + '*' * (len(word) - 1))
            else:
                masked_words.append(word)
        return ' '.join(masked_words)
    except Exception as e:
        print(f"Masking error: {e}")
        return text


class SightengineDetector:
    """
    Uses Sightengine Text Moderation API
    """
    def __init__(self):
        try:
            from django.conf import settings
            self.api_user = getattr(settings, 'SIGHTENGINE_API_USER', os.getenv('SIGHTENGINE_API_USER'))
            self.api_secret = getattr(settings, 'SIGHTENGINE_API_SECRET', os.getenv('SIGHTENGINE_API_SECRET'))
        except:
            self.api_user = os.getenv('SIGHTENGINE_API_USER')
            self.api_secret = os.getenv('SIGHTENGINE_API_SECRET')
            
        self.api_url = "https://api.sightengine.com/1.0/check.json"
        
        if not self.api_user or not self.api_secret:
            print("[!] Sightengine credentials missing!")

    async def detect_async(self, text: str) -> Dict:
        if not self.api_user or not self.api_secret:
            print("[!] Sightengine credentials missing, falling back to keywords")
            return KeywordDetector().detect(text)

        try:
            params = {
                'text': text,
                'lang': 'en',
                'mode': 'rules,ml',
                'api_user': self.api_user,
                'api_secret': self.api_secret,
            }

            print(f"\n[?] Calling Sightengine API for: '{text}'")
            async with httpx.AsyncClient(verify=False) as client: # Bypass SSL issues in local dev
                response = await client.get(self.api_url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"   [!] Sightengine error: {response.status_code}")
                return KeywordDetector().detect(text)

            data = response.json()
            
            # Extract profanity matches
            profanity_matches = data.get('profanity', {}).get('matches', [])
            is_toxic = len(profanity_matches) > 0
            
            # Check ML scores if rules didn't catch it
            categories = {}
            if 'class' in data:
                categories = data['class'] # Sightengine uses 'class' for ML scores
                # Flag if any score is high
                if any(score > 0.5 for score in categories.values()):
                    is_toxic = True
            
            toxicity_score = max(categories.values()) if categories else (1.0 if is_toxic else 0.0)

            return {
                'is_toxic': is_toxic,
                'toxicity_score': toxicity_score,
                'categories': categories,
                'detected_words': [m.get('word') for m in profanity_matches],
                'method': 'sightengine'
            }
        except Exception as e:
            print(f"   [!] Sightengine Async error: {e}")
            return KeywordDetector().detect(text)

    def detect(self, text: str) -> Dict:
        # Simple sync wrapper
        if not self.api_user or not self.api_secret:
            return KeywordDetector().detect(text)
            
        try:
            params = {
                'text': text,
                'lang': 'en',
                'mode': 'rules,ml',
                'api_user': self.api_user,
                'api_secret': self.api_secret,
            }
            response = requests.get(self.api_url, params=params, timeout=10)
            data = response.json()
            profanity_matches = data.get('profanity', {}).get('matches', [])
            is_toxic = len(profanity_matches) > 0 or any(score > 0.5 for score in data.get('class', {}).values())
            return {
                'is_toxic': is_toxic,
                'toxicity_score': 0.8 if is_toxic else 0.0,
                'method': 'sightengine'
            }
        except:
            return KeywordDetector().detect(text)


# -------------------------------

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
