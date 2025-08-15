#!/usr/bin/env python3
"""
Step 5: Generate the final Essen Spiel route.

This script:
1. Loads matched games
2. Groups games by hall and booth
3. Generates an optimized route
4. Creates final report in multiple formats
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))
from data_models import BoardGame, Exhibitor, RouteStop, RouteReport


def load_matched_games() -> Tuple[List[Dict], List[BoardGame]]:
    """Load matched games from step 4."""
    input_file = Path("data/output/matched_games.json")
    if not input_file.exists():
        print("❌ Error: matched_games.json not found!")
        print("   Please run step4_match_publishers.py first")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    matched = data['matched']
    unmatched = [BoardGame(**g) for g in data['unmatched']]
    
    return matched, unmatched


def group_by_location(matched_games: List[Dict]) -> Dict[str, Dict[str, List]]:
    """Group matched games by hall and booth."""
    grouped = defaultdict(lambda: defaultdict(list))
    
    for match in matched_games:
        game = BoardGame(**match['game'])
        exhibitor_matches = match['exhibitor_matches']
        
        # For route generation, we'll use the best match (highest confidence)
        # or the first product-confirmed match if available
        best_match = None
        for em in exhibitor_matches:
            if em.get('product_confirmed', False):
                best_match = em
                break
        
        if not best_match and exhibitor_matches:
            # Use the match with highest confidence
            best_match = max(exhibitor_matches, key=lambda x: x.get('confidence', 0))
        
        if not best_match:
            continue  # Skip if no valid matches
        
        exhibitor = Exhibitor(**best_match['exhibitor'])
        hall = exhibitor.hall
        booth = exhibitor.booth
        
        # Check if we already have this exhibitor
        existing = None
        for existing_data in grouped[hall][booth]:
            if existing_data['exhibitor'].id == exhibitor.id:
                existing = existing_data
                break
        
        if existing:
            existing['games'].append(game)
        else:
            grouped[hall][booth].append({
                'exhibitor': exhibitor,
                'games': [game]
            })
    
    return grouped


def create_route_stops(grouped: Dict[str, Dict[str, List]]) -> List[RouteStop]:
    """Create route stops from grouped data."""
    stops = []
    
    for hall, booths in grouped.items():
        for booth, exhibitor_data_list in booths.items():
            for exhibitor_data in exhibitor_data_list:
                stop = RouteStop(
                    hall=str(hall),
                    booth=booth,
                    exhibitor=exhibitor_data['exhibitor'],
                    games=exhibitor_data['games']
                )
                stops.append(stop)
    
    # Sort by priority (want to buy first), then by hall, then by booth
    def sort_key(stop):
        hall = stop.hall
        try:
            # Convert hall to int for numeric sorting
            hall_sort = int(hall)
        except (ValueError, TypeError):
            # Keep as string for non-numeric halls, sort them after numeric ones
            hall_sort = (999, hall)
        return (-stop.priority_score, hall_sort, stop.booth)
    
    stops.sort(key=sort_key)
    
    return stops


def main():
    """Generate the final route."""
    print("=" * 60)
    print("STEP 5: Generate Essen Spiel Route")
    print("=" * 60)
    
    # Load matched games
    print("\n📥 Loading matched games...")
    matched, unmatched = load_matched_games()
    
    total_games = len(matched) + len(unmatched)
    print(f"  Total games: {total_games}")
    print(f"  Matched: {len(matched)}")
    print(f"  Unmatched: {len(unmatched)}")
    
    # Group by location
    print("\n📍 Grouping by hall and booth...")
    grouped = group_by_location(matched)
    
    # Create route stops
    stops = create_route_stops(grouped)
    print(f"✅ Created {len(stops)} route stops")
    
    # Create route report
    report = RouteReport(
        total_games=total_games,
        matched_games=len(matched),
        unmatched_games=unmatched,
        route_stops=stops
    )
    
    # Save JSON report
    output_dir = Path("data/output")
    json_file = output_dir / "route_report.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved JSON report to: {json_file}")
    
    # Save Markdown report
    markdown_file = output_dir / "ESSEN_ROUTE.md"
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(report.to_markdown())
    print(f"💾 Saved Markdown report to: {markdown_file}")
    
    # Generate CSV for easy reference
    csv_file = output_dir / "route_summary.csv"
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("Hall,Booth,Exhibitor,Priority,Games\n")
        for stop in stops:
            games_str = "; ".join([
                f"{'[BUY]' if g.want_to_buy else '[PLAY]'} {g.name}"
                for g in stop.games
            ])
            f.write(f"{stop.hall},{stop.booth},\"{stop.exhibitor.name}\",{stop.priority_score},\"{games_str}\"\n")
    print(f"💾 Saved CSV summary to: {csv_file}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 ROUTE SUMMARY")
    print("=" * 60)
    
    # Hall distribution
    hall_stats = defaultdict(lambda: {'stops': 0, 'games': 0, 'buy': 0, 'play': 0})
    for stop in stops:
        hall_stats[stop.hall]['stops'] += 1
        hall_stats[stop.hall]['games'] += len(stop.games)
        for game in stop.games:
            if game.want_to_buy:
                hall_stats[stop.hall]['buy'] += 1
            if game.want_to_play:
                hall_stats[stop.hall]['play'] += 1
    
    print("\n📍 Halls to Visit:")
    # Sort halls with integers first, then strings
    def hall_sort_key(hall):
        try:
            return (0, int(hall))
        except (ValueError, TypeError):
            return (1, hall)
    
    for hall in sorted(hall_stats.keys(), key=hall_sort_key):
        stats = hall_stats[hall]
        print(f"  Hall {hall}: {stats['stops']} booths, {stats['games']} games")
        print(f"    🛒 {stats['buy']} to buy, 🎮 {stats['play']} to play")
    
    # Priority stops (want to buy)
    buy_stops = [s for s in stops if any(g.want_to_buy for g in s.games)]
    if buy_stops:
        print(f"\n🛒 Priority Stops (Want to Buy): {len(buy_stops)}")
        for stop in buy_stops[:5]:
            buy_games = [g for g in stop.games if g.want_to_buy]
            print(f"  Hall {stop.hall}, Booth {stop.booth}: {stop.exhibitor.name}")
            for game in buy_games:
                print(f"    - {game.name}")
    
    # Print route start
    if stops:
        print("\n🚶 Suggested Route Start:")
        for stop in stops[:3]:
            print(f"  {stop.hall}-{stop.booth}: {stop.exhibitor.name}")
            for game in stop.games:
                priority = "🛒" if game.want_to_buy else "🎮"
                print(f"    {priority} {game.name}")
    
    print("\n" + "=" * 60)
    print("✅ ROUTE GENERATION COMPLETE!")
    print("=" * 60)
    print("\n📄 Generated files:")
    print(f"  - {markdown_file} (human-readable route)")
    print(f"  - {csv_file} (spreadsheet-friendly)")
    print(f"  - {json_file} (full data)")
    current_year = datetime.now().year
    print(f"\n🎯 Ready for Essen Spiel {current_year}!")


if __name__ == "__main__":
    from typing import Tuple
    main()