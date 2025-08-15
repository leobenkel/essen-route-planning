"""Data models for the Essen Route Planning application."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class Priority(str, Enum):
    """Priority levels for games."""
    WANT_TO_BUY = "want_to_buy"
    WANT_TO_PLAY = "want_to_play"


class BoardGame(BaseModel):
    """Represents a board game from the BGG collection."""
    object_id: int = Field(..., description="BoardGameGeek object ID")
    name: str = Field(..., description="Game name")
    want_to_play: bool = Field(default=False)
    want_to_buy: bool = Field(default=False)
    publishers: List[str] = Field(default_factory=list, description="List of publishers")
    average_rating: Optional[float] = Field(None, description="BGG average rating")
    complexity_weight: Optional[float] = Field(None, description="Game complexity weight")
    playing_time: Optional[int] = Field(None, description="Playing time in minutes")
    min_players: Optional[int] = Field(None, description="Minimum players")
    max_players: Optional[int] = Field(None, description="Maximum players")
    
    @property
    def priority(self) -> Priority:
        """Get the priority level of the game."""
        if self.want_to_buy:
            return Priority.WANT_TO_BUY
        return Priority.WANT_TO_PLAY
    
    @property
    def bgg_url(self) -> str:
        """Generate the BGG URL for the game."""
        from slugify import slugify
        slug = slugify(self.name)
        return f"https://boardgamegeek.com/boardgame/{self.object_id}/{slug}"


class Exhibitor(BaseModel):
    """Represents an exhibitor at Essen Spiel."""
    id: str = Field(..., description="Exhibitor ID")
    name: str = Field(..., description="Exhibitor name")
    hall: Optional[Union[str, int]] = Field(None, description="Hall location")
    booth: Optional[str] = Field(None, description="Booth number")
    address: Optional[str] = Field(None)
    country: Optional[str] = Field(None)
    website: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    info: Optional[str] = Field(None)
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"


class EssenProduct(BaseModel):
    """Represents a product at Essen Spiel."""
    title: str = Field(..., description="Product title")
    company_id: str = Field(..., description="Company/Exhibitor ID")
    subtitle: Optional[str] = Field(None)
    info: Optional[str] = Field(None)
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"


class ExhibitorMatch(BaseModel):
    """Represents a single exhibitor match for a game."""
    exhibitor: Exhibitor
    match_confidence: float = Field(0.0, ge=0.0, le=1.0)
    match_reason: str = Field("", description="Reason for the match")
    product_confirmed: bool = Field(False, description="Whether the game is confirmed as a product at this exhibitor")
    product_match_info: Optional[str] = Field(None, description="Details about the product match")


class GameMatch(BaseModel):
    """Represents all matches between a game and exhibitors."""
    game: BoardGame
    exhibitor_matches: List[ExhibitorMatch] = Field(default_factory=list, description="All exhibitor matches for this game")
    
    @property
    def is_matched(self) -> bool:
        """Check if the game has been successfully matched to any exhibitor."""
        return len(self.exhibitor_matches) > 0
    
    @property
    def best_match(self) -> Optional[ExhibitorMatch]:
        """Get the best exhibitor match (highest confidence)."""
        if not self.exhibitor_matches:
            return None
        return max(self.exhibitor_matches, key=lambda x: x.match_confidence)
    
    @property
    def product_confirmed_matches(self) -> List[ExhibitorMatch]:
        """Get all exhibitor matches where the product is confirmed."""
        return [match for match in self.exhibitor_matches if match.product_confirmed]


class RouteStop(BaseModel):
    """Represents a stop on the route through Essen."""
    hall: str
    booth: str
    exhibitor: Exhibitor
    games: List[BoardGame]
    
    @property
    def priority_score(self) -> int:
        """Calculate priority score for this stop."""
        score = 0
        for game in self.games:
            if game.want_to_buy:
                score += 10
            if game.want_to_play:
                score += 5
        return score


class RouteReport(BaseModel):
    """Final route report for Essen Spiel."""
    total_games: int
    matched_games: int
    unmatched_games: List[BoardGame]
    route_stops: List[RouteStop]
    
    def to_markdown(self) -> str:
        """Generate a markdown report."""
        lines = [
            "# Essen Spiel Route Planning Report",
            "",
            "## Legend",
            "- 🛒 Want to Buy | 🎮 Want to Play",
            "- ⭐ BGG Average Rating | 🎯 Complexity Weight | 👥 Player Count | ⏱️ Playing Time",
            "",
            f"## Summary",
            f"- Total target games: {self.total_games}",
            f"- Successfully matched: {self.matched_games}",
            f"- Unmatched games: {len(self.unmatched_games)}",
            "",
            "## Route by Hall",
            ""
        ]
        
        # Group by hall
        halls: Dict[str, List[RouteStop]] = {}
        for stop in self.route_stops:
            if stop.hall not in halls:
                halls[stop.hall] = []
            halls[stop.hall].append(stop)
        
        # Sort halls and stops
        for hall in sorted(halls.keys()):
            lines.append(f"### Hall {hall}")
            lines.append("")
            
            stops = sorted(halls[hall], key=lambda s: s.priority_score, reverse=True)
            for stop in stops:
                lines.append(f"#### Booth {stop.booth} - {stop.exhibitor.name}")
                for game in stop.games:
                    priority = "🛒" if game.want_to_buy else "🎮"
                    
                    # Build game info string
                    info_parts = []
                    if game.average_rating:
                        info_parts.append(f"⭐{game.average_rating:.1f}")
                    if game.complexity_weight:
                        info_parts.append(f"🎯{game.complexity_weight:.1f}")
                    if game.min_players and game.max_players:
                        if game.min_players == game.max_players:
                            info_parts.append(f"👥{game.min_players}")
                        else:
                            info_parts.append(f"👥{game.min_players}-{game.max_players}")
                    if game.playing_time:
                        info_parts.append(f"⏱️{game.playing_time}min")
                    
                    info_str = f" ({' | '.join(info_parts)})" if info_parts else ""
                    lines.append(f"- [ ] {priority} [{game.name}]({game.bgg_url}){info_str}")
                lines.append("")
        
        if self.unmatched_games:
            lines.append("## Unmatched Games")
            lines.append("")
            for game in self.unmatched_games:
                priority = "🛒" if game.want_to_buy else "🎮"
                
                # Build game info string
                info_parts = []
                if game.average_rating:
                    info_parts.append(f"⭐{game.average_rating:.1f}")
                if game.complexity_weight:
                    info_parts.append(f"🎯{game.complexity_weight:.1f}")
                if game.min_players and game.max_players:
                    if game.min_players == game.max_players:
                        info_parts.append(f"👥{game.min_players}")
                    else:
                        info_parts.append(f"👥{game.min_players}-{game.max_players}")
                if game.playing_time:
                    info_parts.append(f"⏱️{game.playing_time}min")
                
                info_str = f" ({' | '.join(info_parts)})" if info_parts else ""
                lines.append(f"- [ ] {priority} [{game.name}]({game.bgg_url}){info_str}")
        
        return "\n".join(lines)
    
    def to_html(self) -> str:
        """Generate an HTML report that pastes well into Google Docs."""
        checkbox = '<input type="checkbox" />'  # HTML checkboxes
        
        html = [
            "<h1>Essen Spiel Route Planning Report</h1>",
            "",
            "<h2>Legend</h2>",
            "<ul>",
            "<li>🛒 Want to Buy | 🎮 Want to Play</li>",
            "<li>⭐ BGG Average Rating | 🎯 Complexity Weight | 👥 Player Count | ⏱️ Playing Time</li>",
            "</ul>",
            "",
            f"<h2>Summary</h2>",
            "<ul>",
            f"<li>Total target games: {self.total_games}</li>",
            f"<li>Successfully matched: {self.matched_games}</li>",
            f"<li>Unmatched games: {len(self.unmatched_games)}</li>",
            "</ul>",
            "",
            "<h2>Route by Hall</h2>",
            ""
        ]
        
        # Group by hall
        halls: Dict[str, List[RouteStop]] = {}
        for stop in self.route_stops:
            if stop.hall not in halls:
                halls[stop.hall] = []
            halls[stop.hall].append(stop)
        
        # Sort halls numerically/alphabetically
        for hall in sorted(halls.keys(), key=lambda x: (len(x), x)):
            html.append(f"<h3>Hall {hall}</h3>")
            
            stops = sorted(halls[hall], key=lambda s: s.priority_score, reverse=True)
            for stop in stops:
                html.append(f"<h4>Booth {stop.booth} - {stop.exhibitor.name}</h4>")
                html.append("<ul>")
                for game in stop.games:
                    priority = "🛒" if game.want_to_buy else "🎮"
                    
                    # Build game info string
                    info_parts = []
                    if game.average_rating:
                        info_parts.append(f"⭐{game.average_rating:.1f}")
                    if game.complexity_weight:
                        info_parts.append(f"🎯{game.complexity_weight:.1f}")
                    if game.min_players and game.max_players:
                        if game.min_players == game.max_players:
                            info_parts.append(f"👥{game.min_players}")
                        else:
                            info_parts.append(f"👥{game.min_players}-{game.max_players}")
                    if game.playing_time:
                        info_parts.append(f"⏱️{game.playing_time}min")
                    
                    info_str = f" ({' | '.join(info_parts)})" if info_parts else ""
                    html.append(f'<li>{checkbox} {priority} <a href="{game.bgg_url}">{game.name}</a>{info_str}</li>')
                html.append("</ul>")
                html.append("")
        
        if self.unmatched_games:
            html.append("<h2>Unmatched Games</h2>")
            html.append("<ul>")
            for game in self.unmatched_games:
                priority = "🛒" if game.want_to_buy else "🎮"
                
                # Build game info string
                info_parts = []
                if game.average_rating:
                    info_parts.append(f"⭐{game.average_rating:.1f}")
                if game.complexity_weight:
                    info_parts.append(f"🎯{game.complexity_weight:.1f}")
                if game.min_players and game.max_players:
                    if game.min_players == game.max_players:
                        info_parts.append(f"👥{game.min_players}")
                    else:
                        info_parts.append(f"👥{game.min_players}-{game.max_players}")
                if game.playing_time:
                    info_parts.append(f"⏱️{game.playing_time}min")
                
                info_str = f" ({' | '.join(info_parts)})" if info_parts else ""
                html.append(f'<li>{checkbox} {priority} <a href="{game.bgg_url}">{game.name}</a>{info_str}</li>')
            html.append("</ul>")
            html.append("")
        
        return "\n".join(html)