from pathlib import Path
from shapely.geometry import mapping, MultiPoint
import pandas as pd


def get_footprints_from_tifs(folder_path: Path):
    features = []
    
    for file in folder_path.iterdir():
        if file.suffix != ".csv": continue
        if "ASV" not in file.name: continue

        df = pd.read_csv(file)
        df = df.dropna(subset=['GPSLatitude', 'GPSLongitude'])

        # Extract points
        points = list(zip(df['GPSLongitude'], df['GPSLatitude']))  # note (lon, lat)

        if len(points) < 3:
            raise ValueError("At least 3 points are needed to compute a convex hull.")

        # Compute convex hull
        hull = MultiPoint(points).convex_hull
        

        features.append({
            "type": "Feature",
            "geometry": mapping(hull),
            "properties": {
                "filename": file.stem
            }
        })

    
    return {
        "type": "FeatureCollection",
        "features": features
    }

# Usage
folder = Path("../data/")
geojson_data = get_footprints_from_tifs(folder)

# Save as GeoJSON file
import json
with open("../data/ortho_asv_footprint.geojson", "w") as f:
    json.dump(geojson_data, f)
