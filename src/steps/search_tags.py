#!/usr/bin/env python3
"""
Search owned games by tags.

This script:
1. Loads owned games from collection (with caching)
2. Fetches tags from BGG if needed
3. Searches for games matching the provided tag
4. Shows statistics if no matches found
"""

import sys
import argparse
from pathlib import Path
from typing import List

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))
from tag_search import TagSearcher
from data_models import TaggedGame


# ANSI color codes for terminal output
class Colors:
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    UNDERLINE = '\033[4m'


def format_game_info(game: TaggedGame) -> str:
    """Format game information for display."""
    info_parts = []
    
    # Personal rating first (most important)
    if game.personal_rating:
        info_parts.append(f"{Colors.BOLD}🔥 {game.personal_rating:.0f}{Colors.ENDC}")
    else:
        info_parts.append(f"{Colors.CYAN}🚫 Unplayed{Colors.ENDC}")
    
    # BGG average rating
    if game.average_rating:
        info_parts.append(f"⭐ {game.average_rating:.1f}")
    
    # Other info
    if game.complexity_weight:
        info_parts.append(f"🎯 {game.complexity_weight:.1f}")
    if game.min_players and game.max_players:
        if game.min_players == game.max_players:
            info_parts.append(f"👥 {game.min_players}")
        else:
            info_parts.append(f"👥 {game.min_players}-{game.max_players}")
    if game.playing_time:
        info_parts.append(f"⏱️ {game.playing_time}min")
    
    return " | ".join(info_parts) if info_parts else ""


def display_search_results(games: List[TaggedGame], search_tag: str) -> None:
    """Display search results."""
    print(f"\n{Colors.BOLD}{Colors.GREEN}🎲 Found {len(games)} games with tag matching '{search_tag}':{Colors.ENDC}")
    
    # Add legend
    print(f"\n{Colors.BOLD}Legend:{Colors.ENDC}")
    print(f"  🔥 Your Rating | 🚫 Unplayed | ⭐ BGG Average Rating | 🎯 Complexity Weight | 👥 Player Count | ⏱️ Playing Time")
    print("=" * 60)
    
    # Sort by BGG rating (highest first), then by name
    sorted_games = sorted(games, key=lambda g: (-(g.average_rating or 0), g.name))
    
    for game in sorted_games:
        info = format_game_info(game)
        # Game title in bold
        if info:
            print(f"• {Colors.BOLD}{game.name}{Colors.ENDC} ({info})")
        else:
            print(f"• {Colors.BOLD}{game.name}{Colors.ENDC}")
        
        # Show BGG URL with field name in bold
        print(f"  {Colors.BOLD}URL:{Colors.ENDC} {Colors.BLUE}{game.bgg_url}{Colors.ENDC}")
        
        # Show all tags sorted alphabetically
        if game.tags:
            # Sort tags alphabetically
            sorted_tags = sorted(game.tags)
            # Highlight matching tags with yellow background
            highlighted_tags = []
            for tag in sorted_tags:
                if search_tag.lower() in tag.lower():
                    highlighted_tags.append(f"{Colors.YELLOW}{Colors.BOLD}{tag}{Colors.ENDC}")
                else:
                    highlighted_tags.append(tag)
            print(f"  {Colors.BOLD}Tags:{Colors.ENDC} {', '.join(highlighted_tags)}")
        print()


