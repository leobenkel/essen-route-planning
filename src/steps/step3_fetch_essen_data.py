#!/usr/bin/env python3
"""
Step 3: Fetch Essen Spiel exhibitor and product data.

This script:
1. Fetches exhibitor data from Essen API
2. Fetches product data from Essen API
3. Caches the data locally
4. Saves processed data for matching
"""

import json
import time
import argparse
from pathlib import Path
import requests
from typing import Dict, List, Any
from datetime import datetime


def get_essen_year() -> str:
    """
    Get the current Essen Spiel year.
    Essen Spiel typically occurs in October, so:
    - Before October: Use current year
    - October or later: Use current year
    """
    current_year = datetime.now().year
    return str(current_year)[-2:]  # Return last 2 digits (e.g., "25" for 2025)


def fetch_with_cache(url: str, cache_file: Path, description: str, use_cache: bool = True) -> List[Dict[str, Any]]:
    """Fetch data from URL or use cache if available."""
    
    # Check cache first
    if cache_file.exists() and use_cache:
        print(f"📂 Using cached {description}: {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            
        # Extract array from cached data structure
        if isinstance(cached_data, dict):
            if 'exhibitors' in cached_data:
                return cached_data['exhibitors']
            elif 'products' in cached_data:
                return cached_data['products']
            else:
                return []
        else:
            return cached_data
    
    # Fetch fresh data
    print(f"🌐 Fetching {description}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Save to cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Extract array from response structure
        if isinstance(data, dict):
            if 'exhibitors' in data:
                result = data['exhibitors']
            elif 'products' in data:
                result = data['products']
            else:
                # If it's a dict but no known key, return empty
                result = []
        else:
            result = data
        
        print(f"✅ Fetched {len(result)} {description}")
        print(f"💾 Cached to: {cache_file}")
        
        return result
        
    except requests.RequestException as e:
        print(f"❌ Error fetching {description}: {e}")
        return []


def main():
    """Fetch and process Essen Spiel data."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch Essen Spiel exhibitor and product data")
    parser.add_argument("--no-cache", action="store_true", 
                       help="Force fresh data fetch (ignore cache)")
    args = parser.parse_args()
    
    use_cache = not args.no_cache
    
    print("=" * 60)
    print("STEP 3: Fetch Essen Spiel Data")
    print("=" * 60)
    
    # Setup cache directory
    cache_dir = Path("data/cache/essen")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Essen API URLs (dynamic year)
    essen_year = get_essen_year()
    exhibitors_url = f'https://maps.eyeled-services.de/en/spiel{essen_year}/exhibitors?columns=["ID","NAME","ADRESSE","LAND","LOGO","PLZ","STADT","WEB","EMAIL","INFO","TELEFON","S_ORDER","STAND","HALLE"]'
    
    products_url = f'https://maps.eyeled-services.de/en/spiel{essen_year}/products?columns=["INFO","S_ORDER","TITEL","FIRMA_ID","UNTERTITEL","BILDER","BILDER_VERSIONEN","BILDER_TEXTE"]'
    
    # Fetch exhibitors
    print("\n📍 EXHIBITORS DATA")
    print("-" * 40)
    exhibitors = fetch_with_cache(
        exhibitors_url,
        cache_dir / "exhibitors_raw.json",
        "exhibitors",
        use_cache
    )
    
    # Wait a bit before next request
    time.sleep(2)
    
    # Fetch products
    print("\n🎲 PRODUCTS DATA")
    print("-" * 40)
    products = fetch_with_cache(
        products_url,
        cache_dir / "products_raw.json",
        "products",
        use_cache
    )
    
    # Process exhibitors data
    print("\n📋 Processing exhibitor data...")
    processed_exhibitors = []
    
    for exhibitor in exhibitors:
        raw_halls = exhibitor.get('HALLE', '')
        raw_booths = exhibitor.get('STAND', '')
        
        # Skip if no hall/booth data
        if not raw_halls or not raw_booths:
            continue
            
        # Handle pipe-separated multiple halls/booths
        halls = [h.strip() for h in raw_halls.split('|')]
        booths = [b.strip() for b in raw_booths.split('|')]
        
        # Create one entry for each hall/booth combination
        for i, hall in enumerate(halls):
            booth = booths[i] if i < len(booths) else booths[0]  # Use first booth if mismatch
            
            # Clean hall name - remove "Hall " prefix and normalize spaces  
            clean_hall = hall.strip().replace('\u00a0', ' ')
            if clean_hall.startswith('Hall '):
                clean_hall = clean_hall[5:]  # Remove "Hall " prefix
            clean_hall = clean_hall.strip()
            
            # Try to parse as integer for numeric halls
            try:
                hall_num = int(clean_hall)
                clean_hall = hall_num  # Store as integer
            except ValueError:
                # Keep as string for non-numeric halls like "Galeria"
                pass
            
            processed = {
                'id': exhibitor.get('ID', ''),
                'name': exhibitor.get('NAME', ''),
                'hall': clean_hall,
                'booth': booth,
                'country': exhibitor.get('LAND', ''),
                'website': exhibitor.get('WEB', ''),
                'email': exhibitor.get('EMAIL', ''),
                'info': exhibitor.get('INFO', ''),
                'is_multi_location': len(halls) > 1  # Flag for exhibitors in multiple locations
            }
            
            processed_exhibitors.append(processed)
    
    # Save processed exhibitors
    output_file = Path("data/output/essen_exhibitors.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_exhibitors, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Processed {len(processed_exhibitors)} exhibitors with hall/booth info")
    print(f"💾 Saved to: {output_file}")
    
    # Process products data
    print("\n📋 Processing product data...")
    processed_products = []
    
    for product in products:
        processed = {
            'title': product.get('TITEL', ''),
            'company_id': product.get('FIRMA_ID', ''),
            'subtitle': product.get('UNTERTITEL', ''),
            'info': product.get('INFO', '')
        }
        
        # Only include products with title and company
        if processed['title'] and processed['company_id']:
            processed_products.append(processed)
    
    # Save processed products
    output_file = Path("data/output/essen_products.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_products, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Processed {len(processed_products)} products")
    print(f"💾 Saved to: {output_file}")
    
    # Statistics
    print(f"\n📊 Essen Spiel 20{essen_year} Statistics:")
    
    # Hall distribution
    halls = {}
    for exhibitor in processed_exhibitors:
        hall = exhibitor['hall']
        halls[hall] = halls.get(hall, 0) + 1
    
    print(f"\n  Halls distribution:")
    # Sort with integers first, then strings
    sorted_halls = sorted(halls.keys(), key=lambda x: (isinstance(x, str), x))
    for hall in sorted_halls:
        hall_display = f"Hall {hall}" if isinstance(hall, int) else hall
        print(f"    {hall_display}: {halls[hall]} exhibitors")
    
    # Company with products
    companies_with_products = set(p['company_id'] for p in processed_products)
    print(f"\n  Companies with products listed: {len(companies_with_products)}")
    
    # Sample exhibitors
    print("\n  Sample exhibitors:")
    for exhibitor in processed_exhibitors[:5]:
        multi_flag = " [Multi-location]" if exhibitor.get('is_multi_location') else ""
        hall = exhibitor['hall']
        hall_display = f"Hall {hall}" if isinstance(hall, int) else hall
        print(f"    - {exhibitor['name']} ({hall_display}, Booth {exhibitor['booth']}){multi_flag}")
    
    print("\n✅ Step 3 complete! Next: Run step4_match_publishers.py")


if __name__ == "__main__":
    main()