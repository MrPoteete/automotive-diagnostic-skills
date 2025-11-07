#!/usr/bin/env python3
"""
Incremental scraper - only gets NEW questions since last run.

Tracks the last scrape date and only fetches questions created after that.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from src.scrapers.stackexchange_scraper import StackExchangeScraper


def get_last_scrape_date(data_dir: Path) -> datetime:
    """
    Find the most recent scrape date from existing data files.

    Returns:
        datetime of last scrape, or 10 years ago if no previous scrapes
    """
    json_files = list(data_dir.glob("stackexchange_*.json"))

    if not json_files:
        # No previous scrapes - go back 10 years
        return datetime.now() - timedelta(days=365 * 10)

    # Find most recent file
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)

    # Read the scrape date from metadata
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        scrape_date_str = data.get('metadata', {}).get('scrape_date')

        if scrape_date_str:
            # Parse ISO format date
            return datetime.fromisoformat(scrape_date_str)
        else:
            # Fallback to file modification time
            return datetime.fromtimestamp(latest_file.stat().st_mtime)


def scrape_incremental(max_questions: int = 5000):
    """
    Scrape only NEW questions since last run.

    Args:
        max_questions: Maximum questions to fetch
    """
    data_dir = Path("data/raw_imports/forum_data")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Get last scrape date
    last_scrape = get_last_scrape_date(data_dir)

    print("="*70)
    print("INCREMENTAL STACK EXCHANGE SCRAPER")
    print("="*70)
    print(f"Last scrape: {last_scrape.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Fetching questions created AFTER this date...")
    print("="*70 + "\n")

    scraper = StackExchangeScraper()

    questions = scraper.scrape_full_threads(
        tags=None,  # No tags
        from_date=last_scrape,  # Only questions after last scrape
        to_date=None,
        max_questions=max_questions,
    )

    if questions:
        output_path = scraper.save_data(questions)

        print("\n" + "="*70)
        print("INCREMENTAL SCRAPE COMPLETE")
        print("="*70)
        print(f"NEW questions scraped: {len(questions)}")
        print(f"Date range: {last_scrape.strftime('%Y-%m-%d')} to now")
        print(f"Total answers: {sum(len(q.answers) for q in questions)}")
        print(f"Total comments: {sum(len(q.comments) for q in questions)}")
        print(f"Quota used: {scraper.requests_made} requests")
        print(f"Quota remaining: {scraper.quota_remaining}/{scraper.quota_max}")
        print(f"\nOutput: {output_path}")
        print("="*70)
    else:
        print("\n✅ No new questions since last scrape!")
        print("Everything is up to date.")


if __name__ == '__main__':
    scrape_incremental()
