"""
AI Toxicity Detection Module
FILE: backend/moderation/ai_detector.py

This module provides toxicity detection using multiple approaches:
1. Keyword-based detection (fast, simple)
2. Transformer-based model (accurate, requires GPU/CPU)
3. External API integration (optional)
"""

import re
from typing import Dict, List

class ToxicityDetector:
    """Main toxicity detection class"""
    
    def __init__(self, method='keyword'):
        """
        Initialize detector with specified method
        
        Args:
            method: 'keyword', 'transformer', or 'api'
        """
        self.method = method
        self.keyword_detector = KeywordDetector()
        
        if method == 'transformer':
            self.model_detector = TransformerDetector()
        elif method == 'api':
            self.api_detector = APIDetector()
    
    def analyze(self, text: str) -> Dict:
        """
        Analyze text for toxicity
        
        Returns:
            {
                'is_toxic': bool,
                'toxicity_score': float (0-1),
                'categories': dict,
                'detected_words': list
            }
        """
        if self.method == 'keyword':
            return self.keyword_detector.detect(text)
        elif self.method == 'transformer':
            return self.model_detector.detect(text)
        elif self.method == 'api':
            return self.api_detector.detect(text)
        else:
            return self.keyword_detector.detect(text)


class KeywordDetector:
    """Fast keyword-based toxicity detection"""
    
    def __init__(self):
        # Toxic keywords categorized by severity
        self.toxic_keywords = {
            'high': [
                'hate', 'kill', 'die', 'death', 'nazi', 'terrorist',
                'rape', 'murder', 'violence', 'abuse', 'attack'
            ],
            'medium': [
                'stupid', 'idiot', 'dumb', 'moron', 'loser', 'pathetic',
                'trash', 'garbage', 'worthless', 'useless', 'disgusting'
            ],
            'low': [
                'shut up', 'shut', 'annoying', 'boring', 'lame', 'weak',
                'bad', 'terrible', 'awful', 'horrible'
            ]
        }
        
        # Harassment patterns
        self.harassment_patterns = [
            r'kys',  # kill yourself
            r'go die',
            r'f+u+c*k+ *y+o+u+',
            r'you+ *suck',
            r'kill+ *yourself',
        ]
    
    def detect(self, text: str) -> Dict:
        """Detect toxicity using keywords"""
        text_lower = text.lower()
        
        detected_words = []
        severity_scores = {'high': 0, 'medium': 0, 'low': 0}
        
        # Check keywords
        for severity, keywords in self.toxic_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected_words.append(keyword)
                    severity_scores[severity] += 1
        
        # Check harassment patterns
        for pattern in self.harassment_patterns:
            if re.search(pattern, text_lower):
                detected_words.append('harassment_pattern')
                severity_scores['high'] += 1
        
        # Calculate overall toxicity score
        toxicity_score = (
            severity_scores['high'] * 1.0 +
            severity_scores['medium'] * 0.6 +
            severity_scores['low'] * 0.3
        )
        
        # Normalize to 0-1 range
        toxicity_score = min(toxicity_score / 3.0, 1.0)
        
        is_toxic = toxicity_score > 0.3
        
        return {
            'is_toxic': is_toxic,
            'toxicity_score': toxicity_score,
            'categories': {
                'toxicity': toxicity_score,
                'severe_toxicity': severity_scores['high'] > 0,
                'obscene': False,
                'threat': severity_scores['high'] > 0,
                'insult': severity_scores['medium'] > 0,
                'identity_attack': False,
            },
            'detected_words': detected_words,
            'method': 'keyword'
        }


class TransformerDetector:
    """
    Advanced transformer-based toxicity detection
    Uses pre-trained models for more accurate detection
    """
    
    def __init__(self):
        try:
            from transformers import pipeline
            # Load a toxicity detection model
            # Options:
            # - "unitary/toxic-bert"
            # - "martin-ha/toxic-comment-model"
            # - "facebook/roberta-hate-speech-dynabench-r4-target"
            
            self.classifier = pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                top_k=None
            )
        except Exception as e:
            print(f"Error loading transformer model: {e}")
            print("Falling back to keyword detection")
            self.classifier = None
    
    def detect(self, text: str) -> Dict:
        """Detect toxicity using transformer model"""
        if not self.classifier:
            # Fallback to keyword detection
            return KeywordDetector().detect(text)
        
        try:
            results = self.classifier(text)[0]
            
            # Parse results
            toxicity_scores = {}
            for result in results:
                label = result['label'].lower()
                score = result['score']
                toxicity_scores[label] = score
            
            # Get overall toxicity score
            toxicity_score = toxicity_scores.get('toxic', 0.0)
            is_toxic = toxicity_score > 0.5
            
            return {
                'is_toxic': is_toxic,
                'toxicity_score': toxicity_score,
                'categories': toxicity_scores,
                'detected_words': [],
                'method': 'transformer'
            }
        except Exception as e:
            print(f"Error in transformer detection: {e}")
            return KeywordDetector().detect(text)


