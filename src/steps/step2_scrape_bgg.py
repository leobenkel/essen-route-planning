#!/usr/bin/env python3
"""
Step 2: Scrape BoardGameGeek for publisher information.

This script:
1. Loads target games from step 1
2. Scrapes BGG for publisher information
3. Uses caching to avoid re-scraping
4. Saves enriched games with publisher data
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))
from data_models import BoardGame
from bgg_scraper import BGGScraper


def load_target_games() -> tuple[List[BoardGame], dict]:
    """Load games from step 1 with metadata."""
    input_file = Path("data/output/target_games.json")
    if not input_file.exists():
        print("❌ Error: target_games.json not found!")
        print("   Please run step1_extract_games.py first")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both old format (direct list) and new format (with metadata)
    if isinstance(data, list):
        # Old format - just a list of games
        games = [BoardGame(**item) for item in data]
        metadata = {"include_expansions": True}  # Old format didn't filter expansions
    else:
        # New format - has metadata and games
        games = [BoardGame(**item) for item in data["games"]]
        metadata = data.get("metadata", {"include_expansions": False})  # New default
    
    return games, metadata


def main():
    """Scrape BGG for publisher information."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Scrape BGG for publisher information")
    parser.add_argument("--test", action="store_true", 
                       help="Test mode: scrape only first 5 games")
    parser.add_argument("--full", action="store_true",
                       help="Full mode: scrape all games (skip prompts)")
    parser.add_argument("--use-cache", action="store_true",
                       help="Use cached data if available (skip prompts)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("STEP 2: Scrape BoardGameGeek for Publishers")
    print("=" * 60)
    
    # Load target games
    print("\n📥 Loading target games...")
    games, metadata = load_target_games()
    print(f"✅ Loaded {len(games)} games")
    
    # Show expansion filtering info
    if "include_expansions" in metadata:
        expansions_status = "included" if metadata["include_expansions"] else "excluded"
        print(f"   Expansions: {expansions_status}")
    
    # Initialize scraper with human-like delays (1-3 seconds)
    print("\n🌐 Initializing BGG scraper...")
    print("   Rate limit: 1-3 seconds between requests (human-like)")
    print("   Cache enabled: data/cache/")
    scraper = BGGScraper(cache_dir="data/cache", rate_limit=(1.0, 3.0))
    
    # Check for existing progress and handle based on arguments
    cached_games = scraper.load_progress()
    
    if args.use_cache and cached_games:
        print(f"\n📂 Using cached data: {len(cached_games)} games")
        games = cached_games
    elif args.test:
        print(f"\n🧪 TEST MODE: Scraping first 5 games only")
        games = games[:5]
        games = scraper.enrich_games(games)
    elif args.full:
        print(f"\n🔄 FULL MODE: Scraping all {len(games)} games")
        # Check if we can resume from cached progress
        if cached_games and len(cached_games) < len(games):
            cached_ids = {g.object_id for g in cached_games}
            remaining_games = [g for g in games if g.object_id not in cached_ids]
            print(f"   Resuming from cached progress: {len(cached_games)} done, {len(remaining_games)} remaining")
            remaining_games = scraper.enrich_games(remaining_games)
            # Combine cached + new results
            games = cached_games + remaining_games
        else:
            games = scraper.enrich_games(games)
    else:
        # Interactive mode
        if cached_games:
            cached_ids = {g.object_id for g in cached_games}
            remaining_games = [g for g in games if g.object_id not in cached_ids]
            
            if len(remaining_games) == 0:
                print(f"\n✅ All games already scraped: {len(cached_games)} games")
                games = cached_games
            else:
                print(f"\n📂 Found cached progress: {len(cached_games)} games already scraped")
                print(f"   Remaining to scrape: {len(remaining_games)} games")
                try:
                    response = input("Continue from where left off? (y/n/test): ").lower()
                except (EOFError, KeyboardInterrupt):
                    print("\nNo input provided, continuing from where left off.")
                    response = 'y'
                
                if response == 'y':
                    print(f"\n🔄 Continuing scrape: {len(remaining_games)} remaining games")
                    remaining_games = scraper.enrich_games(remaining_games)
                    games = cached_games + remaining_games
                elif response == 'test':
                    # Test mode: scrape only first 5 games
                    print("\n🧪 TEST MODE: Scraping first 5 games only")
                    games = games[:5]
                    games = scraper.enrich_games(games)
                else:
                    print(f"\n🔄 Starting fresh scrape (this will take ~{len(games)*2//60} minutes)")
                    games = scraper.enrich_games(games)
        else:
            # Ask if user wants to test first
            print("\n⚠️  No cached data found")
            try:
                response = input("Run test with 5 games first? (y/n): ").lower()
            except (EOFError, KeyboardInterrupt):
                print("\nNo input provided, running test mode.")
                response = 'y'
            
            if response == 'y':
                print("\n🧪 TEST MODE: Scraping first 5 games")
                test_games = games[:5]
                test_games = scraper.enrich_games(test_games)
                
                # Show results
                print("\n📋 Test Results:")
                for game in test_games:
                    publishers = ", ".join(game.publishers) if game.publishers else "No publishers found"
                    print(f"  - {game.name}: {publishers}")
                
                # Ask if user wants to continue
                try:
                    response = input("\nContinue with all games? (y/n): ").lower()
                except (EOFError, KeyboardInterrupt):
                    print("\nNo input provided, stopping after test.")
                    response = 'n'
                    
                if response == 'y':
                    print("\n🔄 Scraping all games...")
                    games = scraper.enrich_games(games)
                else:
                    print("⏸️  Stopped after test")
                    return
            else:
                print(f"\n🔄 Scraping all games (this will take ~{len(games)*2//60} minutes)")
                games = scraper.enrich_games(games)
    
    # Save enriched games
    output_file = Path("data/output/enriched_games.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    games_data = [game.model_dump() for game in games]
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(games_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved enriched games to: {output_file}")
    
    # Statistics
    games_with_publishers = sum(1 for g in games if g.publishers)
    total_publishers = len(set(p for g in games for p in g.publishers))
    
    print(f"\n📊 Statistics:")
    print(f"  Games with publishers: {games_with_publishers}/{len(games)}")
    print(f"  Unique publishers: {total_publishers}")
    
    # Show some examples
    print("\n📚 Sample publishers found:")
    for game in games[:10]:
        if game.publishers:
            publishers = ", ".join(game.publishers)
            print(f"  - {game.name}: {publishers}")
    
    print("\n✅ Step 2 complete! Next: Run step3_fetch_essen_data.py")


if __name__ == "__main__":
    main()