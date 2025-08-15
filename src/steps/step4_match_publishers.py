#!/usr/bin/env python3
"""
Step 4: Match BGG publishers to Essen exhibitors.

This script:
1. Loads enriched games with publishers
2. Loads Essen exhibitor and product data
3. Performs fuzzy matching between publishers and exhibitors
4. Saves matched results
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from fuzzywuzzy import fuzz, process

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))
from data_models import BoardGame, Exhibitor, GameMatch, ExhibitorMatch


def load_enriched_games() -> List[BoardGame]:
    """Load games with publisher data from step 2."""
    input_file = Path("data/output/enriched_games.json")
    if not input_file.exists():
        print("❌ Error: enriched_games.json not found!")
        print("   Please run step2_scrape_bgg.py first")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return [BoardGame(**item) for item in data]


def load_essen_data() -> Tuple[List[Dict], List[Dict]]:
    """Load Essen exhibitor and product data."""
    exhibitors_file = Path("data/output/essen_exhibitors.json")
    products_file = Path("data/output/essen_products.json")
    
    if not exhibitors_file.exists() or not products_file.exists():
        print("❌ Error: Essen data not found!")
        print("   Please run step3_fetch_essen_data.py first")
        sys.exit(1)
    
    with open(exhibitors_file, 'r', encoding='utf-8') as f:
        exhibitors = json.load(f)
    
    with open(products_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    return exhibitors, products


def match_publisher_to_exhibitor(
    publisher: str, 
    exhibitors: List[Dict],
    threshold: int = 80
) -> Tuple[Dict, float, str]:
    """Match a publisher name to an exhibitor using fuzzy matching on name and info."""
    
    # Create list of exhibitor names for matching
    exhibitor_names = [(e['name'], e) for e in exhibitors]
    
    # Try exact match on name first
    for name, exhibitor in exhibitor_names:
        if publisher.lower() == name.lower():
            return exhibitor, 100.0, "exact_match"
    
    # Check if publisher appears in exhibitor info (for abbreviated names like CGE)
    for exhibitor in exhibitors:
        info = exhibitor.get('info', '').lower()
        if info and publisher.lower() in info:
            # Use token ratio to see how good the match is
            info_score = fuzz.partial_ratio(publisher.lower(), info)
            if info_score >= threshold:
                return exhibitor, info_score, "info_match"
    
    # Fuzzy match on exhibitor names
    best_match = process.extractOne(
        publisher,
        [name for name, _ in exhibitor_names],
        scorer=fuzz.token_sort_ratio
    )
    
    if best_match and best_match[1] >= threshold:
        # Find the exhibitor for this match
        for name, exhibitor in exhibitor_names:
            if name == best_match[0]:
                return exhibitor, best_match[1], "fuzzy_match"
    
    # Also try fuzzy matching against info text (for partial company names in info)
    for exhibitor in exhibitors:
        info = exhibitor.get('info', '')
        if info:
            # Use partial ratio to find publisher name within info text
            info_score = fuzz.partial_ratio(publisher.lower(), info.lower())
            if info_score >= threshold:
                return exhibitor, info_score, "info_fuzzy_match"
    
    return None, 0.0, "no_match"


def match_game_title_to_product(
    game_title: str,
    products: List[Dict],
    threshold: int = 85
) -> Tuple[Dict, float]:
    """Match a game title to a product."""
    
    product_titles = [(p['title'], p) for p in products]
    
    # Try exact match first
    for title, product in product_titles:
        if game_title.lower() == title.lower():
            return product, 100.0
    
    # Fuzzy match
    best_match = process.extractOne(
        game_title,
        [title for title, _ in product_titles],
        scorer=fuzz.token_sort_ratio
    )
    
    if best_match and best_match[1] >= threshold:
        for title, product in product_titles:
            if title == best_match[0]:
                return product, best_match[1]
    
    return None, 0.0


def main():
    """Match publishers to exhibitors."""
    print("=" * 60)
    print("STEP 4: Match Publishers to Exhibitors")
    print("=" * 60)
    
    # Load data
    print("\n📥 Loading data...")
    games = load_enriched_games()
    exhibitors, products = load_essen_data()
    
    print(f"  Games: {len(games)}")
    print(f"  Exhibitors: {len(exhibitors)}")
    print(f"  Products: {len(products)}")
    
    # Matching configuration
    print("\n⚙️  Matching Configuration:")
    publisher_threshold = 90
    product_threshold = 85
    print(f"  Publisher match threshold: {publisher_threshold}%")
    print(f"  Product match threshold: {product_threshold}%")
    
    # Process each game
    print("\n🔍 Matching games to exhibitors...")
    matches = []
    unmatched = []
    
    for game in games:
        exhibitor_matches = []
        
        # Try to match via all publishers
        for publisher in game.publishers:
            exhibitor_data, confidence, reason = match_publisher_to_exhibitor(
                publisher, exhibitors, publisher_threshold
            )
            
            if exhibitor_data:
                # Check if this exhibitor already matched via another publisher
                existing_match = None
                for existing in exhibitor_matches:
                    if existing.exhibitor.id == exhibitor_data['id']:
                        existing_match = existing
                        break
                
                if existing_match:
                    # Update if this match has higher confidence
                    if confidence > existing_match.match_confidence * 100:
                        existing_match.match_confidence = confidence / 100.0
                        existing_match.match_reason = f"Publisher '{publisher}' matched to '{exhibitor_data['name']}' ({reason}, {confidence:.0f}%)"
                else:
                    # Add new exhibitor match
                    exhibitor_match = ExhibitorMatch(
                        exhibitor=Exhibitor(**exhibitor_data),
                        match_confidence=confidence / 100.0,
                        match_reason=f"Publisher '{publisher}' matched to '{exhibitor_data['name']}' ({reason}, {confidence:.0f}%)"
                    )
                    exhibitor_matches.append(exhibitor_match)
        
        # Try product match to find additional exhibitors or confirm existing ones
        product, prod_confidence = match_game_title_to_product(
            game.name, products, product_threshold
        )
        
        if product:
            company_id = product['company_id']
            product_info = f"Product '{product['title']}' confirmed ({prod_confidence:.0f}% match)"
            
            # Find the exhibitor for this product
            product_exhibitor = None
            for exhibitor_data in exhibitors:
                if exhibitor_data['id'] == company_id:
                    product_exhibitor = exhibitor_data
                    break
            
            if product_exhibitor:
                # Check if we already have a match for this exhibitor
                existing_match = None
                for existing in exhibitor_matches:
                    if existing.exhibitor.id == product_exhibitor['id']:
                        existing_match = existing
                        break
                
                if existing_match:
                    # Update existing match with product confirmation
                    existing_match.product_confirmed = True
                    existing_match.product_match_info = product_info
                else:
                    # Add new exhibitor match based on product
                    exhibitor_match = ExhibitorMatch(
                        exhibitor=Exhibitor(**product_exhibitor),
                        match_confidence=prod_confidence / 100.0,
                        match_reason=f"Game title matched to product by '{product_exhibitor['name']}' ({prod_confidence:.0f}%)",
                        product_confirmed=True,
                        product_match_info=product_info
                    )
                    exhibitor_matches.append(exhibitor_match)
        
        # Create match result
        if exhibitor_matches:
            match = GameMatch(
                game=game,
                exhibitor_matches=exhibitor_matches
            )
            matches.append(match)
        else:
            unmatched.append(game)
    
    # Save results
    output_file = Path("data/output/matched_games.json")
    match_data = {
        'matched': [
            {
                'game': m.game.model_dump(),
                'exhibitor_matches': [
                    {
                        'exhibitor': em.exhibitor.model_dump(),
                        'confidence': em.match_confidence,
                        'reason': em.match_reason,
                        'product_confirmed': em.product_confirmed,
                        'product_match_info': em.product_match_info
                    }
                    for em in m.exhibitor_matches
                ]
            }
            for m in matches
        ],
        'unmatched': [g.model_dump() for g in unmatched]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(match_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved matches to: {output_file}")
    
    # Statistics
    print(f"\n📊 Matching Results:")
    print(f"  Matched: {len(matches)}/{len(games)} games")
    print(f"  Unmatched: {len(unmatched)} games")
    
    if matches:
        total_exhibitor_matches = sum(len(m.exhibitor_matches) for m in matches)
        avg_matches_per_game = total_exhibitor_matches / len(matches)
        product_confirmed_games = sum(1 for m in matches if len(m.product_confirmed_matches) > 0)
        total_product_confirmed_matches = sum(len(m.product_confirmed_matches) for m in matches)
        
        print(f"  Total exhibitor matches: {total_exhibitor_matches}")
        print(f"  Average matches per game: {avg_matches_per_game:.1f}")
        print(f"  Games with product confirmation: {product_confirmed_games}/{len(matches)} ({product_confirmed_games/len(matches):.1%})")
        print(f"  Total product confirmed matches: {total_product_confirmed_matches}")
    
    # Show product confirmed games first (since they're rare)
    product_confirmed_games = [m for m in matches if len(m.product_confirmed_matches) > 0]
    if product_confirmed_games:
        print(f"\n🎯 Product Confirmed Games ({len(product_confirmed_games)}):")
        for match in product_confirmed_games:
            priority = "🛒" if match.game.want_to_buy else "🎮"
            print(f"  {priority} {match.game.name}")
            for em in match.product_confirmed_matches:
                print(f"     ✅ {em.exhibitor.name} (Hall {em.exhibitor.hall}, Booth {em.exhibitor.booth})")
                print(f"        🎯 {em.product_match_info}")
    
    # Show sample matches with all exhibitors
    print("\n✅ Sample matches (first 5):")
    for match in matches[:5]:
        priority = "🛒" if match.game.want_to_buy else "🎮"
        print(f"  {priority} {match.game.name} ({len(match.exhibitor_matches)} exhibitors)")
        for i, em in enumerate(match.exhibitor_matches):
            confirmed = " ✅" if em.product_confirmed else " ❓"
            print(f"     {i+1}. {em.exhibitor.name} (Hall {em.exhibitor.hall}, Booth {em.exhibitor.booth}){confirmed}")
            print(f"        {em.match_reason}")
            if em.product_match_info:
                print(f"        🎯 {em.product_match_info}")
    
    # Show unmatched
    if unmatched:
        print(f"\n❌ Unmatched games ({len(unmatched)}):")
        for game in unmatched[:10]:
            priority = "🛒" if game.want_to_buy else "🎮"
            publishers = ", ".join(game.publishers) if game.publishers else "No publishers"
            print(f"  {priority} {game.name}: {publishers}")
    
    print("\n✅ Step 4 complete! Next: Run step5_generate_route.py")


if __name__ == "__main__":
    main()