class APIDetector:
    """
    Use external API for toxicity detection
    Example: Google Perspective API, OpenAI Moderation API
    """
    
    def __init__(self):
        self.api_key = None  # Set your API key here
        # You can use environment variables:
        # import os
        # self.api_key = os.getenv('PERSPECTIVE_API_KEY')
    
    def detect(self, text: str) -> Dict:
        """Detect toxicity using external API"""
        
        # Example: Google Perspective API
        if self.api_key:
            return self._perspective_api(text)
        
        # Fallback to keyword detection
        return KeywordDetector().detect(text)
    
    def _perspective_api(self, text: str) -> Dict:
        """
        Use Google Perspective API for toxicity detection
        Documentation: https://developers.perspectiveapi.com/
        """
        import requests
        
        url = f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={self.api_key}"
        
        data = {
            'comment': {'text': text},
            'languages': ['en'],
            'requestedAttributes': {
                'TOXICITY': {},
                'SEVERE_TOXICITY': {},
                'IDENTITY_ATTACK': {},
                'INSULT': {},
                'PROFANITY': {},
                'THREAT': {}
            }
        }
        
        try:
            response = requests.post(url, json=data)
            result = response.json()
            
            scores = {}
            for attr, data in result['attributeScores'].items():
                scores[attr.lower()] = data['summaryScore']['value']
            
            toxicity_score = scores.get('toxicity', 0.0)
            is_toxic = toxicity_score > 0.7
            
            return {
                'is_toxic': is_toxic,
                'toxicity_score': toxicity_score,
                'categories': scores,
                'detected_words': [],
                'method': 'perspective_api'
            }
        except Exception as e:
            print(f"Perspective API error: {e}")
            return KeywordDetector().detect(text)
    
    def _openai_moderation(self, text: str) -> Dict:
        """
        Use OpenAI Moderation API
        Documentation: https://platform.openai.com/docs/guides/moderation
        """
        import openai
        
        try:
            response = openai.Moderation.create(input=text)
            result = response['results'][0]
            
            categories = result['categories']
            category_scores = result['category_scores']
            
            # Get highest score
            toxicity_score = max(category_scores.values())
            is_toxic = result['flagged']
            
            return {
                'is_toxic': is_toxic,
                'toxicity_score': toxicity_score,
                'categories': category_scores,
                'detected_words': [],
                'method': 'openai_moderation'
            }
        except Exception as e:
            print(f"OpenAI Moderation error: {e}")
            return KeywordDetector().detect(text)


# Utility functions for advanced detection
def detect_spam(text: str) -> bool:
    """Detect spam patterns"""
    spam_indicators = [
        len(text) > 500,  # Very long messages
        text.count('http') > 3,  # Multiple links
        len(set(text.lower().split())) / len(text.split()) < 0.3,  # Low word diversity
    ]
    return sum(spam_indicators) >= 2


def detect_repeated_characters(text: str) -> bool:
    """Detect excessive repeated characters (like 'aaaaaaa')"""
    pattern = r'(.)\1{5,}'
    return bool(re.search(pattern, text))


def detect_all_caps(text: str) -> bool:
    """Detect messages in ALL CAPS (shouting)"""
    if len(text) < 10:
        return False
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return False
    caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
    return caps_ratio > 0.7


def comprehensive_check(text: str) -> Dict:
    """Perform comprehensive toxicity and quality checks"""
    detector = ToxicityDetector(method='keyword')
    toxicity_result = detector.analyze(text)
    
    return {
        **toxicity_result,
        'is_spam': detect_spam(text),
        'has_repeated_chars': detect_repeated_characters(text),
        'is_shouting': detect_all_caps(text),
    }


# Example usage
if __name__ == '__main__':
    detector = ToxicityDetector(method='keyword')
    
    test_messages = [
        "Hello everyone! How are you?",
        "You are so stupid and worthless",
        "I hate this person, they should die",
        "This is amazing! Great work!",
        "STOP SPAMMING YOU IDIOT"
    ]
    
    print("Toxicity Detection Results:")
    print("=" * 50)
    
    for msg in test_messages:
        result = detector.analyze(msg)
        print(f"\nMessage: {msg}")
        print(f"Toxic: {result['is_toxic']}")
        print(f"Score: {result['toxicity_score']:.2f}")
        print(f"Detected: {result['detected_words']}")
        print("-" * 50)