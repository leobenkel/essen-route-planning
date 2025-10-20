"""Game lookup service for finding Essen exhibitor information."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from rapidfuzz import fuzz, process

from data_models import BoardGame, Exhibitor, ExhibitorMatch, GameMatch
from bgg_scraper import BGGScraper


class GameLookupService:
    """Service for looking up game information and matching to Essen exhibitors."""
    
    def __init__(self):
        """Initialize the lookup service."""
        self.bgg_scraper = BGGScraper()
        self._exhibitors_cache: Optional[List[Dict]] = None
        self._products_cache: Optional[List[Dict]] = None
    
    def _load_essen_exhibitors(self) -> List[Dict]:
        """Load Essen exhibitors data."""
        if self._exhibitors_cache is not None:
            return self._exhibitors_cache
            
        exhibitors_file = Path("data/output/essen_exhibitors.json")
        if not exhibitors_file.exists():
            raise FileNotFoundError(
                "Essen exhibitors data not found! Please run ./scripts/step_03 first"
            )
        
        with open(exhibitors_file, 'r', encoding='utf-8') as f:
            self._exhibitors_cache = json.load(f)
        
        return self._exhibitors_cache
    
    def _load_essen_products(self) -> List[Dict]:
        """Load Essen products data."""
        if self._products_cache is not None:
            return self._products_cache
            
        products_file = Path("data/output/essen_products.json")
        if not products_file.exists():
            raise FileNotFoundError(
                "Essen products data not found! Please run ./scripts/step_03 first"
            )
        
        with open(products_file, 'r', encoding='utf-8') as f:
            self._products_cache = json.load(f)
        
        return self._products_cache
    
    def _enrich_game_data(self, game: BoardGame) -> BoardGame:
        """Enrich game with data from BGG."""
        # Extract publisher information
        publishers = self.bgg_scraper.get_publishers(game)
        game.publishers = publishers
        
        # Extract BGG data for game name and other details
        data = self.bgg_scraper._extract_bgg_data(game.bgg_url)
        if data and isinstance(data, dict) and 'item' in data:
            item_data = data['item']
            
            # Update game name
            if isinstance(item_data, dict) and 'name' in item_data and item_data['name']:
                game.name = item_data['name']
            
            # Extract additional game details if available
            if isinstance(item_data, dict) and 'stats' in item_data and item_data['stats']:
                stats = item_data['stats']
                if isinstance(stats, dict):
                    # Average rating
                    if 'average' in stats:
                        try:
                            game.average_rating = float(stats['average'])
                        except (ValueError, TypeError):
                            pass
                    
                    # Complexity weight  
                    if 'avgweight' in stats:
                        try:
                            game.complexity_weight = float(stats['avgweight'])
                        except (ValueError, TypeError):
                            pass
            
            # Playing time from minplaytime/maxplaytime
            if isinstance(item_data, dict) and 'minplaytime' in item_data:
                try:
                    game.playing_time = int(item_data['minplaytime'])
                except (ValueError, TypeError):
                    pass
            
            # Player count from minplayers/maxplayers
            if isinstance(item_data, dict) and 'minplayers' in item_data:
                try:
                    game.min_players = int(item_data['minplayers'])
                except (ValueError, TypeError):
                    pass
            
            if isinstance(item_data, dict) and 'maxplayers' in item_data:
                try:
                    game.max_players = int(item_data['maxplayers'])
                except (ValueError, TypeError):
                    pass
        
        return game
    
    def _match_publisher_to_exhibitor(
        self,
        publisher: str, 
        exhibitors: List[Dict],
        threshold: int = 80
    ) -> Tuple[Optional[Dict], float, str]:
        """Match a publisher name to an exhibitor using fuzzy matching."""
        
        # Create list of exhibitor names for matching
        exhibitor_names = [(e['name'], e) for e in exhibitors if isinstance(e, dict) and 'name' in e]
        
        # Try exact match on name first
        for name, exhibitor in exhibitor_names:
            if publisher.lower() == name.lower():
                return exhibitor, 100.0, "exact_match"
        
        # Check if publisher appears in exhibitor info
        for exhibitor in exhibitors:
            if not isinstance(exhibitor, dict):
                continue
            info = exhibitor.get('info', '').lower()
            if info and publisher.lower() in info:
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
            for name, exhibitor in exhibitor_names:
                if name == best_match[0]:
                    return exhibitor, best_match[1], "fuzzy_match"
        
        # Try fuzzy matching against info text
        for exhibitor in exhibitors:
            if not isinstance(exhibitor, dict):
                continue
            info = exhibitor.get('info', '')
            if info:
                info_score = fuzz.partial_ratio(publisher.lower(), info.lower())
                if info_score >= threshold:
                    return exhibitor, info_score, "info_fuzzy_match"
        
        return None, 0.0, "no_match"
    
    def _match_game_title_to_product(
        self,
        game_title: str,
        products: List[Dict],
        threshold: int = 85
    ) -> Tuple[Optional[Dict], float]:
        """Match a game title to a product."""
        
        product_titles = [(p['title'], p) for p in products if isinstance(p, dict) and 'title' in p]
        
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
    
    def lookup_game(self, game: BoardGame) -> GameMatch:
        """Look up a game and find matching exhibitors at Essen.
        
        Args:
            game: BoardGame object (can have minimal data, will be enriched)
            
        Returns:
            GameMatch with all found exhibitor matches
        """
        # Enrich game data from BGG
        enriched_game = self._enrich_game_data(game)
        
        # Load Essen data
        exhibitors = self._load_essen_exhibitors()
        products = self._load_essen_products()
        
        # Match publishers to exhibitors
        exhibitor_matches = []
        publisher_threshold = 80
        
        for publisher in enriched_game.publishers:
            exhibitor_data, confidence, reason = self._match_publisher_to_exhibitor(
                publisher, exhibitors, publisher_threshold
            )
            
            if exhibitor_data:
                # Check if this exhibitor already matched
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
        product_threshold = 85
        product, prod_confidence = self._match_game_title_to_product(
            enriched_game.name, products, product_threshold
        )
        
        if product:
            company_id = product['company_id']
            product_info = f"Product '{product['title']}' confirmed ({prod_confidence:.0f}% match)"
            
            # Find the exhibitor for this product
            product_exhibitor = None
            for exhibitor_data in exhibitors:
                if isinstance(exhibitor_data, dict) and exhibitor_data.get('id') == company_id:
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
        
        # Create and return the match result
        return GameMatch(
            game=enriched_game,
            exhibitor_matches=exhibitor_matches
        )