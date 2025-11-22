# 🗺️ GeoJSON Data Scraping Guide

This guide explains how to collect real building data from OpenStreetMap for your GeoAI platform.

##  Overview

The `scrape_geojson.py` script fetches building data from OpenStreetMap's Overpass API and converts it to GeoJSON format with properties suitable for seismic analysis.

##  Quick Start

### 1. Setup

Create a `scripts` directory and add the scraper:
```bash
mkdir scripts
# Copy scrape_geojson.py to scripts/
```

Install additional dependencies:
```bash
pip install requests
```

### 2. Basic Usage

**Scrape Nairobi (default):**
```bash
python scripts/scrape_geojson.py
```

**Scrape specific city:**
```bash
python scripts/scrape_geojson.py --city Mombasa
```

**Scrape all predefined cities:**
```bash
python scripts/scrape_geojson.py --all-cities
```

**Custom location with bounding box:**
```bash
python scripts/scrape_geojson.py --city "Custom City" --bbox -1.35 36.70 -1.20 36.95
```

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--city` | City name | `--city Nairobi` |
| `--bbox` | Custom bounding box (S W N E) | `--bbox -1.35 36.70 -1.20 36.95` |
| `--output` | Custom output filename | `--output my_buildings.geojson` |
| `--output-dir` | Output directory | `--output-dir data` |
| `--all-cities` | Scrape all predefined cities | `--all-cities` |

## Finding Bounding Box Coordinates

### Method 1: BoundingBox.com (Easiest)
1. Go to [boundingbox.klokantech.com](http://boundingbox.klokantech.com/)
2. Search for your city
3. Select "CSV" format
4. Copy coordinates in order: south, west, north, east

### Method 2: OpenStreetMap Export
1. Go to [openstreetmap.org](https://www.openstreetmap.org/)
2. Click "Export" in the top menu
3. Select "Manually select a different area"
4. Draw a box around your area
5. Note the coordinates

### Method 3: Geojson.io
1. Go to [geojson.io](http://geojson.io/)
2. Draw a rectangle on the map
3. View the coordinates in the JSON output

## Predefined Cities

The script includes these Kenyan cities by default:

```python
CITY_BBOXES = {
    "Nairobi": (-1.3500, 36.7000, -1.2000, 36.9500),
    "Mombasa": (-4.1000, 39.6000, -4.0000, 39.7500),
    "Kisumu": (-0.1500, 34.7000, -0.0500, 34.8000),
    "Nakuru": (-0.3500, 36.0500, -0.2500, 36.1000),
    "Eldoret": (0.4500, 35.2500, 0.5500, 35.3500),
}
```

### Adding More Cities

Edit `scrape_geojson.py` and add to `CITY_BBOXES`:
```python
CITY_BBOXES = {
    # ... existing cities ...
    "YourCity": (south, west, north, east),
}
```

## Output Format

The scraper generates GeoJSON with these properties:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "osm_id": 12345678,
        "name": "Building Name",
        "type": "residential",
        "height_m": 25.5,
        "levels": 8,
        "address": "123 Main St, Nairobi",
        "amenity": "school",
        "risk_level": "moderate"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [36.8172, -1.2864]
      }
    }
  ]
}
```

### Building Properties Extracted

- **osm_id**: OpenStreetMap ID
- **name**: Building name (if available)
- **type**: Building type (residential, commercial, industrial, etc.)
- **height_m**: Height in meters
- **levels**: Number of floors
- **address**: Street address
- **amenity**: Special use (hospital, school, etc.)
- **shop**: Shop type (if commercial)
- **risk_level**: Estimated seismic risk (low, moderate, moderate-high, high)

## Advanced Usage

### Python API Usage

