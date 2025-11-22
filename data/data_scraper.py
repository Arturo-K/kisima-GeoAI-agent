"""
GeoJSON Data Scraper for Building Footprints
Fetches building data from OpenStreetMap using Overpass API
"""

import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import argparse

class GeoDataScraper:
    """Scraper for collecting building data from OpenStreetMap"""
    
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        
    def build_overpass_query(
        self, 
        bbox: tuple, 
        building_types: Optional[List[str]] = None,
        include_height: bool = True
    ) -> str:
        """
        Build Overpass API query for building data
        
        Args:
            bbox: Bounding box (south, west, north, east)
            building_types: List of building types to filter (optional)
            include_height: Whether to only include buildings with height data
        
        Returns:
            Overpass QL query string
        """
        south, west, north, east = bbox
        
        # Base query for all buildings
        query = f"""
        [out:json][timeout:60];
        (
          way["building"]({south},{west},{north},{east});
          relation["building"]({south},{west},{north},{east});
        );
        out body;
        >;
        out skel qt;
        """
        
        return query
    
    def fetch_osm_data(self, bbox: tuple, max_retries: int = 3) -> Dict:
        """
        Fetch data from OpenStreetMap Overpass API
        
        Args:
            bbox: Bounding box coordinates
            max_retries: Maximum retry attempts
            
        Returns:
            JSON response from Overpass API
        """
        query = self.build_overpass_query(bbox)
        
        for attempt in range(max_retries):
            try:
                print(f"Fetching data from OpenStreetMap (attempt {attempt + 1}/{max_retries})...")
                response = requests.post(
                    self.overpass_url,
                    data={"data": query},
                    timeout=120
                )
                response.raise_for_status()
                
                data = response.json()
                print(f"✓ Successfully fetched {len(data.get('elements', []))} elements")
                return data
                
            except requests.exceptions.RequestException as e:
                print(f"✗ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"  Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to fetch data after {max_retries} attempts")
    
    def osm_to_geojson(self, osm_data: Dict) -> Dict:
        """
        Convert OSM data to GeoJSON format
        
        Args:
            osm_data: Raw OSM data from Overpass API
            
        Returns:
            GeoJSON FeatureCollection
        """
        # Create lookup for nodes
        nodes = {}
        ways = []
        
        for element in osm_data.get('elements', []):
            if element['type'] == 'node':
                nodes[element['id']] = (element['lon'], element['lat'])
            elif element['type'] == 'way' and 'tags' in element:
                ways.append(element)
        
        features = []
        
        for way in ways:
            # Get building properties
            tags = way.get('tags', {})
            
            # Skip if not a building
            if 'building' not in tags:
                continue
            
            # Get coordinates
            coords = []
            for node_id in way.get('nodes', []):
                if node_id in nodes:
                    coords.append(nodes[node_id])
            
            if len(coords) < 3:
                continue
            
            # Calculate centroid for point representation
            centroid_lon = sum(c[0] for c in coords) / len(coords)
            centroid_lat = sum(c[1] for c in coords) / len(coords)
            
            # Extract building properties
            properties = {
                'osm_id': way['id'],
                'name': tags.get('name', f"Building {way['id']}"),
                'type': tags.get('building', 'yes'),
                'height_m': self._parse_height(tags.get('height')),
                'levels': tags.get('building:levels'),
                'address': self._get_address(tags),
                'amenity': tags.get('amenity'),
                'shop': tags.get('shop'),
            }
            
            # Estimate risk level based on building characteristics
            properties['risk_level'] = self._estimate_risk(properties)
            
            # Create feature (using centroid as point)
            feature = {
                'type': 'Feature',
                'properties': {k: v for k, v in properties.items() if v is not None},
                'geometry': {
                    'type': 'Point',
                    'coordinates': [centroid_lon, centroid_lat]
                }
            }
            
            features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return geojson
    
    def _parse_height(self, height_str: Optional[str]) -> Optional[float]:
        """Parse height string to meters"""
        if not height_str:
            return None
        
        try:
            # Remove units and convert to float
            height = height_str.replace('m', '').replace(' ', '')
            return float(height)
        except (ValueError, AttributeError):
            return None
    
    def _get_address(self, tags: Dict) -> Optional[str]:
        """Construct address from OSM tags"""
        addr_parts = []
        
        if 'addr:housenumber' in tags:
            addr_parts.append(tags['addr:housenumber'])
        if 'addr:street' in tags:
            addr_parts.append(tags['addr:street'])
        if 'addr:city' in tags:
            addr_parts.append(tags['addr:city'])
            
        return ', '.join(addr_parts) if addr_parts else None
    
    def _estimate_risk(self, properties: Dict) -> str:
        """Estimate seismic risk based on building characteristics"""
        # Simple heuristic - can be made more sophisticated
        height = properties.get('height_m', 0)
        building_type = properties.get('type', 'yes')
        
        if height and height > 50:
            return 'moderate'
        elif building_type in ['industrial', 'warehouse']:
            return 'moderate-high'
        elif height and height < 15:
            return 'low'
        else:
            return 'moderate'
    
    def scrape_city(
        self, 
        city_name: str, 
        bbox: tuple,
        filename: Optional[str] = None
    ) -> Path:
        """
        Scrape building data for a city and save as GeoJSON
        
        Args:
            city_name: Name of the city
            bbox: Bounding box (south, west, north, east)
            filename: Output filename (optional)
            
        Returns:
            Path to saved GeoJSON file
        """
        print(f"\n🌍 Scraping building data for {city_name}...")
        print(f"Bounding box: {bbox}")
        
        # Fetch data
        osm_data = self.fetch_osm_data(bbox)
        
        # Convert to GeoJSON
        print("Converting to GeoJSON format...")
        geojson = self.osm_to_geojson(osm_data)
        
        print(f"✓ Processed {len(geojson['features'])} buildings")
        
        # Save to file
        if filename is None:
            filename = f"{city_name.lower().replace(' ', '_')}_buildings.geojson"
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved to: {output_path}")
        print(f"File size: {output_path.stat().st_size / 1024:.2f} KB")
        
        return output_path
    
    def scrape_multiple_cities(self, cities: Dict[str, tuple]) -> List[Path]:
        """
        Scrape data for multiple cities
        
        Args:
            cities: Dictionary of {city_name: bbox}
            
        Returns:
            List of output file paths
        """
        output_paths = []
        
        for i, (city_name, bbox) in enumerate(cities.items(), 1):
            print(f"\n{'='*60}")
            print(f"Processing city {i}/{len(cities)}: {city_name}")
            print(f"{'='*60}")
            
            try:
                path = self.scrape_city(city_name, bbox)
                output_paths.append(path)
                
                # Be nice to the API - wait between requests
                if i < len(cities):
                    print("\nWaiting 10 seconds before next city...")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"✗ Error processing {city_name}: {str(e)}")
                continue
        
        return output_paths


