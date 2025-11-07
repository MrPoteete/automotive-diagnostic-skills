#!/usr/bin/env python3
"""
Simplified scraper runner - uses fewer tags to ensure results.

The default scraper combines 18 tags which may be too restrictive.
This version uses a simpler approach that's guaranteed to return results.
"""

from datetime import datetime, timedelta
from src.scrapers.stackexchange_scraper import StackExchangeScraper

def main():
    """
    Run scraper with optimized tag selection.
    """
    scraper = StackExchangeScraper()

    print("="*70)
    print("SIMPLIFIED STACK EXCHANGE SCRAPER")
    print("="*70)
    print("\nStrategy: Scraping with BROADER tags for better coverage")
    print("Using: diagnostics, troubleshooting, obd-ii")
    print("\nThis ensures we get actual results instead of 0 questions.")
    print("="*70 + "\n")

    # Use just a few highly relevant tags instead of 18
    # This dramatically increases the chance of finding questions
    simplified_tags = [
        'diagnostics',
        'troubleshooting',
        'obd-ii',
    ]

    # Scrape last 10 years with simplified tags
    from_date = datetime.now() - timedelta(days=365 * 10)

    questions = scraper.scrape_full_threads(
        tags=simplified_tags,  # Much simpler tag list
        from_date=from_date,
        to_date=None,
        max_questions=1000,  # Start with 1000 to test
    )

    if questions:
        output_path = scraper.save_data(questions)

        # Print summary
        print("\n" + "="*70)
        print("SCRAPE COMPLETE!")
        print("="*70)
        print(f"Questions scraped: {len(questions)}")
        print(f"Total answers: {sum(len(q.answers) for q in questions)}")
        print(f"Total comments: {sum(len(q.comments) for q in questions)}")
        print(f"API requests: {scraper.requests_made}")
        print(f"Quota remaining: {scraper.quota_remaining}/{scraper.quota_max}")
        print(f"\nOutput file: {output_path}")
        print("="*70)

        # Show manufacturer breakdown
        print("\nQuick analysis - Manufacturer mentions:")
        manufacturers = {'ford': 0, 'gm': 0, 'chevrolet': 0, 'ram': 0, 'dodge': 0}
        for q in questions:
            text = (q.title + ' ' + q.body).lower()
            for make in manufacturers.keys():
                if make in text:
                    manufacturers[make] += 1

        for make, count in sorted(manufacturers.items(), key=lambda x: x[1], reverse=True):
            print(f"  {make.capitalize():15s} {count:4d} questions")

        print("\n✅ SUCCESS! Now run: python src/scrapers/analyze_forum_data.py")
    else:
        print("\n❌ FAILED: No questions scraped")
        print("\nTroubleshooting:")
        print("1. Check internet connection")
        print("2. Verify Stack Exchange API is accessible")
        print("3. Try running: python test_tags.py")

if __name__ == '__main__':
    main()
