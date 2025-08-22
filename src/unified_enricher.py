"""Unified game enricher that fetches all BGG data for the entire collection."""

import json
from typing import List, Dict, Optional
from pathlib import Path
from tqdm import tqdm

from data_models import BoardGame, TaggedGame
from collection_extractor import CollectionExtractor
from bgg_scraper import BGGScraper


class UnifiedEnricher:
    """Unified enricher for all games in the collection."""
    
    def __init__(self, cache_file: str = "data/cache/enriched_all_games.json"):
        """Initialize the unified enricher.
        
        Args:
            cache_file: Path to cache file for enriched games
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.enriched_games: List[TaggedGame] = []
    
    def load_from_cache(self) -> bool:
        """Load enriched games from cache.
        
        Returns:
            True if cache exists and was loaded, False otherwise
        """
        if not self.cache_file.exists():
            return False
        
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
            
            # Load with TaggedGame to get all fields including tags
            self.enriched_games = [TaggedGame(**game) for game in data['games']]
            print(f"Loaded {len(self.enriched_games)} games from cache")
            return True
        except Exception as e:
            print(f"Error loading cache: {e}")
            return False
    
    def save_to_cache(self) -> None:
        """Save enriched games to cache."""
        data = {
            'metadata': {
                'total_games': len(self.enriched_games),
                'owned_games': sum(1 for g in self.enriched_games if g.owned),
                'want_to_play': sum(1 for g in self.enriched_games if g.want_to_play),
                'want_to_buy': sum(1 for g in self.enriched_games if g.want_to_buy),
            },
            'games': [game.model_dump() for game in self.enriched_games]
        }
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def enrich_all_games(self, collection_path: str = "collection.csv",
                         exclude_expansions: bool = True,
                         force_refresh: bool = False) -> List[TaggedGame]:
        """Enrich all games from the collection with BGG data.
        
        Args:
            collection_path: Path to BGG collection CSV
            exclude_expansions: Whether to exclude expansions
            force_refresh: Force refresh from BGG even if cache exists
        
        Returns:
            List of enriched games with publishers and tags
        """
        # Extract ALL games from collection first
        print("Extracting all games from collection...")
        extractor = CollectionExtractor(collection_path)
        all_games = extractor.extract_all_games(mark_expansions=True)
        
        # Filter expansions if requested
        if exclude_expansions:
            base_games = [g for g in all_games if not g.is_expansion]
            expansion_count = len(all_games) - len(base_games)
            print(f"Filtering out {expansion_count} expansions")
            all_games = base_games
        
        # Show breakdown
        owned = sum(1 for g in all_games if g.owned)
        want_to_play = sum(1 for g in all_games if g.want_to_play and not g.owned)
        want_to_buy = sum(1 for g in all_games if g.want_to_buy and not g.owned)
        
        print(f"\n📊 Collection breakdown:")
        print(f"  Total games: {len(all_games)}")
        print(f"  Owned: {owned}")
        print(f"  Want to Play: {want_to_play}")
        print(f"  Want to Buy: {want_to_buy}")
        
        # Load existing cache to check what we already have
        existing_cache = {}
        if self.cache_file.exists() and not force_refresh:
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    # Create lookup by object_id
                    for game_data in cache_data.get('games', []):
                        # Only use cached data if it has the enriched fields
                        if 'publishers' in game_data or 'tags' in game_data:
                            existing_cache[game_data['object_id']] = game_data
                    print(f"Found {len(existing_cache)} enriched games in cache")
            except Exception:
                pass
        
        # Determine which games need enrichment
        games_to_fetch = []
        cached_games = []
        
        for game in all_games:
            if game.object_id in existing_cache and not force_refresh:
                cached = existing_cache[game.object_id]
                # Create enriched game from cache with updated collection status
                enriched_game = TaggedGame(
                    object_id=game.object_id,
                    name=game.name,
                    want_to_play=game.want_to_play,
                    want_to_buy=game.want_to_buy,
                    owned=game.owned,
                    is_expansion=game.is_expansion,
                    publishers=cached.get('publishers', []),
                    personal_rating=game.personal_rating,  # Use fresh personal rating from collection
                    tags=cached.get('tags', []),
                    average_rating=game.average_rating,
                    complexity_weight=game.complexity_weight,
                    playing_time=game.playing_time,
                    min_players=game.min_players,
                    max_players=game.max_players
                )
                cached_games.append(enriched_game)
            else:
                games_to_fetch.append(game)
        
        print(f"Using cached data for {len(cached_games)} games")
        print(f"Need to fetch BGG data for {len(games_to_fetch)} games")
        
        # Initialize scraper only if we need to fetch
        enriched_games = cached_games.copy()
        
        if games_to_fetch:
            scraper = BGGScraper()
            print("\nFetching BGG data (publishers and tags)...")
            
            for game in tqdm(games_to_fetch, desc="Fetching from BGG"):
                # Fetch from BGG
                publishers = scraper.get_publishers(game)
                tags = scraper.get_tags(game)
                
                # Create enriched game with fetched data
                game_data = game.model_dump()
                game_data['publishers'] = publishers
                game_data['tags'] = tags
                enriched_game = TaggedGame(**game_data)
                
                enriched_games.append(enriched_game)
                
                # Save progress periodically (including cached games)
                if len(enriched_games) % 10 == 0:
                    self.enriched_games = enriched_games
                    self.save_to_cache()
        
        # Save final results
        self.enriched_games = enriched_games
        self.save_to_cache()
        
        print(f"\n✅ Total enriched games: {len(self.enriched_games)}")
        return self.enriched_games
    
    def get_owned_games(self) -> List[TaggedGame]:
        """Get only owned games from the enriched collection."""
        return [g for g in self.enriched_games if g.owned]
    
    def get_target_games(self) -> List[TaggedGame]:
        """Get target games (want to play/buy, not owned) from the enriched collection."""
        return [g for g in self.enriched_games if (g.want_to_play or g.want_to_buy) and not g.owned]