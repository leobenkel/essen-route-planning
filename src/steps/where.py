#!/usr/bin/env python3
"""
Where Command: Find Essen exhibitor information for a specific BoardGameGeek game.

Usage: python where.py <BGG_URL>
Example: python where.py https://boardgamegeek.com/boardgame/418354/babylon
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))

from url_parser import parse_bgg_url, is_valid_bgg_url
from game_lookup import GameLookupService


class Colors:
    """Terminal colors for formatted output."""
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    ENDC = '\033[0m'  # End color


def show_usage():
    """Display usage information."""
    print(f"{Colors.BOLD}🎲 Essen Game Locator{Colors.ENDC}")
    print("=" * 30)
    print()
    print("Find hall and booth information for any BoardGameGeek game at Essen Spiel.")
    print()
    print(f"{Colors.BOLD}Usage:{Colors.ENDC}")
    print("  ./where <BGG_URL>")
    print()
    print(f"{Colors.BOLD}Examples:{Colors.ENDC}")
    print("  ./where https://boardgamegeek.com/boardgame/418354/babylon")
    print("  ./where https://boardgamegeek.com/boardgame/1406")
    print("  ./where boardgamegeek.com/boardgame/418354")
    print()
    print(f"{Colors.BOLD}Supported URL Formats:{Colors.ENDC}")
    print("  • https://boardgamegeek.com/boardgame/{id}/{slug}")
    print("  • https://boardgamegeek.com/boardgame/{id}")
    print("  • boardgamegeek.com/boardgame/{id}/{slug}")
    print()
    print(f"{Colors.BOLD}💡 Tips:{Colors.ENDC}")
    print("  • Results are cached for faster subsequent lookups")
    print("  • Requires Essen data - run ./scripts/step_03 first if needed")


def format_exhibitor_match(match):
    """Format an exhibitor match for display."""
    exhibitor = match.exhibitor
    
    # Format hall display
    if isinstance(exhibitor.hall, int):
        hall_display = f"Hall {exhibitor.hall}"
    else:
        hall_display = exhibitor.hall
    
    # Confirmation status
    if match.product_confirmed:
        status = f"{Colors.GREEN}✅ Product confirmed{Colors.ENDC}"
    else:
        confidence_pct = int(match.match_confidence * 100)
        if confidence_pct >= 90:
            status = f"{Colors.GREEN}❓ Publisher match ({confidence_pct}%){Colors.ENDC}"
        elif confidence_pct >= 80:
            status = f"{Colors.YELLOW}❓ Publisher match ({confidence_pct}%){Colors.ENDC}"
        else:
            status = f"{Colors.RED}❓ Weak match ({confidence_pct}%){Colors.ENDC}"
    
    # Additional info
    info_lines = []
    if exhibitor.country:
        info_lines.append(f"Country: {exhibitor.country}")
    if exhibitor.website:
        info_lines.append(f"Website: {Colors.BLUE}{exhibitor.website}{Colors.ENDC}")
    if match.product_match_info:
        info_lines.append(f"Product: {match.product_match_info}")
    
    print(f"   {status} {Colors.BOLD}{exhibitor.name}{Colors.ENDC} ({Colors.CYAN}{hall_display}, Booth {exhibitor.booth}{Colors.ENDC})")
    for info in info_lines:
        print(f"      {info}")


def main():
    """Main entry point for the where command."""
    parser = argparse.ArgumentParser(
        description="Find Essen exhibitor information for a BoardGameGeek game",
        add_help=False
    )
    parser.add_argument("url", nargs="?", help="BoardGameGeek URL")
    parser.add_argument("--help", "-h", action="store_true", help="Show help")
    
    args = parser.parse_args()
    
    if args.help or not args.url:
        show_usage()
        return
    
    # Validate URL
    if not is_valid_bgg_url(args.url):
        print(f"{Colors.RED}❌ Error: Invalid BoardGameGeek URL{Colors.ENDC}")
        print(f"   Provided: {args.url}")
        print()
        print("Expected format: https://boardgamegeek.com/boardgame/{id}/{slug}")
        return
    
    # Parse the URL
    game = parse_bgg_url(args.url)
    if not game:
        print(f"{Colors.RED}❌ Error: Could not parse BGG URL{Colors.ENDC}")
        return
    
    print(f"{Colors.BOLD}🔍 Looking up game...{Colors.ENDC}")
    print(f"   BGG ID: {game.object_id}")
    print()
    
    try:
        # Initialize lookup service and find the game
        lookup_service = GameLookupService()
        match_result = lookup_service.lookup_game(game)
        
        # Display results
        enriched_game = match_result.game
        
        print(f"{Colors.BOLD}🎲 {enriched_game.name}{Colors.ENDC}")
        
        # Game details
        details = []
        if enriched_game.average_rating:
            details.append(f"⭐ {enriched_game.average_rating:.1f}")
        if enriched_game.complexity_weight:
            details.append(f"🎯 {enriched_game.complexity_weight:.1f}")
        if enriched_game.min_players and enriched_game.max_players:
            if enriched_game.min_players == enriched_game.max_players:
                details.append(f"👥 {enriched_game.min_players}")
            else:
                details.append(f"👥 {enriched_game.min_players}-{enriched_game.max_players}")
        if enriched_game.playing_time:
            details.append(f"⏱️ {enriched_game.playing_time}min")
        
        if details:
            print(f"{Colors.WHITE}   {' | '.join(details)}{Colors.ENDC}")
        
        print(f"{Colors.BOLD}🔗 {Colors.BLUE}{enriched_game.bgg_url}{Colors.ENDC}")
        print()
        
        # Publishers
        if enriched_game.publishers:
            publishers_str = ", ".join(enriched_game.publishers)
            print(f"{Colors.BOLD}📍 Publishers:{Colors.ENDC} {publishers_str}")
        else:
            print(f"{Colors.YELLOW}📍 No publishers found{Colors.ENDC}")
        print()
        
        # Exhibitor matches
        if match_result.exhibitor_matches:
            print(f"{Colors.BOLD}🏢 Found at Essen:{Colors.ENDC}")
            
            # Sort by product confirmed first, then by confidence
            sorted_matches = sorted(
                match_result.exhibitor_matches,
                key=lambda x: (x.product_confirmed, x.match_confidence),
                reverse=True
            )
            
            for match in sorted_matches:
                format_exhibitor_match(match)
            
            print()
            
            # Summary
            confirmed_count = len(match_result.product_confirmed_matches)
            total_count = len(match_result.exhibitor_matches)
            
            if confirmed_count > 0:
                print(f"{Colors.GREEN}✅ {confirmed_count} confirmed match(es) found{Colors.ENDC}")
            else:
                print(f"{Colors.YELLOW}❓ {total_count} potential match(es) found{Colors.ENDC}")
                print(f"   {Colors.WHITE}(No product confirmation available){Colors.ENDC}")
        
        else:
            print(f"{Colors.RED}❌ No exhibitors found at Essen{Colors.ENDC}")
            if enriched_game.publishers:
                print(f"   {Colors.WHITE}Searched for: {', '.join(enriched_game.publishers)}{Colors.ENDC}")
            else:
                print(f"   {Colors.WHITE}No publisher information available for matching{Colors.ENDC}")
            print()
            print(f"{Colors.YELLOW}💡 Tips:{Colors.ENDC}")
            print("   • The game might be available at Essen but not listed under these publishers")
            print("   • Try checking the BGG page for alternative or international publishers")
            print("   • Some games may be distributed by different companies at Essen")
    
    except FileNotFoundError as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.ENDC}")
        print(f"   {Colors.WHITE}Run ./scripts/step_03 to fetch Essen data first{Colors.ENDC}")
    
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.ENDC}")
        print(f"   {Colors.WHITE}Please try again or report this issue{Colors.ENDC}")


if __name__ == "__main__":
    main()