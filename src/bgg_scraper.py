"""BoardGameGeek scraper for publisher information."""

import time
import json
import random
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from diskcache import Cache
from tqdm import tqdm
from data_models import BoardGame


class BGGScraper:
    """Scraper for BoardGameGeek publisher information."""
    
    def __init__(self, cache_dir: str = "data/cache", 
                 rate_limit: Tuple[float, float] = (1.0, 3.0)):
        """Initialize the scraper with caching and rate limiting.
        
        Args:
            cache_dir: Directory for caching responses
            rate_limit: Tuple of (min, max) seconds to wait between requests
        """
        self.cache = Cache(cache_dir)
        self.rate_limit_min = rate_limit[0]
        self.rate_limit_max = rate_limit[1]
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def _rate_limit_wait(self) -> None:
        """Enforce rate limiting with random delay for human-like behavior."""
        elapsed = time.time() - self.last_request_time
        # Random wait between min and max seconds
        wait_time = random.uniform(self.rate_limit_min, self.rate_limit_max)
        
        if elapsed < wait_time:
            actual_wait = wait_time - elapsed
            time.sleep(actual_wait)
        
        self.last_request_time = time.time()
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with caching and rate limiting."""
        # Check cache first
        if url in self.cache:
            return self.cache[url]
        
        # Rate limit
        self._rate_limit_wait()
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            content = response.text
            
            # Cache the response
            self.cache[url] = content
            return content
            
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_publishers(self, game: BoardGame) -> List[str]:
        """Extract publisher names from a game's BGG page."""
        content = self._fetch_page(game.bgg_url)
        if not content:
            return []
        
        publishers = []
        
        # First try: Extract from JSON data embedded in the page
        try:
            import re
            import json as json_lib
            
            # Look for the GEEK.geekitemPreload JSON data
            json_match = re.search(r'GEEK\.geekitemPreload\s*=\s*(\{.*?\});', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json_lib.loads(json_str)
                
                # Navigate to publisher data
                if 'item' in data and 'links' in data['item'] and 'boardgamepublisher' in data['item']['links']:
                    for publisher in data['item']['links']['boardgamepublisher']:
                        if 'name' in publisher and publisher['name']:
                            name = publisher['name'].strip()
                            if name and name not in publishers:
                                publishers.append(name)
        except Exception as e:
            # JSON parsing failed, continue to HTML fallback
            pass
        
        # Fallback: Try HTML parsing (older method)
        if not publishers:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for publisher links in the game credits
            publisher_links = soup.find_all('a', href=lambda x: x and '/boardgamepublisher/' in x)
            
            for link in publisher_links:
                publisher_name = link.get_text(strip=True)
                if publisher_name and publisher_name not in publishers:
                    publishers.append(publisher_name)
            
            # Alternative method: look in the info panel
            if not publishers:
                info_items = soup.find_all('div', class_='game-header-credits')
                for item in info_items:
                    if 'Publisher' in item.get_text():
                        links = item.find_all('a')
                        for link in links:
                            name = link.get_text(strip=True)
                            if name and name not in publishers:
                                publishers.append(name)
        
        return publishers
    
    def enrich_games(self, games: List[BoardGame], progress: bool = True) -> List[BoardGame]:
        """Enrich games with publisher information from BGG.
        
        Args:
            games: List of games to enrich
            progress: Show progress bar
        
        Returns:
            List of games with publisher information added
        """
        iterator = tqdm(games, desc="Fetching BGG data") if progress else games
        
        for game in iterator:
            if progress:
                iterator.set_description(f"Fetching: {game.name[:30]}")
            
            publishers = self.get_publishers(game)
            game.publishers = publishers
            
            # Save progress periodically
            if len(games) > 10 and games.index(game) % 10 == 0:
                self._save_progress(games[:games.index(game)+1])
        
        # Save final results
        self._save_progress(games)
        return games
    
    def _save_progress(self, games: List[BoardGame]) -> None:
        """Save enriched games to a JSON file for recovery."""
        output_file = Path("data/cache/enriched_games.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = [game.model_dump() for game in games]
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_progress(self) -> Optional[List[BoardGame]]:
        """Load previously enriched games from cache."""
        cache_file = Path("data/cache/enriched_games.json")
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return [BoardGame(**item) for item in data]
        except Exception as e:
            print(f"Error loading cached games: {e}")
            return None