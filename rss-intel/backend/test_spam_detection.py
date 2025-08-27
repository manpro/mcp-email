#!/usr/bin/env python3
"""
Test script for spam detection system
Validates spam detection with sample content
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.intelligence.spam_detector import AdvancedSpamDetector

def test_spam_detection():
    """Test spam detection with various content types"""
    print("🔍 Testing RSS Intelligence Spam Detection System")
    print("=" * 60)
    
    detector = AdvancedSpamDetector()
    
    # Test cases: (title, content, expected_result)
    test_cases = [
        {
            'title': 'Join Our Exclusive Webinar - Register Now!',
            'content': 'Don\'t miss this limited time opportunity! Register now for our exclusive webinar featuring industry leaders. Click here to sign up today and save your seat. This offer won\'t last long - act now!',
            'description': 'Promotional webinar spam',
            'expected_spam': True
        },
        {
            'title': 'AI Breakthrough in Machine Learning Research',
            'content': 'Researchers at MIT have developed a new neural network architecture that significantly improves natural language processing capabilities. The study, published in Nature, demonstrates a 20% improvement in accuracy over previous methods. The research team used a novel approach combining transformer models with reinforcement learning.',
            'description': 'Legitimate news article',
            'expected_spam': False
        },
        {
            'title': 'SHOCKING: You Won\'t Believe What Happened Next!',
            'content': 'This will blow your mind! Click here to see the amazing trick that doctors hate. You won\'t believe the results! This simple method will change everything.',
            'description': 'Clickbait spam',
            'expected_spam': True
        },
        {
            'title': 'New Payment Processing API Released',
            'content': 'A new API for payment processing has been released. Read more for details.',
            'description': 'Thin content',
            'expected_spam': True  # Should be flagged for thin content
        },
        {
            'title': 'Fintech Startup Raises $50M in Series B Funding',
            'content': 'Stockholm-based payments company Klarna announced today that it has raised $50 million in Series B funding led by Sequoia Capital. The funding will be used to expand operations in the European market and develop new payment technologies. CEO Sebastian Siemiatkowski said the company plans to double its workforce over the next year.',
            'description': 'Legitimate business news',
            'expected_spam': False
        },
        {
            'title': 'Revolutionary AI Tool Transforms Business Operations',
            'content': 'Our cutting-edge AI solution will transform your business operations and maximize ROI. Industry leaders trust our award-winning platform. Download our free whitepaper and request a demo today! Limited time offer - contact us now to learn more about our enterprise solution.',
            'description': 'Business/product promotion',
            'expected_spam': True
        }
    ]
    
    results = []
    correct_predictions = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['description']}")
        print(f"Title: {test_case['title']}")
        print(f"Content: {test_case['content'][:100]}...")
        
        # Run spam detection
        result = detector.detect_spam(
            title=test_case['title'],
            content=test_case['content'],
            source='test-source.com'
        )
        
        # Evaluate results
        predicted_spam = result.is_spam
        expected_spam = test_case['expected_spam']
        correct = predicted_spam == expected_spam
        
        if correct:
            correct_predictions += 1
            status = "✅ CORRECT"
        else:
            status = "❌ INCORRECT"
        
        print(f"Expected: {'SPAM' if expected_spam else 'NOT SPAM'}")
        print(f"Predicted: {'SPAM' if predicted_spam else 'NOT SPAM'} ({result.spam_probability:.2%} probability)")
        print(f"Content Score: {result.content_score:.2%}")
        print(f"Title Coherence: {result.title_content_coherence:.2%}")
        print(f"Recommendation: {result.recommendation}")
        print(f"Status: {status}")
        
        # Show detected signals
        if result.spam_signals:
            print("Detected Signals:")
            for signal in result.spam_signals[:3]:  # Show top 3 signals
                print(f"  - {signal.type}: {signal.confidence:.2%} ({signal.reason})")
        
        results.append({
            'test_case': test_case['description'],
            'correct': correct,
            'predicted_spam': predicted_spam,
            'expected_spam': expected_spam,
            'spam_probability': result.spam_probability,
            'content_score': result.content_score,
            'signals': len(result.spam_signals)
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 SPAM DETECTION TEST RESULTS")
    print("=" * 60)
    
    accuracy = correct_predictions / len(test_cases)
    print(f"Accuracy: {correct_predictions}/{len(test_cases)} ({accuracy:.1%})")
    
    # Detailed breakdown
    print("\nDetailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result['correct'] else "❌"
        print(f"{status} Test {i}: {result['test_case']} - "
              f"Spam: {result['spam_probability']:.1%}, "
              f"Quality: {result['content_score']:.1%}, "
              f"Signals: {result['signals']}")
    
    # Performance summary
    spam_cases = [r for r in results if r['expected_spam']]
    non_spam_cases = [r for r in results if not r['expected_spam']]
    
    if spam_cases:
        spam_accuracy = sum(1 for r in spam_cases if r['correct']) / len(spam_cases)
        print(f"\nSpam Detection Rate: {spam_accuracy:.1%} ({sum(1 for r in spam_cases if r['correct'])}/{len(spam_cases)})")
    
    if non_spam_cases:
        non_spam_accuracy = sum(1 for r in non_spam_cases if r['correct']) / len(non_spam_cases)
        print(f"False Positive Rate: {1-non_spam_accuracy:.1%} ({sum(1 for r in non_spam_cases if not r['correct'])}/{len(non_spam_cases)})")
    
    # System health check
    print(f"\n🔧 SYSTEM STATUS:")
    print(f"Spam Detector: ✅ Active")
    print(f"Configuration: ✅ Loaded")
    print(f"NLP Models: {'✅ Available' if detector.nlp else '⚠️  Basic mode'}")
    
    if accuracy >= 0.8:
        print(f"\n🎉 OVERALL RESULT: EXCELLENT (Accuracy: {accuracy:.1%})")
        return True
    elif accuracy >= 0.6:
        print(f"\n⚠️  OVERALL RESULT: GOOD (Accuracy: {accuracy:.1%}) - Consider tuning")
        return False
    else:
        print(f"\n❌ OVERALL RESULT: NEEDS IMPROVEMENT (Accuracy: {accuracy:.1%})")
        return False

if __name__ == "__main__":
    success = test_spam_detection()
    sys.exit(0 if success else 1)