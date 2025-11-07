#!/usr/bin/env python3
"""
Debug why documents aren't being created.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from rag.process_forum_data import ForumDataProcessor
from rag import config

def debug_processing():
    """Debug the processing pipeline."""
    processor = ForumDataProcessor()

    # Load data
    questions = processor.load_forum_data()
    print(f"\n✅ Loaded {len(questions)} questions")

    # Check high quality
    high_quality = [q for q in questions if processor.is_high_quality(q)]
    print(f"✅ {len(high_quality)} pass quality filters\n")

    if not high_quality:
        print("❌ No high-quality questions found!")
        return

    # Debug first few
    print("🔍 Debugging first 5 high-quality questions:\n")
    print("="*70)

    for i, question in enumerate(high_quality[:5], 1):
        print(f"\n📝 Question {i}: {question.get('title', 'N/A')[:60]}...")
        print(f"   Question ID: {question.get('question_id')}")
        print(f"   Question Score: {question.get('score', 0)}")
        print(f"   Has accepted answer: {question.get('accepted_answer_id') is not None}")
        print(f"   Number of answers: {len(question.get('answers', []))}")

        # Get best answer
        answer = processor.get_best_answer(question)
        if not answer:
            print(f"   ❌ FAIL: get_best_answer() returned None")
            print(f"      Answers: {question.get('answers', [])}")
            continue

        print(f"   ✅ Best answer found")
        print(f"   Answer Score: {answer.get('score', 0)}")
        print(f"   Answer ID: {answer.get('answer_id')}")

        # Check answer score threshold
        if answer.get('score', 0) < config.MIN_ANSWER_SCORE:
            print(f"   ❌ FAIL: Answer score {answer.get('score', 0)} < {config.MIN_ANSWER_SCORE} (MIN_ANSWER_SCORE)")
            continue

        # Check answer length
        answer_text = processor.clean_html(answer.get('body', ''))
        print(f"   Answer length: {len(answer_text)} chars")

        if len(answer_text) < config.MIN_ANSWER_LENGTH:
            print(f"   ❌ FAIL: Answer too short ({len(answer_text)} < {config.MIN_ANSWER_LENGTH})")
            continue

        print(f"   ✅ Would create document successfully!")

    print("\n" + "="*70)

    # Count failure reasons
    print("\n📊 FAILURE ANALYSIS (all high-quality questions):\n")

    no_answer = 0
    low_answer_score = 0
    short_answer = 0
    success = 0

    for question in high_quality:
        answer = processor.get_best_answer(question)
        if not answer:
            no_answer += 1
            continue

        if answer.get('score', 0) < config.MIN_ANSWER_SCORE:
            low_answer_score += 1
            continue

        answer_text = processor.clean_html(answer.get('body', ''))
        if len(answer_text) < config.MIN_ANSWER_LENGTH:
            short_answer += 1
            continue

        success += 1

    total = len(high_quality)
    print(f"Total high-quality questions: {total}")
    print(f"  ✅ Would create documents: {success} ({success/total*100:.1f}%)")
    print(f"  ❌ No answer found: {no_answer} ({no_answer/total*100:.1f}%)")
    print(f"  ❌ Answer score < {config.MIN_ANSWER_SCORE}: {low_answer_score} ({low_answer_score/total*100:.1f}%)")
    print(f"  ❌ Answer too short (< {config.MIN_ANSWER_LENGTH} chars): {short_answer} ({short_answer/total*100:.1f}%)")

    print("\n💡 RECOMMENDATIONS:")
    if low_answer_score > success:
        print(f"   Most failures due to answer score threshold ({config.MIN_ANSWER_SCORE})")
        print(f"   Consider lowering MIN_ANSWER_SCORE in src/rag/config.py")
        print(f"   Suggested value: 1 or 0 (accept all scored answers)")

    if short_answer > success:
        print(f"   Many answers too short (< {config.MIN_ANSWER_LENGTH} chars)")
        print(f"   Consider lowering MIN_ANSWER_LENGTH in src/rag/config.py")
        print(f"   Suggested value: 50")

if __name__ == '__main__':
    debug_processing()