# Predefined city bounding boxes
CITY_BBOXES = {
    "Nairobi": (-1.3500, 36.7000, -1.2000, 36.9500),
    "Mombasa": (-4.1000, 39.6000, -4.0000, 39.7500),
    "Kisumu": (-0.1500, 34.7000, -0.0500, 34.8000),
    "Nakuru": (-0.3500, 36.0500, -0.2500, 36.1000),
    "Eldoret": (0.4500, 35.2500, 0.5500, 35.3500),
}


def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description='Scrape building data from OpenStreetMap'
    )
    parser.add_argument(
        '--city',
        type=str,
        help='City name (e.g., Nairobi, Mombasa)',
        default='Nairobi'
    )
    parser.add_argument(
        '--bbox',
        type=float,
        nargs=4,
        metavar=('S', 'W', 'N', 'E'),
        help='Custom bounding box: south west north east'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output filename (optional)'
    )
    parser.add_argument(
        '--all-cities',
        action='store_true',
        help='Scrape all predefined cities'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data',
        help='Output directory (default: data)'
    )
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = GeoDataScraper(output_dir=args.output_dir)
    
    if args.all_cities:
        # Scrape all predefined cities
        print(f"\n🌍 Scraping {len(CITY_BBOXES)} cities...")
        scraper.scrape_multiple_cities(CITY_BBOXES)
    else:
        # Scrape single city
        if args.bbox:
            bbox = tuple(args.bbox)
        elif args.city in CITY_BBOXES:
            bbox = CITY_BBOXES[args.city]
        else:
            print(f"✗ City '{args.city}' not found in predefined cities.")
            print(f"Available cities: {', '.join(CITY_BBOXES.keys())}")
            print("Or provide custom --bbox coordinates")
            return
        
        scraper.scrape_city(args.city, bbox, args.output)
    
    print("\n Scraping complete!")


if __name__ == "__main__":
    main()