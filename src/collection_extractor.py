"""Extract target games from BGG collection CSV using DuckDB."""

import duckdb
from typing import List
from pathlib import Path
from data_models import BoardGame


class CollectionExtractor:
    """Extract and process games from BGG collection CSV."""
    
    def __init__(self, csv_path: str = "collection.csv", include_expansions: bool = False):
        """Initialize the extractor with CSV path.
        
        Args:
            csv_path: Path to the BGG collection CSV file
            include_expansions: Whether to include expansions in results
        """
        self.csv_path = Path(csv_path)
        self.include_expansions = include_expansions
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Collection CSV not found: {csv_path}")
    
    def _is_expansion(self, name: str) -> bool:
        """Check if a game name indicates it's an expansion."""
        expansion_keywords = [
            'expansion', 'extension', 'add-on', 'addon', 
            'mini-expansion', 'promo', 'promotional',
            # Common patterns for expansions
            ': ', ' – ', ' - ',  # Games with colons/dashes often indicate expansions
        ]
        
        name_lower = name.lower()
        
        # Check for explicit expansion keywords
        for keyword in expansion_keywords[:5]:  # First 5 are explicit keywords
            if keyword in name_lower:
                return True
        
        # Check for colon/dash patterns (but be more selective)
        if (':' in name or ' – ' in name or ' - ' in name):
            # Some base games also have colons, so we need to be careful
            # Skip if it's likely a subtitle rather than expansion
            # But be more specific - only skip if these words are at the end or standalone
            exclusion_words = ['edition', 'deluxe', 'collection', 'reprint']
            # Only exclude if the word appears as a complete word, not as part of another word
            words = name_lower.split()
            if any(word in exclusion_words for word in words):
                return False
            return True
        
        return False
    
    def extract_target_games(self, include_expansions: bool = None) -> List[BoardGame]:
        """Extract games marked as want to play or want to buy.
        
        Args:
            include_expansions: Override the instance setting for this extraction
        """
        if include_expansions is None:
            include_expansions = self.include_expansions
            
        conn = duckdb.connect(":memory:")
        
        query = f"""
        SELECT 
            objectid as object_id,
            objectname as name,
            CASE WHEN wanttoplay = '1' THEN true ELSE false END as want_to_play,
            CASE WHEN wanttobuy = '1' THEN true ELSE false END as want_to_buy,
            average as average_rating,
            avgweight as complexity_weight,
            playingtime as playing_time,
            minplayers as min_players,
            maxplayers as max_players
        FROM '{self.csv_path}'
        WHERE (wanttoplay = '1' OR wanttobuy = '1') AND own != '1'
        ORDER BY 
            CASE WHEN wanttobuy = '1' THEN 0 ELSE 1 END,
            objectname
        """
        
        result = conn.execute(query).fetchall()
        conn.close()
        
        games = []
        expansions_filtered = 0
        
        for row in result:
            game_name = row[1]
            
            # Check if this is an expansion and should be filtered
            if not include_expansions and self._is_expansion(game_name):
                expansions_filtered += 1
                continue
                
            game = BoardGame(
                object_id=row[0],
                name=game_name,
                want_to_play=row[2],
                want_to_buy=row[3],
                average_rating=row[4] if row[4] is not None else None,
                complexity_weight=row[5] if row[5] is not None else None,
                playing_time=row[6] if row[6] is not None else None,
                min_players=row[7] if row[7] is not None else None,
                max_players=row[8] if row[8] is not None else None
            )
            games.append(game)
        
        # Store filtering stats for reporting
        self._last_expansions_filtered = expansions_filtered
        
        return games
    
    def get_summary(self) -> dict:
        """Get summary statistics of the collection."""
        conn = duckdb.connect(":memory:")
        
        query = f"""
        SELECT 
            COUNT(*) as total_collection,
            SUM(CASE WHEN wanttoplay = '1' THEN 1 ELSE 0 END) as want_to_play,
            SUM(CASE WHEN wanttobuy = '1' THEN 1 ELSE 0 END) as want_to_buy,
            SUM(CASE WHEN wanttoplay = '1' OR wanttobuy = '1' THEN 1 ELSE 0 END) as target_games,
            SUM(CASE WHEN own = '1' THEN 1 ELSE 0 END) as owned
        FROM '{self.csv_path}'
        """
        
        result = conn.execute(query).fetchone()
        conn.close()
        
        return {
            "total_collection": result[0],
            "want_to_play": result[1],
            "want_to_buy": result[2],
            "target_games": result[3],
            "owned": result[4]
        }
    
    def extract_all_games(self, mark_expansions: bool = True) -> List[BoardGame]:
        """Extract ALL games from the collection.
        
        Args:
            mark_expansions: Whether to mark games as expansions
            
        Returns:
            List of all games in collection (with expansions marked)
        """
        conn = duckdb.connect(":memory:")
        
        query = f"""
        SELECT 
            objectid as object_id,
            objectname as name,
            rating as personal_rating,
            CASE WHEN wanttoplay = '1' THEN true ELSE false END as want_to_play,
            CASE WHEN wanttobuy = '1' THEN true ELSE false END as want_to_buy,
            CASE WHEN own = '1' THEN true ELSE false END as owned,
            average as average_rating,
            avgweight as complexity_weight,
            playingtime as playing_time,
            minplayers as min_players,
            maxplayers as max_players,
            itemtype as item_type,
            version_publishers
        FROM '{self.csv_path}'
        ORDER BY objectname
        """
        
        result = conn.execute(query).fetchall()
        conn.close()
        
        games = []
        expansions_count = 0
        
        for row in result:
            game_name = row[1]
            personal_rating = row[2] if row[2] is not None and row[2] != 0 else None
            item_type = row[11] if row[11] is not None else ""
            version_publishers_str = row[12] if row[12] is not None else ""
            
            # Parse version publishers (semicolon separated)
            version_publishers = []
            if version_publishers_str and version_publishers_str.strip():
                # Split by semicolon and clean up each publisher name
                for pub in version_publishers_str.split(';'):
                    pub_clean = pub.strip()
                    if pub_clean and pub_clean not in version_publishers:
                        version_publishers.append(pub_clean)
            
            # Check if this is an expansion using itemtype field first, then name-based detection
            is_expansion = False
            if mark_expansions:
                # Primary method: check itemtype field
                if item_type == "expansion":
                    is_expansion = True
                # Fallback method: name-based detection for games not marked in itemtype
                elif not item_type or item_type == "":
                    is_expansion = self._is_expansion(game_name)
            
            if is_expansion:
                expansions_count += 1
            
            game = BoardGame(
                object_id=row[0],
                name=game_name,
                want_to_play=row[3],
                want_to_buy=row[4],
                owned=row[5],
                is_expansion=is_expansion,
                publishers=version_publishers,  # Prepopulate with version publishers
                personal_rating=personal_rating,
                average_rating=row[6] if row[6] is not None else None,
                complexity_weight=row[7] if row[7] is not None else None,
                playing_time=row[8] if row[8] is not None else None,
                min_players=row[9] if row[9] is not None else None,
                max_players=row[10] if row[10] is not None else None
            )
            games.append(game)
        
        print(f"Extracted {len(games)} games ({expansions_count} marked as expansions)")
        return games
    
    def extract_owned_games(self) -> List[BoardGame]:
        """Extract games that are owned.
        
        Returns:
            List of owned games
        """
        conn = duckdb.connect(":memory:")
        
        query = f"""
        SELECT 
            objectid as object_id,
            objectname as name,
            CASE WHEN wanttoplay = '1' THEN true ELSE false END as want_to_play,
            CASE WHEN wanttobuy = '1' THEN true ELSE false END as want_to_buy,
            average as average_rating,
            avgweight as complexity_weight,
            playingtime as playing_time,
            minplayers as min_players,
            maxplayers as max_players
        FROM '{self.csv_path}'
        WHERE own = '1'
        ORDER BY objectname
        """
        
        result = conn.execute(query).fetchall()
        conn.close()
        
        games = []
        for row in result:
            game = BoardGame(
                object_id=row[0],
                name=row[1],
                want_to_play=row[2],
                want_to_buy=row[3],
                average_rating=row[4] if row[4] is not None else None,
                complexity_weight=row[5] if row[5] is not None else None,
                playing_time=row[6] if row[6] is not None else None,
                min_players=row[7] if row[7] is not None else None,
                max_players=row[8] if row[8] is not None else None
            )
            games.append(game)
        
        return games
    
    def get_expansion_info(self) -> dict:
        """Get information about expansions in the target games."""
        # First get all target games including expansions
        all_games = self.extract_target_games(include_expansions=True)
        
        # Then get games excluding expansions
        base_games = self.extract_target_games(include_expansions=False)
        
        # Find which games were filtered as expansions
        all_names = {g.name for g in all_games}
        base_names = {g.name for g in base_games}
        expansion_names = all_names - base_names
        
        return {
            "total_with_expansions": len(all_games),
            "total_without_expansions": len(base_games),
            "expansions_filtered": len(expansion_names),
            "expansion_examples": sorted(list(expansion_names))[:5]  # Show first 5
        }