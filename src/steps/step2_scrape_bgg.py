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
from utils import safe_input


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
    parser.add_argument("--no-cache", action="store_true",
                       help="Ignore cached data and scrape all games fresh")
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
    
    # Check for cached data (unless --no-cache is specified)
    if args.no_cache:
        print(f"\n🔄 Fresh scrape requested: Scraping all {len(games)} games")
        print(f"   Estimated time: ~{len(games)*2//60} minutes")
        games = scraper.enrich_games(games)
    else:
        cached_games = scraper.load_progress()
        
        if cached_games:
            cached_ids = {g.object_id for g in cached_games}
            remaining_games = [g for g in games if g.object_id not in cached_ids]
            
            if len(remaining_games) == 0:
                print(f"\n✅ All games already scraped: {len(cached_games)} games")
                games = cached_games
            else:
                print(f"\n📂 Found cached progress: {len(cached_games)} games already scraped")
                print(f"   Remaining to scrape: {len(remaining_games)} games")
                response = safe_input("Continue from where left off? (y/n): ", "y").lower()
                
                if response == 'y':
                    print(f"\n🔄 Continuing scrape: {len(remaining_games)} remaining games")
                    remaining_games = scraper.enrich_games(remaining_games)
                    games = cached_games + remaining_games
                else:
                    print(f"\n🔄 Starting fresh scrape (this will take ~{len(games)*2//60} minutes)")
                    games = scraper.enrich_games(games)
        else:
            # No cached data, scrape all games
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