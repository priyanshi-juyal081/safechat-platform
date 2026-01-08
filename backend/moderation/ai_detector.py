import re
import os
import time
from typing import Dict, List

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
        if self.method == 'keyword':
            return self.keyword_detector.detect(text)
        elif self.method == 'transformer':
            return self.model_detector.detect(text)
        elif self.method == 'api':
            return self.api_detector.detect(text)
        else:
            return self.keyword_detector.detect(text)


# -------------------------------
# Keyword Fallback Detector
# -------------------------------

class KeywordDetector:
    """Fast keyword-based toxicity detection"""

    def __init__(self):
        self.toxic_keywords = {
            'high': [
                'hate', 'kill', 'die', 'death', 'nazi', 'terrorist',
                'rape', 'murder', 'violence', 'abuse', 'attack'
            ],
            'medium': [
                'stupid', 'idiot', 'dumb', 'moron', 'loser', 'pathetic',
                'trash', 'garbage', 'worthless', 'useless', 'disgusting',
                'fuck', 'shit', 'bitch', 'asshole', 'fucking'
            ],
            'low': [
                'shut up', 'annoying', 'boring', 'lame',
                'bad', 'terrible', 'awful', 'horrible'
            ]
        }

        self.harassment_patterns = [
            r'\bkys\b',
            r'go die',
            r'\bfuck(?:ing)?\b',
            r'you\s+suck',
            r'kill(?:\s+yourself)?',
        ]

    def detect(self, text: str) -> Dict:
        text_lower = text.lower()
        detected_words = []
        severity_scores = {'high': 0, 'medium': 0, 'low': 0}

        # Helper: allow non-word separators between characters to match obfuscated words
        def make_fuzzy_pattern(word: str) -> str:
            # e.g. 'fuck' -> r'\bf\W*u\W*c\W*k\b'
            chars = [re.escape(c) for c in word]
            return r"\b" + r"\W*".join(chars) + r"\b"

        for severity, keywords in self.toxic_keywords.items():
            for keyword in keywords:
                pattern = make_fuzzy_pattern(keyword)
                if keyword in text_lower or re.search(pattern, text_lower):
                    detected_words.append(keyword)
                    severity_scores[severity] += 1

        for pattern in self.harassment_patterns:
            if re.search(pattern, text_lower):
                detected_words.append('harassment_pattern')
                severity_scores['high'] += 1

        toxicity_score = (
            severity_scores['high'] * 1.0 +
            severity_scores['medium'] * 0.6 +
            severity_scores['low'] * 0.3
        )
        toxicity_score = min(toxicity_score / 3.0, 1.0)
        is_toxic = toxicity_score > 0.3

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
    Uses OpenAI Moderation API
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")

    def detect(self, text: str) -> Dict:
        if not self.api_key:
            print("OPENAI_API_KEY not set, falling back to keywords")
            return KeywordDetector().detect(text)

        return self._openai_moderation(text)

    def _openai_moderation(self, text: str) -> Dict:
        max_attempts = 3
        backoff = 1

        for attempt in range(1, max_attempts + 1):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)

                response = client.moderations.create(
                    model="omni-moderation-latest",
                    input=text
                )

                result = response.results[0]
                scores = result.category_scores
                toxicity_score = max(scores.values()) if scores else 0.0

                # If OpenAI flags the content, return that result
                if result.flagged:
                    return {
                        'is_toxic': True,
                        'toxicity_score': toxicity_score,
                        'categories': scores,
                        'detected_words': [],
                        'method': 'openai_moderation'
                    }

                # Fallback: if OpenAI did not flag, still run keyword detector as a safety net
                keyword_result = KeywordDetector().detect(text)
                if keyword_result.get('is_toxic'):
                    merged = keyword_result.copy()
                    merged.update({
                        'method': 'openai_moderation+keyword',
                        'categories': {**(scores or {}), **keyword_result.get('categories', {})}
                    })
                    return merged

                # Neither OpenAI nor keyword detected toxicity
                return {
                    'is_toxic': False,
                    'toxicity_score': toxicity_score,
                    'categories': scores,
                    'detected_words': [],
                    'method': 'openai_moderation'
                }

            except Exception as e:
                msg = str(e)
                print("OpenAI moderation error:", e)

                # If rate limited, retry with exponential backoff
                if attempt < max_attempts and ("too many requests" in msg.lower() or "429" in msg):
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                # On final failure or non-retriable error, fall back to keyword detector
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


def comprehensive_check(text: str) -> Dict:
    detector = ToxicityDetector(method='api')
    result = detector.analyze(text)

    return {
        **result,
        'is_spam': detect_spam(text),
        'has_repeated_chars': detect_repeated_characters(text),
        'is_shouting': detect_all_caps(text),
    }


# -------------------------------
# Test
# -------------------------------

if __name__ == '__main__':
    detector = ToxicityDetector(method='api')

    tests = [
        "Hello everyone!",
        "you are a f***ing idiot",
        "go kill yourself",
        "THIS IS SO ANNOYING"
    ]

    for t in tests:
        print("\nText:", t)
        print(detector.analyze(t))