```python
from scripts.scrape_geojson import GeoDataScraper

# Initialize scraper
scraper = GeoDataScraper(output_dir='data')

# Scrape single city
scraper.scrape_city(
    city_name='Nairobi',
    bbox=(-1.3500, 36.7000, -1.2000, 36.9500),
    filename='nairobi_buildings.geojson'
)

# Scrape multiple cities
cities = {
    'Nairobi': (-1.3500, 36.7000, -1.2000, 36.9500),
    'Mombasa': (-4.1000, 39.6000, -4.0000, 39.7500),
}
scraper.scrape_multiple_cities(cities)
```

### Customizing the Query

Edit the `build_overpass_query` method in `scrape_geojson.py`:

```python
def build_overpass_query(self, bbox, building_types=None):
    south, west, north, east = bbox
    
    # Example: Only get buildings with height data
    query = f"""
    [out:json][timeout:60];
    (
      way["building"]["height"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    """
    return query
```

## ⚠️ Important Notes

### API Rate Limits
- OpenStreetMap Overpass API has rate limits
- Script automatically waits 10 seconds between cities
- For large areas, consider splitting into smaller bounding boxes

### Bounding Box Size
- **Small city center**: 0.05° × 0.05° (~5km × 5km)
- **Medium city**: 0.15° × 0.15° (~15km × 15km)
- **Large area**: May need to split into multiple requests

### Data Quality
- Not all buildings have height information
- Building names may be missing
- Risk levels are estimated heuristically

##  Troubleshooting

### Issue: Request timeout
```bash
✗ Attempt 1 failed: HTTPConnectionPool... timeout
```
**Solution**: Reduce bounding box size or increase timeout in script

### Issue: Too many buildings (>100,000)
```bash
✗ Error: Query result too large
```
**Solution**: Split area into smaller bounding boxes

### Issue: No buildings returned
```bash
✓ Processed 0 buildings
```
**Solutions**:
- Check bounding box coordinates (they might be swapped)
- Verify the area has buildings in OpenStreetMap
- Try a different area

### Issue: Script is slow
**Normal behavior**: Large cities can take 30-60 seconds
**Speed up**: 
- Reduce bounding box size
- Filter specific building types
- Use smaller timeout value

## Examples

### Example 1: Scrape Downtown Only
```bash
# Get just Nairobi CBD
python scripts/scrape_geojson.py \
    --city "Nairobi CBD" \
    --bbox -1.2950 36.8100 -1.2800 36.8300 \
    --output nairobi_cbd.geojson
```

### Example 2: All Major Kenyan Cities
```bash
python scripts/scrape_geojson.py --all-cities
```

### Example 3: Custom Location (e.g., your neighborhood)
```bash
python scripts/scrape_geojson.py \
    --city "My Neighborhood" \
    --bbox -1.2900 36.8100 -1.2850 36.8150
```

## Global Usage

The scraper works worldwide! Just provide coordinates:

### New York City
```bash
python scripts/scrape_geojson.py \
    --city "New York" \
    --bbox 40.7000 -74.0200 40.8000 -73.9000
```

### London
```bash
python scripts/scrape_geojson.py \
    --city "London" \
    --bbox 51.4500 -0.2000 51.5500 0.0000
```

### Tokyo
```bash
python scripts/scrape_geojson.py \
    --city "Tokyo" \
    --bbox 35.6000 139.6000 35.7500 139.8000
```

## Updating Your App

After scraping, update your Streamlit app:

1. **Replace data file**:
```bash
cp nairobi_buildings.geojson data/
```

2. **Restart Streamlit**:
```bash
streamlit run app.py
```

3. **Verify in UI**: Check that new buildings appear on map

## Best Practices

1. **Start Small**: Test with small bounding box first
2. **Check Results**: Verify GeoJSON is valid before using
3. **Backup Data**: Keep copies of scraped data
4. **Update Regularly**: Building data changes over time
5. **Document Sources**: Note when and where data was collected

## 🆘 Need Help?

- **OpenStreetMap Wiki**: [wiki.openstreetmap.org](https://wiki.openstreetmap.org/)
- **Overpass API Docs**: [overpass-api.de](https://overpass-api.de/)
- **Test Queries**: [overpass-turbo.eu](https://overpass-turbo.eu/)
