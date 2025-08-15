# Source Code Structure

This directory contains the core Python modules and step scripts for the Essen Route Planning tool.

## Core Modules

- **`data_models.py`** - Pydantic models for type safety and data validation
- **`collection_extractor.py`** - DuckDB-based extraction from BGG collection CSV
- **`bgg_scraper.py`** - BoardGameGeek scraper with caching and rate limiting

## Step Scripts

The `steps/` directory contains the main pipeline scripts:

1. **`step1_extract_games.py`** - Extract target games from collection.csv
2. **`step2_scrape_bgg.py`** - Scrape BGG for publisher information
3. **`step3_fetch_essen_data.py`** - Fetch Essen exhibitor and product data
4. **`step4_match_publishers.py`** - Match publishers to exhibitors using fuzzy matching
5. **`step5_generate_route.py`** - Generate final route reports

## Usage

These scripts are designed to be run via the bash wrappers in the project root:

```bash
./step_01    # Runs src/steps/step1_extract_games.py
./step_02    # Runs src/steps/step2_scrape_bgg.py
# etc...
```

Or via the master script:

```bash
./run_all    # Runs all steps in sequence
```

## Development

When modifying the code:

1. Update imports if moving files
2. Test individual steps with the bash wrappers
3. Ensure virtual environment is activated
4. Run type checking and linting as needed