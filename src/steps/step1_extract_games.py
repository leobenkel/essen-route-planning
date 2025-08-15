#!/usr/bin/env python3
"""
Step 1: Extract target games from BGG collection CSV.

This script:
1. Reads the collection.csv file
2. Extracts games marked as WANT TO PLAY or WANT TO BUY
3. Saves the results to data/output/target_games.json
"""

import json
import sys
from pathlib import Path
import argparse

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))
from collection_extractor import CollectionExtractor


def main():
    """Extract and save target games."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Extract target games from BGG collection")
    parser.add_argument("--include-expansions", action="store_true",
                       help="Include expansions in extraction (default: exclude)")
    parser.add_argument("--exclude-expansions", action="store_true", 
                       help="Explicitly exclude expansions (default behavior)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("STEP 1: Extract Target Games from Collection")
    print("=" * 60)
    
    # Ensure output directory exists
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine expansion filtering preference
    include_expansions = False  # Default: exclude expansions
    
    if args.include_expansions:
        include_expansions = True
        print("\n🎯 Including expansions (--include-expansions)")
    elif args.exclude_expansions:
        include_expansions = False
        print("\n🎯 Excluding expansions (default behavior)")
    else:
        # Interactive mode - show what would be filtered and let user decide
        print("\n🎯 Expansion Filtering (Default: Exclude):")
        print("   Board game expansions are often sold at the same booth as the base game.")
        print("   By default, expansions are EXCLUDED to focus on finding new publishers/booths.")
        
        # Check what expansions would be filtered
        temp_extractor = CollectionExtractor("collection.csv", include_expansions=False)
        expansion_info = temp_extractor.get_expansion_info()
        
        if expansion_info["expansions_filtered"] > 0:
            print(f"\n📋 Found {expansion_info['expansions_filtered']} potential expansions that will be excluded:")
            for example in expansion_info["expansion_examples"]:
                print(f"   - {example}")
            if len(expansion_info["expansion_examples"]) < expansion_info["expansions_filtered"]:
                remaining = expansion_info["expansions_filtered"] - len(expansion_info["expansion_examples"])
                print(f"   ... and {remaining} more")
            
            print(f"\n   Target games: {expansion_info['total_without_expansions']} (excluding expansions)")
            print(f"   If including expansions: {expansion_info['total_with_expansions']} games")
            
            try:
                response = input("\nInclude expansions anyway? (y/n, default=n): ").lower()
                include_expansions = response == 'y'
            except (EOFError, KeyboardInterrupt):
                print("\nNo input provided, excluding expansions (default).")
                include_expansions = False
        else:
            print("   No expansions detected in your target games.")
            include_expansions = False
    
    # Initialize extractor with user preference
    extractor = CollectionExtractor("collection.csv", include_expansions=include_expansions)
    
    # Get summary
    print("\n📊 Collection Summary:")
    summary = extractor.get_summary()
    for key, value in summary.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Extract target games
    print(f"\n🎮 Extracting target games{'(excluding expansions)' if not include_expansions else ''}...")
    games = extractor.extract_target_games()
    print(f"✅ Extracted {len(games)} games")
    
    # Save to JSON with metadata
    output_file = output_dir / "target_games.json"
    
    # Prepare data with metadata
    output_data = {
        "metadata": {
            "include_expansions": include_expansions,
            "total_games": len(games),
            "extraction_settings": {
                "expansions_filtered": not include_expansions
            }
        },
        "games": [game.model_dump() for game in games]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved to: {output_file}")
    
    # Show breakdown
    want_to_buy = sum(1 for g in games if g.want_to_buy)
    want_to_play = sum(1 for g in games if g.want_to_play)
    
    print(f"\n📝 Breakdown:")
    print(f"  🛒 Want to Buy: {want_to_buy}")
    print(f"  🎮 Want to Play: {want_to_play}")
    
    # Show first 5 games of each type
    print("\n🛒 First 5 'Want to Buy' games:")
    buy_games = [g for g in games if g.want_to_buy]
    for game in buy_games[:5]:
        print(f"  - {game.name} (ID: {game.object_id})")
    
    print("\n🎮 First 5 'Want to Play' games:")
    play_games = [g for g in games if g.want_to_play and not g.want_to_buy]
    for game in play_games[:5]:
        print(f"  - {game.name} (ID: {game.object_id})")
    
    print("\n✅ Step 1 complete! Next: Run step2_scrape_bgg.py")


if __name__ == "__main__":
    main()