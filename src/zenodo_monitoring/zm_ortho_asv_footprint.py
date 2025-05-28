import json
from pathlib import Path


class OrthoASVFootprint:
    def __init__(self):
        
        self.data_path = Path("data/ortho_asv_footprint.geojson")
        self.data = []
        
        if not self.data_path.exists():
            raise FileNotFoundError("edna_data not found")
        
        with open(self.data_path) as f:
            self.data = json.load(f)
    
    def get_data(self, year: str, empty: bool = False) -> dict:
        
        if empty:
            return {
                "type": "FeatureCollection",
                "features": []
            }

        features = []
        for feature in self.data["features"]:
            year_feature = feature["properties"]["filename"][0:4]

            if year == year_feature:
                features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }