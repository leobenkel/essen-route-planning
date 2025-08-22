#!/usr/bin/env python3
"""
Step 2: Enrich all games with BGG data (publishers and tags).

This script:
1. Loads the entire collection
2. Enriches ALL games with BGG data (publishers and tags)
3. Uses unified caching for both owned and target games
4. Saves enriched games for use by other steps
"""

import json
import sys
import argparse
from pathlib import Path

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))
from unified_enricher import UnifiedEnricher
from data_models import BoardGame, TaggedGame
from utils import safe_input


def main():
    """Enrich all games with BGG data."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Enrich all games with BGG data")
    parser.add_argument("--no-cache", action="store_true",
                       help="Ignore cached data and scrape all games fresh")
    parser.add_argument("--include-expansions", action="store_true",
                       help="Include expansions in enrichment")
    args = parser.parse_args()
    
    print("=" * 60)
    print("STEP 2: Enrich All Games with BGG Data")
    print("=" * 60)
    
    # Check if collection.csv exists
    if not Path("collection.csv").exists():
        print("❌ Error: collection.csv not found!")
        print("   Please download your BGG collection first.")
        print("   Run: ./run_all to get setup instructions")
        sys.exit(1)
    
    # Initialize unified enricher
    print("\n🌐 Initializing unified enricher...")
    print("   This enriches ALL games in your collection")
    print("   Rate limit: 1-3 seconds between requests (human-like)")
    print("   BGG page cache: data/cache/bgg/")
    
    enricher = UnifiedEnricher()
    
    # Enrich all games
    print("\n📚 Enriching entire collection...")
    all_games = enricher.enrich_all_games(
        collection_path="collection.csv",
        exclude_expansions=not args.include_expansions,
        force_refresh=args.no_cache
    )
    
    # Get target games for Essen route planning
    target_games = enricher.get_target_games()
    
    # Save target games in the format expected by step 3
    output_file = Path("data/output/enriched_games.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert TaggedGame to BoardGame format for compatibility
    games_data = []
    for game in target_games:
        # Create BoardGame-compatible dict
        game_dict = game.model_dump()
        # Remove 'tags' field for backward compatibility
        game_dict.pop('tags', None)
        games_data.append(game_dict)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(games_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved target games to: {output_file}")
    
    # Statistics
    owned = enricher.get_owned_games()
    games_with_publishers = sum(1 for g in target_games if g.publishers)
    games_with_tags = sum(1 for g in owned if g.tags)
    total_publishers = len(set(p for g in target_games for p in g.publishers))
    total_tags = len(set(t for g in owned for t in g.tags))
    
    print(f"\n📊 Enrichment Statistics:")
    print(f"\n  Collection Overview:")
    print(f"    Total games: {len(all_games)}")
    print(f"    Owned games: {len(owned)}")
    print(f"    Target games (want to play/buy): {len(target_games)}")
    
    print(f"\n  Target Games (for Essen route):")
    print(f"    Games with publishers: {games_with_publishers}/{len(target_games)}")
    print(f"    Unique publishers: {total_publishers}")
    
    print(f"\n  Owned Games (for tag search):")
    print(f"    Games with tags: {games_with_tags}/{len(owned)}")
    print(f"    Unique tags: {total_tags}")
    
    # Show some examples
    if target_games:
        print("\n📚 Sample target games with publishers:")
        for game in target_games[:5]:
            if game.publishers:
                publishers = ", ".join(game.publishers)
                print(f"  - {game.name}: {publishers}")
    
    if owned:
        print("\n🏷️ Sample owned games with tags:")
        for game in owned[:5]:
            if game.tags:
                tags = ", ".join(game.tags[:3])
                if len(game.tags) > 3:
                    tags += f" ... ({len(game.tags)-3} more)"
                print(f"  - {game.name}: {tags}")
    
    print("\n✅ Step 2 complete!")
    print("   All games enriched and cached for both features:")
    print("   • Essen route planning: Run step3_fetch_essen_data.py")
    print("   • Tag search: Run ./search <tag>")


if __name__ == "__main__":
    main()