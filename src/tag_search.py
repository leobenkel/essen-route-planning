"""Tag search functionality for owned games."""

from typing import List, Dict, Tuple
from pathlib import Path

from data_models import TaggedGame
from unified_enricher import UnifiedEnricher


class TagSearcher:
    """Search owned games by tags (mechanics and categories)."""
    
    def __init__(self):
        """Initialize the tag searcher."""
        self.enricher = UnifiedEnricher()
        self.owned_games: List[TaggedGame] = []
    
    def load_owned_games(self, collection_path: str = "collection.csv",
                        exclude_expansions: bool = True,
                        force_refresh: bool = False) -> List[TaggedGame]:
        """Load owned games with tags from unified enricher.
        
        Args:
            collection_path: Path to BGG collection CSV
            exclude_expansions: Whether to exclude expansions
            force_refresh: Force refresh from BGG even if cache exists
        
        Returns:
            List of owned games with tags
        """
        # Enrich all games (will use cache if available)
        all_games = self.enricher.enrich_all_games(
            collection_path=collection_path,
            exclude_expansions=exclude_expansions,
            force_refresh=force_refresh
        )
        
        # Filter to owned games only
        self.owned_games = self.enricher.get_owned_games()
        print(f"Found {len(self.owned_games)} owned games")
        
        return self.owned_games
    
    def search_by_tag(self, tag: str, exclude_expansions: bool = True) -> List[TaggedGame]:
        """Search for games with a specific tag or special search modes.
        
        Args:
            tag: Tag to search for (case-insensitive, partial match) or 'unplayed'
            exclude_expansions: Whether to exclude expansions from results
        
        Returns:
            List of games matching the tag or search criteria
        """
        if not self.owned_games:
            raise ValueError("No games loaded. Call load_owned_games first.")
        
        # Special search mode for unplayed games
        if tag.lower() == "unplayed":
            matching_games = []
            for game in self.owned_games:
                # Skip expansions if requested
                if exclude_expansions and game.is_expansion:
                    continue
                # Check if game has no personal rating (unplayed)
                if not game.personal_rating:
                    matching_games.append(game)
            return matching_games
        
        # Normal tag search
        tag_lower = tag.lower()
        matching_games = []
        
        for game in self.owned_games:
            # Skip expansions if requested
            if exclude_expansions and game.is_expansion:
                continue
                
            # Check if any of the game's tags contain the search term
            for game_tag in game.tags:
                if tag_lower in game_tag.lower():
                    matching_games.append(game)
                    break
        
        return matching_games
    
    def get_tag_statistics(self) -> Dict[str, Tuple[int, List[str]]]:
        """Get statistics about all tags in the collection.
        
        Returns:
            Dictionary mapping tag to (count, list of example game names)
        """
        if not self.owned_games:
            raise ValueError("No games loaded. Call load_owned_games first.")
        
        # Count tags and track example games
        tag_games: Dict[str, List[str]] = {}
        
        for game in self.owned_games:
            for tag in game.tags:
                if tag not in tag_games:
                    tag_games[tag] = []
                tag_games[tag].append(game.name)
        
        # Create statistics with counts and up to 3 example games
        stats = {}
        for tag, games in tag_games.items():
            stats[tag] = (len(games), games[:3])
        
        return stats
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags from the collection.
        
        Returns:
            Sorted list of unique tags
        """
        if not self.owned_games:
            raise ValueError("No games loaded. Call load_owned_games first.")
        
        all_tags = set()
        for game in self.owned_games:
            all_tags.update(game.tags)
        
        return sorted(list(all_tags))