"""FastAPI application for Essen Route Planning - Where endpoint."""

import sys
import re
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
from bs4 import BeautifulSoup

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))

from game_lookup import GameLookupService
from url_parser import parse_bgg_url, is_valid_bgg_url
from data_models import BoardGame, ExhibitorMatch

app = FastAPI(
    title="Essen Route Planning API",
    description="Find BoardGameGeek games at Essen Spiel",
    version="1.0.0"
)

# Enable CORS for potential frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting middleware - add 2 second delay to prevent hammering
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Add a 2-second delay before processing requests to prevent API hammering."""
    # Skip delay for health check endpoint
    if request.url.path != "/health":
        await asyncio.sleep(2)
    response = await call_next(request)
    return response


# Templates directory
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class GameInfo(BaseModel):
    """Game information response model."""
    object_id: int
    name: str
    bgg_url: str
    publishers: List[str] = Field(default_factory=list)
    average_rating: Optional[float] = None
    complexity_weight: Optional[float] = None
    min_players: Optional[int] = None
    max_players: Optional[int] = None
    playing_time: Optional[int] = None


class ExhibitorInfo(BaseModel):
    """Exhibitor match response model."""
    id: str
    name: str
    hall: Optional[str] = None
    booth: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    match_confidence: float
    match_reason: str
    product_confirmed: bool
    product_match_info: Optional[str] = None


class WhereResponse(BaseModel):
    """Response model for where endpoint."""
    game: GameInfo
    exhibitors: List[ExhibitorInfo] = Field(default_factory=list)
    matched: bool
    confirmed_matches: int


class BGGSearchResult(BaseModel):
    """BGG search result model."""
    id: int
    name: str
    year: Optional[int] = None
    bgg_url: str


class BGGSearchResponse(BaseModel):
    """Response model for BGG search endpoint."""
    query: str
    results: List[BGGSearchResult] = Field(default_factory=list)
    count: int


def exhibitor_match_to_info(match: ExhibitorMatch) -> ExhibitorInfo:
    """Convert ExhibitorMatch to ExhibitorInfo response."""
    hall_str = str(match.exhibitor.hall) if match.exhibitor.hall is not None else None

    return ExhibitorInfo(
        id=match.exhibitor.id,
        name=match.exhibitor.name,
        hall=hall_str,
        booth=match.exhibitor.booth,
        country=match.exhibitor.country,
        website=match.exhibitor.website,
        match_confidence=match.match_confidence,
        match_reason=match.match_reason,
        product_confirmed=match.product_confirmed,
        product_match_info=match.product_match_info
    )


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main HTML UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint for Kubernetes."""
    return {"status": "healthy"}


@app.get("/search", response_model=BGGSearchResponse)
async def search_bgg(
    q: str = Query(..., description="Search query", min_length=1)
):
    """
    Search for board games on BoardGameGeek.

    Returns a list of games matching the search query.
    """
    try:
        # Make request to BGG search
        url = "https://boardgamegeek.com/geeksearch.php"
        params = {
            "action": "search",
            "q": q,
            "objecttype": "boardgame"
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        # Parse HTML response
        soup = BeautifulSoup(response.text, 'html.parser')

        results = []

        # Find all links to boardgame pages
        # Format: <a href="/boardgame/{id}/{slug}">Game Name</a>
        for link in soup.find_all('a', href=True):
            try:
                href = link.get('href', '')

                # Match /boardgame/{id}/...
                if not href.startswith('/boardgame/'):
                    continue

                # Extract game ID from href
                parts = href.split('/')
                if len(parts) < 3:
                    continue

                game_id = int(parts[2])

                # Extract game name from link text
                game_name = link.get_text(strip=True)
                if not game_name:
                    continue

                # Try to extract year from nearby text (if in format "(YYYY)")
                year = None
                # Look for year in the link's parent or next sibling
                parent_text = link.parent.get_text() if link.parent else ""
                year_match = re.search(r'\((\d{4})\)', parent_text)
                if year_match:
                    try:
                        year = int(year_match.group(1))
                    except ValueError:
                        pass

                # Construct BGG URL
                bgg_url = f"https://boardgamegeek.com/boardgame/{game_id}"

                results.append(BGGSearchResult(
                    id=game_id,
                    name=game_name,
                    year=year,
                    bgg_url=bgg_url
                ))

            except (ValueError, AttributeError, IndexError) as e:
                # Skip invalid links
                continue

        return BGGSearchResponse(
            query=q,
            results=results[:20],  # Limit to top 20 results
            count=len(results)
        )

    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to search BoardGameGeek: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {str(e)}"
        )


@app.get("/where", response_model=WhereResponse)
async def where(
    id: Optional[int] = Query(None, description="BoardGameGeek game ID"),
    link: Optional[str] = Query(None, description="BoardGameGeek game URL")
):
    """
    Find Essen exhibitor information for a BoardGameGeek game.

    Provide either 'id' or 'link' parameter:
    - id: BoardGameGeek game ID (e.g., 418354)
    - link: Full BGG URL (e.g., https://boardgamegeek.com/boardgame/418354/babylon)

    Returns game information and matched exhibitors at Essen Spiel.
    """
    # Validate inputs
    if not id and not link:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'id' or 'link' parameter"
        )

    if id and link:
        raise HTTPException(
            status_code=400,
            detail="Provide only one of 'id' or 'link', not both"
        )

    # Parse game from input
    game: Optional[BoardGame] = None

    if link:
        # Validate URL format
        if not is_valid_bgg_url(link):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid BoardGameGeek URL format. Expected: https://boardgamegeek.com/boardgame/{{id}}/{{slug}}"
            )

        # Parse URL
        game = parse_bgg_url(link)
        if not game:
            raise HTTPException(
                status_code=400,
                detail="Could not parse BoardGameGeek URL"
            )

    if id:
        # Create minimal game object from ID
        game = BoardGame(object_id=id, name=f"Game {id}")

    if not game:
        raise HTTPException(
            status_code=400,
            detail="Invalid game input"
        )

    try:
        # Initialize lookup service and find the game
        lookup_service = GameLookupService()
        match_result = lookup_service.lookup_game(game)

        # Build response
        enriched_game = match_result.game

        game_info = GameInfo(
            object_id=enriched_game.object_id,
            name=enriched_game.name,
            bgg_url=enriched_game.bgg_url,
            publishers=enriched_game.publishers,
            average_rating=enriched_game.average_rating,
            complexity_weight=enriched_game.complexity_weight,
            min_players=enriched_game.min_players,
            max_players=enriched_game.max_players,
            playing_time=enriched_game.playing_time
        )

        exhibitor_infos = [
            exhibitor_match_to_info(match)
            for match in match_result.exhibitor_matches
        ]

        # Sort exhibitors by product confirmed first, then by confidence
        exhibitor_infos.sort(
            key=lambda x: (x.product_confirmed, x.match_confidence),
            reverse=True
        )

        confirmed_count = len(match_result.product_confirmed_matches)

        return WhereResponse(
            game=game_info,
            exhibitors=exhibitor_infos,
            matched=len(exhibitor_infos) > 0,
            confirmed_matches=confirmed_count
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Essen data not available: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
