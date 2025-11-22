from langchain_core.tools import tool
import json
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def load_geospatial_data() -> gpd.GeoDataFrame | None:
    """
    Load GeoJSON once, cache forever.
    OPTIMIZED: Uses pyogrio engine with arrow for 100x+ speedup.
    """
    logger.info("Loading geospatial data...")
    data_path = Path("data/nairobi_buildings.geojson")
    
    if not data_path.exists():
        logger.warning("Data file not found")
        return None
    
    try:
        # CRITICAL: Use pyogrio engine with arrow for massive speedup
        try:
            gdf = gpd.read_file(data_path, engine='pyogrio', use_arrow=True)
            logger.info("Using pyogrio engine (fast)")
        except (ImportError, Exception) as e:
            logger.warning(f"pyogrio not available ({e}), falling back to fiona (slow)")
            gdf = gpd.read_file(data_path)
        
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        
        # Ensure columns exist
        for col in ['name', 'type', 'risk_level']:
            if col not in gdf.columns:
                gdf[col] = "Unknown" if col != 'risk_level' else 'low'
        
        # Create spatial index ONCE at load time
        gdf.sindex  # This builds it
        
        logger.info(f"Loaded {len(gdf)} features with spatial index")
        return gdf
    except Exception as e:
        logger.error(f"Load error: {e}")
        return None

@lru_cache(maxsize=1)
def load_simplified_display_data() -> gpd.GeoDataFrame | None:
    """
    Load SIMPLIFIED version for map display only.
    This is what the map should use - not the full dataset.
    """
    gdf = load_geospatial_data()
    if gdf is None:
        return None
    
    # Option 1: Sample 0.5% of buildings
    simplified = gdf.sample(frac=0.005, random_state=84)
    
    # Option 2: Or simplify geometries
    #simplified = gdf.copy()
    #simplified['geometry'] = simplified['geometry'].simplify(tolerance=0.0001)
    
    return simplified

@tool
def search_buildings_by_location(latitude: float, longitude: float, radius_meters: float = 500) -> str:
    """
    Search for buildings within radius of coordinates.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate  
        radius_meters: Search radius in meters (default 500)
    
    Returns:
        JSON string with building data and coordinates
    """
    gdf = load_geospatial_data()
    if gdf is None:
        return json.dumps({"error": "Data unavailable"})
    
    try:
        gdf_utm = gdf.to_crs("EPSG:32737")
        point_utm = gpd.GeoSeries([Point(longitude, latitude)], crs="EPSG:4326").to_crs("EPSG:32737")[0]
        buffer_geom = point_utm.buffer(radius_meters)
        
        within = gdf_utm[gdf_utm.geometry.within(buffer_geom)].to_crs("EPSG:4326")
        
        return json.dumps({
            "count": len(within),
            "center": {"lat": latitude, "lon": longitude},
            "buildings": within[['name', 'risk_level', 'type']].fillna('Unknown').head(10).to_dict('records')
        }, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def analyze_seismic_risk(zone: str = "all") -> str:
    """
    Analyze seismic risk distribution across buildings.
    
    Returns:
        JSON with risk statistics
    """
    gdf = load_geospatial_data()
    if gdf is None:
        return json.dumps({"error": "Data unavailable"})
    
    try:
        risk_counts = gdf['risk_level'].value_counts().to_dict()
        total = len(gdf)
        high_risk = risk_counts.get('high', 0)
        
        return json.dumps({
            "total_buildings": total,
            "risk_distribution": risk_counts,
            "risk_score": round((high_risk / total * 10) if total > 0 else 0, 1),
            "high_risk_pct": round((high_risk / total * 100) if total > 0 else 0, 2)
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def calculate_building_density(area_name: str = "Nairobi") -> str:
    """Calculate building density per square kilometer."""
    gdf = load_geospatial_data()
    if gdf is None:
        return json.dumps({"error": "Data unavailable"})
    
    try:
        gdf_utm = gdf.to_crs("EPSG:32737")
        area_sq_km = gdf_utm.unary_union.convex_hull.area / 1e6
        density = len(gdf) / area_sq_km if area_sq_km > 0 else 0
        
        return json.dumps({
            "area": area_name,
            "buildings": len(gdf),
            "area_sq_km": round(area_sq_km, 2),
            "density_per_km2": round(density, 2)
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def find_critical_infrastructure(infrastructure_type: str = "all") -> str:
    """
    Find critical infrastructure like hospitals, schools, police stations.
    
    Args:
        infrastructure_type: One of 'school', 'hospital', 'police', 'fire', or 'all'
    
    Returns:
        JSON with infrastructure locations including coordinates
    """
    gdf = load_geospatial_data()
    if gdf is None:
        return json.dumps({"error": "Data unavailable"})
    
    try:
        search_map = {
            "school": "school|academy|college|university",
            "hospital": "hospital|clinic|medical|dispensary",
            "police": "police|station",
            "fire": "fire"
        }
        
        pattern = search_map.get(infrastructure_type, "|".join(search_map.values()))
        mask = gdf['type'].str.contains(pattern, case=False, na=False) | \
               gdf['name'].str.contains(pattern, case=False, na=False)
        
        matches = gdf[mask].head(20)
        
        results = []
        for _, row in matches.iterrows():
            results.append({
                "name": row['name'],
                "type": row['type'],
                "risk_level": row['risk_level'],
                "coords": [row.geometry.y, row.geometry.x]  # [lat, lon]
            })
        
        return json.dumps({
            "count": len(matches),
            "items": results
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool  
def get_seismic_history(years_back: int = 10) -> str:
    """Get historical seismic events (simulated data)."""
    return json.dumps({
        "period": f"Last {years_back} years",
        "events": [
            {"date": "2023-08-15", "magnitude": 4.2, "location": "15km NE Nairobi"},
            {"date": "2021-03-22", "magnitude": 5.1, "location": "28km E Nairobi"}
        ]
    })

def get_tools():
    return [
        search_buildings_by_location,
        analyze_seismic_risk,
        calculate_building_density,
        find_critical_infrastructure,
        get_seismic_history
    ]