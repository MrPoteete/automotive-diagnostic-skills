#!/usr/bin/env python3
"""
Backfill historical data systematically.

Gets ALL questions from the last 10 years by scraping in yearly batches.
Respects API quota and can resume across multiple days.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from src.scrapers.stackexchange_scraper import StackExchangeScraper


def backfill_by_year(start_year: int = 2015, end_year: int = 2025):
    """
    Backfill data year by year.

    Args:
        start_year: Starting year (default: 2015 for 10 years ago)
        end_year: Ending year (default: 2025 for current year)
    """
    scraper = StackExchangeScraper()
    data_dir = Path("data/raw_imports/forum_data")
    data_dir.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("HISTORICAL BACKFILL - YEAR BY YEAR")
    print("="*70)
    print(f"Date range: {start_year} to {end_year}")
    print(f"Strategy: Scrape one year at a time to manage quota")
    print("="*70 + "\n")

    total_questions = 0
    years_completed = 0

    for year in range(start_year, end_year + 1):
        # Check if already scraped
        existing_file = data_dir / f"stackexchange_mechanics_{year}.json"
        if existing_file.exists():
            print(f"⏭️  {year}: Already scraped, skipping...")
            with open(existing_file, 'r') as f:
                data = json.load(f)
                total_questions += len(data.get('questions', []))
            continue

        print(f"\n📅 SCRAPING YEAR: {year}")
        print("-" * 70)

        # Define year boundaries
        from_date = datetime(year, 1, 1)
        to_date = datetime(year, 12, 31, 23, 59, 59)

        # Check if we have enough quota
        if scraper.quota_remaining and scraper.quota_remaining < 50:
            print(f"\n⚠️  Low quota ({scraper.quota_remaining} remaining)")
            print(f"Stopping at year {year}. Resume tomorrow with:")
            print(f"  python backfill_historical.py --start-year {year}")
            break

        # Scrape this year
        questions = scraper.scrape_full_threads(
            tags=None,
            from_date=from_date,
            to_date=to_date,
            max_questions=10000,  # High limit for complete year
        )

        if questions:
            # Save with year-specific filename
            filename = f"stackexchange_mechanics_{year}.json"
            output_path = scraper.save_data(questions, filename)

            print(f"✅ {year}: Scraped {len(questions)} questions")
            print(f"   Saved to: {filename}")
            print(f"   Quota remaining: {scraper.quota_remaining}/{scraper.quota_max}")

            total_questions += len(questions)
            years_completed += 1
        else:
            print(f"⚠️  {year}: No questions found")

    # Summary
    print("\n" + "="*70)
    print("BACKFILL SUMMARY")
    print("="*70)
    print(f"Years completed: {years_completed}/{end_year - start_year + 1}")
    print(f"Total questions: {total_questions}")
    print(f"API requests made: {scraper.requests_made}")
    print(f"Quota remaining: {scraper.quota_remaining}/{scraper.quota_max}")
    print("="*70)

    if years_completed < (end_year - start_year + 1):
        print("\n⚠️  Backfill incomplete - resume tomorrow!")
    else:
        print("\n✅ Backfill complete! Run deduplicate_data.py to merge.")


def backfill_by_month(year: int, month: int):
    """
    Backfill a specific month (for gap filling).

    Args:
        year: Year to backfill
        month: Month to backfill (1-12)
    """
    scraper = StackExchangeScraper()
    data_dir = Path("data/raw_imports/forum_data")
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📅 SCRAPING: {year}-{month:02d}")

    # Month boundaries
    from_date = datetime(year, month, 1)
    if month == 12:
        to_date = datetime(year, 12, 31, 23, 59, 59)
    else:
        to_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

    questions = scraper.scrape_full_threads(
        tags=None,
        from_date=from_date,
        to_date=to_date,
        max_questions=10000,
    )

    if questions:
        filename = f"stackexchange_mechanics_{year}_{month:02d}.json"
        output_path = scraper.save_data(questions, filename)
        print(f"✅ Scraped {len(questions)} questions for {year}-{month:02d}")
        print(f"   Saved to: {filename}")
    else:
        print(f"⚠️  No questions found for {year}-{month:02d}")


if __name__ == '__main__':
    import sys

    # Parse command line args
    if len(sys.argv) > 1 and sys.argv[1] == '--start-year':
        start_year = int(sys.argv[2])
        backfill_by_year(start_year=start_year)
    else:
        # Default: backfill last 10 years
        backfill_by_year(start_year=2015, end_year=2025)