def display_tag_statistics(searcher: TagSearcher, search_tag: str) -> None:
    """Display tag statistics when no matches found."""
    print(f"\n{Colors.RED}❌ No games found with tag matching '{search_tag}'{Colors.ENDC}")
    print(f"\n{Colors.BOLD}{Colors.CYAN}📊 Available tags in your collection:{Colors.ENDC}")
    print("=" * 60)
    
    # Get statistics
    stats = searcher.get_tag_statistics()
    
    # Sort by count (descending)
    sorted_tags = sorted(stats.items(), key=lambda x: x[1][0], reverse=True)
    
    # Show top 20 tags
    print(f"\n{Colors.BOLD}Top 20 most common tags:{Colors.ENDC}")
    for tag, (count, examples) in sorted_tags[:20]:
        example_str = ", ".join(examples)
        if len(examples) < count:
            example_str += "..."
        print(f"• {Colors.BOLD}{tag}{Colors.ENDC} ({Colors.GREEN}{count} games{Colors.ENDC})")
        print(f"  {Colors.BOLD}Examples:{Colors.ENDC} {example_str}")
    
    if len(sorted_tags) > 20:
        print(f"\n... and {len(sorted_tags) - 20} more tags")
    
    # Suggest similar tags
    print(f"\n{Colors.BOLD}{Colors.YELLOW}💡 Searching tips:{Colors.ENDC}")
    print("• Tags are case-insensitive")
    print("• Partial matches work (e.g., 'coop' matches 'Cooperative Game')")
    print("• Try broader terms like 'card', 'dice', 'economic', etc.")


def main():
    """Main search function."""
    parser = argparse.ArgumentParser(description="Search owned games by tags")
    parser.add_argument("tag", nargs="?", help="Tag to search for")
    parser.add_argument("--refresh", action="store_true", 
                       help="Force refresh from BGG (ignore cache)")
    parser.add_argument("--list-tags", action="store_true",
                       help="List all available tags")
    parser.add_argument("--include-expansions", action="store_true",
                       help="Include expansions in search results")
    args = parser.parse_args()
    
    # Initialize searcher
    searcher = TagSearcher()
    
    # Load or fetch games
    print("Loading owned games...")
    try:
        exclude_expansions_for_loading = not args.include_expansions
        games = searcher.load_owned_games(
            exclude_expansions=exclude_expansions_for_loading, 
            force_refresh=args.refresh
        )
        print(f"✅ Loaded {len(games)} owned games")
    except FileNotFoundError:
        print("❌ Error: collection.csv not found!")
        print("   Please download your BGG collection first.")
        sys.exit(1)
    
    # List all tags if requested
    if args.list_tags:
        all_tags = searcher.get_all_tags()
        print(f"\n📋 All {len(all_tags)} unique tags in your collection:")
        print("=" * 60)
        for tag in all_tags:
            matching_games = searcher.search_by_tag(tag)
            print(f"• {tag} ({len(matching_games)} games)")
        return
    
    # Check if tag was provided
    if not args.tag:
        print("\n❌ Error: Please provide a tag to search for")
        print("   Usage: ./search <tag>")
        print("   Example: ./search coop")
        print("\n   Or use --list-tags to see all available tags")
        sys.exit(1)
    
    # Search for games (expansions already filtered during loading)
    matching_games = searcher.search_by_tag(args.tag, exclude_expansions=False)
    
    if matching_games:
        # Special messaging for unplayed search
        if args.tag.lower() == "unplayed":
            print(f"\n{Colors.BOLD}{Colors.GREEN}🎲 Found {len(matching_games)} unplayed games:{Colors.ENDC}")
            print("=" * 60)
            
            # Sort unplayed games by BGG rating (highest first)
            sorted_games = sorted(matching_games, key=lambda g: (-(g.average_rating or 0), g.name))
            
            for game in sorted_games:
                info = format_game_info(game)
                print(f"• {Colors.BOLD}{game.name}{Colors.ENDC} ({info})")
                print(f"  {Colors.BOLD}URL:{Colors.ENDC} {Colors.BLUE}{game.bgg_url}{Colors.ENDC}")
                
                # Show all tags sorted alphabetically for unplayed games
                if game.tags:
                    sorted_tags = sorted(game.tags)
                    print(f"  {Colors.BOLD}Tags:{Colors.ENDC} {', '.join(sorted_tags)}")
                print()
        else:
            display_search_results(matching_games, args.tag)
            
        if not args.include_expansions:
            print(f"\n{Colors.CYAN}💡 Note: Expansions are excluded by default. Use --include-expansions to see them.{Colors.ENDC}")
    else:
        if args.tag.lower() == "unplayed":
            print(f"\n{Colors.GREEN}🎉 All your games have been played! No unplayed games found.{Colors.ENDC}")
        else:
            display_tag_statistics(searcher, args.tag)


if __name__ == "__main__":
    main()